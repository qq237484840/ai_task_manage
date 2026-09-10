"""聚合层与归属窗口 Schema（MODULE_API.md v0.2.0 / API-M001-019~020）。

- `WindowInfo`：`WindowResolver.resolve` 返回的归属窗口快照（纯计算产物）
- `TaskGroupDTO`：聚合任务（`task_groups`）
- `TaskGroupSubjectDTO`：★判定单元（`task_group_subjects`；结论由 M002 经内部接口回写）
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.modules.m001.schemas.common import PageMeta

WindowType = Literal["day", "weekend", "holiday"]
ConclusionStatus = Literal["pending", "draft", "confirmed"]


class WindowInfo(BaseModel):
    """归属窗口：`belong_date` / `week_index` / `window_type` / `group_key`。"""

    belong_date: str  # YYYY-MM-DD（AT_TIMEZONE + AT_DAY_CUTOFF 计算）
    week_index: int
    window_type: WindowType
    group_key: str  # day→belong_date；weekend→W:<周五>；holiday→H:<周起始>.W<n>


class TaskGroupSubjectDTO(BaseModel):
    """聚合学科子任务（★判定单元）。"""

    group_subject_id: UUID
    subject: str
    content_refs: list[UUID] = []
    conclusion: str | None = None
    conclusion_status: ConclusionStatus = "pending"


class TaskGroupDTO(BaseModel):
    """聚合任务（展示/挂接/判定统一载体）。"""

    group_id: UUID
    student_id: UUID
    category: str
    group_key: str
    display_name: str
    window_type: WindowType
    policy_version: str
    subjects: list[TaskGroupSubjectDTO] = []
    created_at: str


class TaskGroupListResponse(PageMeta):
    items: list[TaskGroupDTO]
