"""M002 纯图像单元测试：质检 v1.0 矩阵 / 归一（白底、长边、EXIF 方向）/ 本地存储。

画像合成均为确定性绘制（PIL），不依赖外部样本；阈值依据 = MODULE_CONTRACT
Configuration 默认值（modules/m002/config.py）。
"""
from __future__ import annotations

import hashlib
import io
import struct

from PIL import Image, ImageDraw, ImageFilter

from app.modules.m002.config import M002Settings
from app.modules.m002.services.image_store import ImageStore
from app.modules.m002.services.normalizer import Normalizer
from app.modules.m002.services.quality import LocalQualityChecker


def _settings(tmp_path) -> M002Settings:
    return M002Settings(image_store_root=str(tmp_path))


def _page(bg: int = 205) -> Image.Image:
    """可读的"作业纸"合成：浅底 + 多条横向深色笔迹（四周留白）。"""
    w, h = 900, 660
    img = Image.new("RGB", (w, h), (bg, bg, bg))
    d = ImageDraw.Draw(img)
    y = 90
    while y < h - 90:
        d.rectangle([80, y, w - 80, y + 16], fill=0)
        y += 80
    return img


def _rotated_page(degrees: float, bg: int = 205) -> Image.Image:
    """旋转后的作业纸；fillcolor 必须为 RGB 元组，避免 PIL 把整数索引成红色。"""
    return _page(bg).rotate(
        degrees, resample=Image.BILINEAR, expand=True, fillcolor=(bg, bg, bg)
    )


def _failed_ids(img: Image.Image, tmp_path) -> set[str]:
    report = LocalQualityChecker(_settings(tmp_path)).run(img)
    return {c.id for c in report.checks if not c.passed}


def _mean_luma(img: Image.Image) -> float:
    data = list(img.convert("L").getdata())
    return sum(data) / len(data)


# ---------------------------------------------------------------- 质检矩阵
def test_quality_accepts_normal_page(tmp_path):
    report = LocalQualityChecker(_settings(tmp_path)).run(_page())
    assert report.passed is True
    assert report.ruleset_version == "v1.0"


def test_quality_rejects_blur(tmp_path):
    blurred = _page().filter(ImageFilter.GaussianBlur(radius=12))
    report = LocalQualityChecker(_settings(tmp_path)).run(blurred)
    assert report.passed is False
    assert "blur" in {c.id for c in report.checks if not c.passed}


def test_quality_rejects_too_dark(tmp_path):
    img = _page(bg=15)
    assert _mean_luma(img) < 40
    assert "too_dark" in _failed_ids(img, tmp_path)


def test_quality_rejects_too_bright(tmp_path):
    img = Image.new("RGB", (900, 660), (250, 250, 250))
    assert "too_bright" in _failed_ids(img, tmp_path)


def test_quality_rejects_occlusion(tmp_path):
    img = _page()
    ImageDraw.Draw(img).rectangle([270, 230, 630, 450], fill=0)  # 中心大块深色遮挡
    assert "occlusion" in _failed_ids(img, tmp_path)


def test_quality_rejects_page_crop(tmp_path):
    img = _page()
    ImageDraw.Draw(img).rectangle([0, 0, 100, 660], fill=0)  # 左侧内容贴边（页角裁切信号）
    assert "page_crop" in _failed_ids(img, tmp_path)


def test_quality_rejects_tilt(tmp_path):
    img = _rotated_page(20)
    assert "tilt" in _failed_ids(img, tmp_path)


def test_quality_disabled_rule_is_skipped(tmp_path):
    settings = _settings(tmp_path)
    settings = M002Settings(**{**settings.model_dump(), "quality_page_crop_enabled": False})
    img = _page()
    ImageDraw.Draw(img).rectangle([0, 0, 100, 660], fill=0)
    report = LocalQualityChecker(settings).run(img)
    assert report.passed is True
    assert "page_crop" not in {c.id for c in report.checks}


# ---------------------------------------------------------------- 归一
def test_normalizer_white_composite_and_long_side(tmp_path):
    img = Image.new("RGBA", (2200, 200), (0, 0, 0, 0))  # 全透明长图
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 400, 200], fill=(200, 0, 0, 255))  # 左段不透明内容
    jpeg, size = Normalizer(_settings(tmp_path)).normalize(img)
    assert size[0] == 2000  # 长边 2200 → 2000
    assert size[1] == 181
    opened = Image.open(io.BytesIO(jpeg))
    assert opened.format == "JPEG"
    # 缩放系数 ≈ 2000/2200 = 0.909；内容段覆盖输出 x≈0..363，透明段在右侧
    assert opened.getpixel((1800, 90)) == (255, 255, 255)  # 透明段白底合成
    assert opened.getpixel((200, 90)) == (200, 0, 0)  # 内容段保留红色调


def _exif_bytes(orientation: int) -> bytes:
    """最小 EXIF（IFD0 tag 0x0112 Orientation），供 exif_transpose 识别。"""
    tiff = b"II" + struct.pack("<H", 42) + struct.pack("<I", 8)
    tiff += struct.pack("<H", 1)
    tiff += struct.pack("<HHII", 0x0112, 3, 1, orientation)
    tiff += struct.pack("<I", 0)
    return b"Exif\x00\x00" + tiff


def test_normalizer_exif_orientation(tmp_path):
    img = _page()
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=_exif_bytes(6))  # orientation 6 = 旋转 90°
    buf.seek(0)
    w, h = Image.open(buf).size
    jpeg, size = Normalizer(_settings(tmp_path)).normalize(Image.open(buf))
    assert size == (h, w)  # 方向矫正生效（宽高互换）


# ---------------------------------------------------------------- 本地存储
def test_image_store_roundtrip_and_delete(tmp_path):
    store = ImageStore(tmp_path)
    data = b"\x89PNG\r\n\x1a\n" + b"x" * 64
    rel_dir = store.batch_rel_dir("fam1", "batch1")
    rel, sha = store.save_original(rel_dir, seq_no=1, photo_id="p1", data=data, mime="image/png")
    assert sha == hashlib.sha256(data).hexdigest()
    nrel = store.save_normalized(rel_dir, seq_no=1, photo_id="p1", data=b"jpeg")
    assert store.read(rel) == data
    assert store.abs_path(rel).exists()
    store.delete(rel, nrel)
    assert not store.abs_path(rel).exists()
    store.delete(rel)  # 幂等
