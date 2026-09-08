"""作业任务 Schema（API-M001-007~011）。"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.m001.schemas.common import PageMeta

ItemType = Literal["objective", "subjective"]
TaskStatus = Literal["draft", "published", "in_progress", "closed"]
TaskAction = Literal["publish", "close", "reopen"]

_MAX_STEM = 2000
_MAX_ANSWER = 2000


class TaskItemIn(BaseModel):
    seq: int = Field(ge=1)
    item_type: ItemType
    subject: str = Field(min_length=1, max_length=32)
    stem: str = Field(min_length=1, max_length=_MAX_STEM)
    reference_answer: str | None = Field(default=None, max_length=_MAX_ANSWER)

    @model_validator(mode="after")
    def _check_answer_rules(self):
        # 客观题参考答案可选；主观题禁止参考答案（ADR-006：主观题只评质量不判对错，防误导）
        if self.item_type == "subjective":
            if self.reference_answer is not None and self.reference_answer.strip():
                raise ValueError("主观题不允许录入参考答案")
            self.reference_answer = None
        else:
            if self.reference_answer is not None and not self.reference_answer.strip():
                self.reference_answer = None
        return self


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=64)
    subject: str = Field(min_length=1, max_length=32)
    grade_level: str | None = Field(default=None, max_length=64)
    content: str | None = Field(default=None, max_length=_MAX_STEM)
    student_id: UUID
    deadline: datetime | None = None
    items: list[TaskItemIn] = Field(min_length=1)


class TaskUpdate(BaseModel):
    """PATCH：可改 标题/内容/截止时间/题目集（仅 draft/published 且未开始上传）。"""

    title: str | None = Field(default=None, min_length=1, max_length=64)
    content: str | None = Field(default=None, max_length=_MAX_STEM)
    deadline: datetime | None = None  # null = 清除截止时间
    items: list[TaskItemIn] | None = Field(default=None, min_length=1)


class TaskItemOut(BaseModel):
    """题目输出。reference_answer 默认不外泄；include_answers=true 时客观题返回。"""

    seq: int
    item_type: ItemType
    subject: str
    stem: str
    reference_answer: str | None = None


class TaskDetailDTO(BaseModel):
    task_id: UUID
    student_id: UUID
    title: str
    subject: str
    grade_level: str | None
    content: str | None
    status: TaskStatus
    deadline: str | None
    created_at: str
    updated_at: str
    items: list[TaskItemOut]


class TaskSummaryDTO(BaseModel):
    task_id: UUID
    student_id: UUID
    student_name: str
    title: str
    subject: str
    grade_level: str | None
    status: TaskStatus
    deadline: str | None
    item_count: int
    created_at: str
    updated_at: str


class TaskListResponse(PageMeta):
    items: list[TaskSummaryDTO]


class TaskStatusAction(BaseModel):
    action: TaskAction


class TaskStatusResult(BaseModel):
    task_id: UUID
    status: TaskStatus
