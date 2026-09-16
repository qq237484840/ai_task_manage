"""布置单图片源读取 —— 回调槽（`CR-005` / M001 v0.3.0）。

跨模块唯一通道 = **回调注册**（与 `aggregation_service.register_links_migration_hook` 同模式）：
M001 定义槽 → M002 **导入期**注册实现 → `main.py` **启动期**幂等自愈。
M001 **不 import M002**（分层约束）。

消费方 = M001 链路 T（`task_parser._to_ai_sources`）：**仅当 Vision Provider 为真实**
（非 Mock / 非 degraded）时才调用 —— Mock 无视觉能力，硬转发会产出占位草稿（伪造，
`BUG-004` 教训）。未注册 / 取图失败 → `None`，调用方按「不转发该源」处理（保持 `placeholder`）。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaskSourceImage:
    """布置单图片引用（**受控本地路径，仅限同机进程内读取，不外发任何 API 响应**）。"""

    mime: str
    abs_path: str


#: 实现签名：`fn(session, family_id, photo_id) -> TaskSourceImage | None`（M002 提供，`CR-005`）。
ImageProvider = Callable[..., "TaskSourceImage | None"]

_task_spec_image_provider: ImageProvider | None = None


def register_task_spec_image_provider(fn: ImageProvider | None) -> None:
    """注册布置单图片源读取实现（M002 导入期调用；传 `None` 可清空，供启动期兜底/测试）。"""
    global _task_spec_image_provider
    _task_spec_image_provider = fn


def get_task_source_image(session: object, family_id: str, photo_id: str) -> TaskSourceImage | None:
    """经已注册实现取图；**未注册 / 实现抛错 → `None`**（不报错、不阻断链路 T）。"""
    fn = _task_spec_image_provider
    if fn is None:
        return None
    try:
        return fn(session, family_id, photo_id)
    except Exception as exc:  # noqa: BLE001 - 取图失败按「不转发」处理
        logger.warning("布置单图片源读取失败（photo=%s）：%s", photo_id, exc)
        return None


__all__ = [
    "TaskSourceImage",
    "register_task_spec_image_provider",
    "get_task_source_image",
]
