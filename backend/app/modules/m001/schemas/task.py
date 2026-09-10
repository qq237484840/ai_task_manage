"""作业任务 Schema（MODULE_API.md v0.2.0 / API-M001-007~011、018、021）。

- `TaskDTO`（事实层按天）= { task_id, student_id, category, belong_date, week_index, window_type,
  spec_status, title, grade_level, status, deadline, contents, sources, created_at, updated_at }
- `ContentItemDTO` / `SourceDTO` 见 MODULE_API DTO 约定
- `TaskItemIn`/`TaskItemOut`/`TaskGroupSegmentDTO` 为 **Deprecated 兼容面**（`task_items` 退役），
  仅保留给旧内部方法签名，新链路不得使用。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.m001.schemas.common import PageMeta

TaskStatus = Literal["draft", "published", "in_progress", "closed"]
TaskAction = Literal["publish", "close", "reopen"]
SpecStatus = Literal["placeholder", "parsed", "confirmed"]
SourceKind = Literal["text", "image"]
WindowType = Literal["day", "weekend", "holiday"]
Category = Literal["school"]

# Deprecated（task_items 退役）：保留枚举与逐题 DTO 供旧签名使用
ItemType = Literal["objective", "subjective"]

_MAX_TEXT = 2000
_MAX_SOURCE_TEXT = 4000
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# —— 输入源与创建（API-M001-007） ——
class SourceIn(BaseModel):
    """任务输入源段落（图片 / 粘贴文本）。上传无需填写内容。"""

    seq: int = Field(ge=1)
    kind: SourceKind
    text_content: str | None = Field(default=None, max_length=_MAX_SOURCE_TEXT)
    photo_id: UUID | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.kind == "text":
            text = (self.text_content or "").strip()
            if not text:
                raise ValueError("kind=text 时 text_content 不能为空")
            self.text_content = text
            self.photo_id = None
        else:  # image
            if self.photo_id is None:
                raise ValueError("kind=image 时 photo_id 不能为空")
            self.text_content = None
        return self


class TaskIngest(BaseModel):
    """上传任务输入源（`POST /tasks`）。"""

    student_id: UUID
    category: Category = "school"
    grade_level: str | None = Field(default=None, max_length=64)
    sources: list[SourceIn] = Field(min_length=1, max_length=50)

    @field_validator("grade_level")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class ContentItemIn(BaseModel):
    """内容项（确认/更新入参；`content_id` 提供时用于对齐已有项）。"""

    content_id: UUID | None = None
    subject: str = Field(min_length=1, max_length=32)
    text: str = Field(min_length=1, max_length=_MAX_TEXT)

    @field_validator("subject")
    @classmethod
    def _norm_subject(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("学科不能为空")
        return v

    @field_validator("text")
    @classmethod
    def _strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("内容项文本不能为空")
        return v


class ParseDigest(BaseModel):
    """隐式确认摘要（M002 判定链携带，用于「一并落库」前展示）。"""

    subjects: list[str] = []
    content_texts: list[str] = []


class ParseConfirmation(BaseModel):
    """解析结果确认（API-M001-018；含隐式确认 C7）。"""

    confirmed: bool = True
    contents: list[ContentItemIn] | None = None
    implicit: bool = False
    digest: ParseDigest | None = None

    @model_validator(mode="after")
    def _implicit_requires_digest(self):
        if self.implicit and self.digest is None:
            raise ValueError("implicit=true 时必须携带 digest（避免盲确认）")
        return self


class BelongDateChange(BaseModel):
    """手工改归属日（API-M001-021）。"""

    belong_date: str

    @field_validator("belong_date")
    @classmethod
    def _valid_date(cls, v: str) -> str:
        v = (v or "").strip()
        if not _DATE_RE.match(v):
            raise ValueError("belong_date 必须为 YYYY-MM-DD")
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("belong_date 非法日期") from exc
        return v


class TaskUpdate(BaseModel):
    """PATCH：改 `title`/`grade_level`/`deadline` + 内容项增删改（归属字段不可经此修改）。"""

    title: str | None = Field(default=None, min_length=1, max_length=64)
    grade_level: str | None = Field(default=None, max_length=64)
    deadline: datetime | None = None  # null = 清除截止时间
    contents: list[ContentItemIn] | None = Field(default=None, max_length=200)  # 提供则整体替换


# —— 输出 DTO ——
class ContentItemDTO(BaseModel):
    content_id: UUID
    subject: str
    seq: int
    text: str


class SourceDTO(BaseModel):
    source_id: UUID
    seq: int
    kind: SourceKind
    text_content: str | None = None
    photo_id: UUID | None = None


class TaskDTO(BaseModel):
    """事实层按天任务（API-M001-007/009/021 响应）。"""

    task_id: UUID
    student_id: UUID
    category: str
    belong_date: str
    week_index: int
    window_type: WindowType
    spec_status: SpecStatus
    title: str
    grade_level: str | None
    status: TaskStatus
    deadline: str | None
    contents: list[ContentItemDTO] = []
    sources: list[SourceDTO] = []
    created_at: str
    updated_at: str


class TaskSummaryDTO(BaseModel):
    task_id: UUID
    student_id: UUID
    student_name: str
    category: str
    belong_date: str
    week_index: int
    window_type: WindowType
    spec_status: SpecStatus
    title: str
    grade_level: str | None
    status: TaskStatus
    deadline: str | None
    content_count: int
    source_count: int
    created_at: str
    updated_at: str


class TaskListResponse(PageMeta):
    items: list[TaskSummaryDTO]


class TaskStatusAction(BaseModel):
    action: TaskAction


class TaskStatusResult(BaseModel):
    task_id: UUID
    status: TaskStatus


# —— Deprecated 兼容面（task_items 退役；仅旧内部方法使用） ——
class TaskItemIn(BaseModel):
    seq: int = Field(ge=1)
    item_type: ItemType
    subject: str = Field(min_length=1, max_length=32)
    group_no: int = Field(default=0, ge=0)
    stem: str = Field(min_length=1, max_length=_MAX_TEXT)
    reference_answer: str | None = Field(default=None, max_length=_MAX_TEXT)


class TaskItemOut(BaseModel):
    seq: int
    item_type: ItemType
    subject: str
    group_no: int
    stem: str
    reference_answer: str | None = None


class TaskGroupSegmentDTO(BaseModel):
    """Deprecated：任务内某学科作业段（CR-001 语义，ADR-013 作废）。"""

    task_id: UUID
    student_id: UUID
    title: str
    subject: str
    group_no: int
    item_count: int
    items: list[TaskItemOut]
