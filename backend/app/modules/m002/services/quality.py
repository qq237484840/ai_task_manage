"""本地规则质检（契约 D1/D4：QualityChecker 协议 + LocalQualityChecker v1.0）。

范围声明（诚实边界，见 MODULE_DESIGN 决策 5/6）：
- 硬校验（format / size / 像素上限）由上传管线先行处理（415/413/422），不在本文件重复。
- 规则项 blur/too_dark/too_bright 为确定性强信号；tilt/occlusion/page_crop 为
  「可解释 + 可配置」近似启发式（检测尺度/判定阈值登记于 M002Settings），不声称像素级精确。
- 输出 QualityReport{passed, checks[]}：任一 reject 级未过 → passed=False（不入库）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image, ImageFilter

from app.modules.m002.config import M002Settings


@dataclass(frozen=True)
class QualityCheckItem:
    id: str
    passed: bool
    value: float | None = None
    threshold: float | None = None
    severity: str = "reject"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "passed": self.passed,
            "value": self.value,
            "threshold": self.threshold,
            "severity": self.severity,
        }


@dataclass
class QualityReport:
    ruleset_version: str
    passed: bool
    checks: list[QualityCheckItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ruleset_version": self.ruleset_version,
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
        }


class QualityChecker:
    """质检协议：run(已解码 PIL.Image) -> QualityReport。"""

    def run(self, image: Image.Image) -> QualityReport:
        raise NotImplementedError


def _luma_preview(image: Image.Image, side: int) -> Image.Image:
    """统一尺度灰度预览：启发式全部在此尺度计算以保证确定性。"""
    img = image.convert("L")
    w, h = img.size
    scale = min(1.0, side / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BILINEAR)
    return img


def _mean(data: list[int]) -> float:
    return sum(data) / len(data)


def _variance(data: list[int]) -> float:
    n = len(data)
    m = _mean(data)
    return sum((x - m) ** 2 for x in data) / n


def _float_laplacian_variance(image: Image.Image) -> float:
    """4-邻域浮点拉普拉斯方差（不经过字节裁剪），用于 blur 规则。

    仅对灰度图 ``image`` 的内部像素计算，保持边缘处理简洁且与预览尺度解耦。
    """
    g = image.convert("L")
    w, h = g.size
    px = list(g.getdata())
    s, s2, n = 0.0, 0.0, 0
    for y in range(1, h - 1):
        base = y * w
        for x in range(1, w - 1):
            i = base + x
            lap = 4 * px[i] - px[i - 1] - px[i + 1] - px[i - w] - px[i + w]
            s += lap
            s2 += lap * lap
            n += 1
    if n == 0:
        return 0.0
    mean = s / n
    return s2 / n - mean * mean


class LocalQualityChecker(QualityChecker):
    """本地规则 v1.0：确定性、全部阈值来自 M002Settings（禁止硬编码）。"""

    def __init__(self, settings: M002Settings):
        self.s = settings

    # —— 规则项 ——
    def _blur(self, preview: Image.Image) -> QualityCheckItem:
        """模糊：浮点拉普拉斯方差；值低于阈值判为模糊（reject）。"""
        side = self.s.quality_blur_probe_side
        probe = _luma_preview(preview, side)
        value = _float_laplacian_variance(probe)
        th = self.s.quality_blur_laplacian_min
        return QualityCheckItem("blur", value >= th, round(value, 1), th, "reject")

    def _luma(self, preview: Image.Image) -> list[QualityCheckItem]:
        value = _mean(list(preview.getdata()))
        lo, hi = self.s.quality_luma_min, self.s.quality_luma_max
        return [
            QualityCheckItem("too_dark", value >= lo, round(value, 1), lo, "reject"),
            QualityCheckItem("too_bright", value <= hi, round(value, 1), hi, "reject"),
        ]

    def _tilt(self, preview: Image.Image) -> QualityCheckItem:
        """主轴倾斜近似：将文本行对齐的旋转角视为主轴（行投影方差在文本行水平时最大）。

        双线性预览 → 二值化 → [-15..15]° 步进 3° 扫描行投影方差 → 最大者为主轴角绝对量。
        """
        probe = _luma_preview(preview, self.s.quality_tilt_probe_side)
        best_score, best_angle = -1.0, 0.0
        for angle in range(-15, 16, 3):
            rot = probe.rotate(
                -angle, resample=Image.BICUBIC, expand=True, fillcolor=255
            )
            data = list(rot.getdata())
            wt, ht = rot.size
            row_counts = [
                sum(1 for x in range(wt) if data[y * wt + x] < 128) for y in range(ht)
            ]
            score = _variance(row_counts)
            if score > best_score:
                best_score, best_angle = score, abs(float(angle))
        th = self.s.quality_tilt_max_deg
        return QualityCheckItem(
            "tilt", best_angle <= th, best_angle, th, self.s.quality_tilt_severity
        )

    def _grid16(self, preview: Image.Image) -> list[int]:
        g = preview.resize((16, 16), Image.BILINEAR)
        return list(g.getdata())

    def _occlusion(self, preview: Image.Image) -> QualityCheckItem:
        """中心区低亮度异常块占比（近似深色遮挡物信号）。中心 = 16×16 格的 12×12 内区。"""
        cells = self._grid16(preview)
        dark_luma = self.s.quality_occlusion_dark_luma
        center = [cells[r * 16 + c] for r in range(2, 14) for c in range(2, 14)]
        ratio = sum(1 for v in center if v < dark_luma) / len(center)
        th = self.s.quality_occlusion_max_ratio
        return QualityCheckItem(
            "occlusion", ratio <= th, round(ratio, 4), th, self.s.quality_occlusion_severity
        )

    def _page_crop(self, preview: Image.Image) -> QualityCheckItem:
        """页边裁切近似：内容贴边信号 —— 4 个外边格（16 格侧边）的低亮度占比超限即判定。"""
        cells = self._grid16(preview)
        ink = self.s.quality_page_crop_ink_luma
        sides = {
            "top": cells[0:16],
            "bottom": cells[240:256],
            "left": cells[0::16],
            "right": cells[15::16],
        }
        worst = max(sum(1 for v in vals if v < ink) / 16 for vals in sides.values())
        th = self.s.quality_page_crop_max_ratio
        return QualityCheckItem(
            "page_crop", worst <= th, round(worst, 4), th, self.s.quality_page_crop_severity
        )

    # —— 协议实现 ——
    def run(self, image: Image.Image) -> QualityReport:
        s = self.s
        preview = _luma_preview(image, s.quality_preview_side)
        checks: list[QualityCheckItem] = [self._blur(preview)]
        checks.extend(self._luma(preview))
        if s.quality_tilt_enabled:
            checks.append(self._tilt(preview))
        if s.quality_occlusion_enabled:
            checks.append(self._occlusion(preview))
        if s.quality_page_crop_enabled:
            checks.append(self._page_crop(preview))
        passed = all(not (c.severity == "reject" and not c.passed) for c in checks)
        return QualityReport(ruleset_version=s.quality_ruleset_version, passed=passed, checks=checks)
