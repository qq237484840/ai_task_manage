"""M002 运行配置（契约 MODULE_CONTRACT Configuration 表登记）。

- 环境变量前缀 `AT_M002_`（如 AT_M002_UPLOAD_MAX_PHOTOS_PER_BATCH）；env_file 支持 .env。
- 默认值 = 契约 v0.3.0 Configuration 表；所有质检/归一/上限阈值集中于此，禁止硬编码散落。
- 图片根目录默认 `<项目根>/backend/data/images`（ASM-010 本地受控目录，随部署整体备份）。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[4]  # backend/app/modules/m002/config.py -> 项目根


class M002Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AT_M002_", env_file=".env", extra="ignore")

    app_name_m002: str = "AI Task Management (M002 作业图片采集与归属)"

    # —— 上传（upload.*）——
    upload_max_photos_per_batch: int = 50  # 单批次上限（D5，422 batch_photo_limit）

    # —— 图片硬校验（image.*）——
    image_accept_mimes: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")
    image_max_size_bytes: int = 10 * 1024 * 1024  # 单图大小上限（413）
    image_max_pixels: int = 60_000_000  # 解码像素上限（422）

    # —— 质检规则（quality.*，v1.0 本地规则）——
    quality_ruleset_version: str = "v1.0"
    quality_blur_laplacian_min: float = 100.0  # 灰度拉普拉斯方差下限（模糊 → reject）
    quality_luma_min: float = 40.0  # 过暗：灰度均值下限
    quality_luma_max: float = 215.0  # 过亮：灰度均值上限
    # 倾斜（启发式，severity 可配 reject|warn）
    quality_tilt_enabled: bool = True
    quality_tilt_max_deg: float = 12.0
    quality_tilt_severity: str = "reject"
    # 遮挡（启发式：中心区低亮度异常块占比）
    quality_occlusion_enabled: bool = True
    quality_occlusion_severity: str = "reject"
    quality_occlusion_dark_luma: float = 90.0  # 中心格「过暗块」判定亮度
    quality_occlusion_max_ratio: float = 0.08  # 中心区过暗格占比上限
    # 缺页/页角裁切（启发式：内容贴边近似信号）
    quality_page_crop_enabled: bool = True
    quality_page_crop_severity: str = "reject"
    quality_page_crop_ink_luma: float = 100.0  # 贴边格判定亮度
    quality_page_crop_max_ratio: float = 0.5  # 单边贴边格占比上限
    # 质检分析用预览长边（启发式在统一尺度上计算，保证确定性）
    quality_preview_side: int = 1024
    quality_blur_probe_side: int = 320  # 模糊探测进一步降采样边长（浮点 Laplacian）
    quality_tilt_probe_side: int = 160  # 倾斜探测进一步降采样边长

    # —— 归一（normalized.*，D2）——
    normalized_max_side_px: int = 2000  # 长边上限
    normalized_jpeg_quality: int = 88  # 归一图 JPEG 质量

    # —— 入口 kind（batch.kind；菜单决定，后端冗余）——
    batch_kinds: tuple[str, ...] = ("task_spec", "homework")
    batch_default_kind: str = "homework"

    # —— 归属/挂接上限（association.*，D5）——
    association_max_photos_per_task: int = 200  # 单窗口任务已 assigned 照片上限（409）
    association_max_photos_per_subject: int = 50  # 单聚合学科子任务挂接照片上限（409）
    association_suggestion_enabled: bool = True  # 上传后异步挂接建议总开关
    association_suggestion_top_k: int = 3  # 单照片最多采纳的 AI 建议数

    # —— 完成分析（analysis.*，ADR-013）——
    analysis_gate_enabled: bool = True  # 窗口级门控：全部照片确认挂接后才分析
    analysis_evidence_max_photos: int = 20  # 单次分析最多取用依据照片数
    ai_suggestion_timeout_seconds: int = 20  # AI 挂接建议超时（超时降级）
    ai_analysis_timeout_seconds: int = 60  # AI 完成分析超时（超时降级为无法判断）

    # —— 图片存储（image_store.root，ASM-010）——
    image_store_root: str = str(_PROJECT_ROOT / "backend" / "data" / "images")

    # —— 分页（与 M001 一致）——
    pagination_default_size: int = 20
    pagination_max_size: int = 100

    @property
    def image_root(self) -> Path:
        return Path(self.image_store_root)


@lru_cache
def get_m002_settings() -> M002Settings:
    return M002Settings()
