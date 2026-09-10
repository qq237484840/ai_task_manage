"""轻量归一（契约 D2 / MODULE_DESIGN 决策 7，本地确定性规则）。

1) EXIF 方向矫正（ImageOps.exif_transpose）
2) 透明通道（PNG RGBA/LA/P+transparency）→ 白底合成 RGB
3) 长边 > 2000 → 等比缩放（LANCZOS）
4) 统一 JPEG 输出（质量 88）
归一阈值登记于 M002Settings.normalized_*（禁止硬编码）。
"""
from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps

from app.modules.m002.config import M002Settings


class Normalizer:
    def __init__(self, settings: M002Settings):
        self.s = settings

    def normalize(self, image: Image.Image) -> tuple[bytes, tuple[int, int]]:
        im = ImageOps.exif_transpose(image)
        has_alpha = im.mode in ("RGBA", "LA") or (
            im.mode == "P" and "transparency" in im.info
        )
        if has_alpha:
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        w, h = im.size
        side = max(w, h)
        if side > self.s.normalized_max_side_px:
            scale = self.s.normalized_max_side_px / side
            im = im.resize(
                (max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS
            )
        buf = BytesIO()
        im.save(buf, format="JPEG", quality=self.s.normalized_jpeg_quality)
        return buf.getvalue(), im.size
