"""作业任务 Schema（API-M001-007~011；随 CHANGE-001 容器化 + group_no）。"""

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
_MIXED_SUBJECT = "mixed"  # 多学科登记单：tasks.subject 使用该值


class TaskItemIn(BaseModel):
    seq: int = Field(ge=1)
    item_type: ItemType
    subject: str = Field(min_length=1, max_length=32)
    group_no: int = Field(default=0, ge=0)  # 学科作业段号（CR-001；0=默认单段）
    stem: str = Field(min_length=1, max_length=_MAX_STEM)
    reference_answer: str | None = Field(default=None, max_length=_MAX_ANSWER)

    @field_validator("subject")
    @classmethod
    def _norm_subject(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("科目不能为空")
        return v.lower()

    @model_validator(mode="after")
    def _check_answer_rules(self):
        # reference_answer 仅为**非判定基准**辅助字段（ADR-010：判定链端到端直判）。
        # 主观题不维护参考答案（防误导）；客观题可选。
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
    # subject：登记单主学科标注（CR-001 放宽）。单学科任务传学科名；多学科任务不传或传 'mixed'。
    subject: str | None = Field(default=None, min_length=1, max_length=32)
    grade_level: str | None = Field(default=None, max_length=64)
    content: str | None = Field(default=None, max_length=_MAX_STEM)
    student_id: UUID
    deadline: datetime | None = None
    items: list[TaskItemIn] = Field(min_length=1)

    @field_validator("subject")
    @classmethod
    def _norm_subject(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        # 保留 'mixed' 字面语义；其余一律规范化小写
        return _MIXED_SUBJECT if v.lower() == _MIXED_SUBJECT else v.lower()


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
    group_no: int
    stem: str
    reference_answer: str | None = None


class TaskDetailDTO(BaseModel):
    task_id: UUID
    student_id: UUID
    title: str
    subject: str | None  # 可空：多学科登记单容器（CR-001）
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
    subject: str | None
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


class TaskGroupSegmentDTO(BaseModel):
    """任务内一个学科作业段（CR-001；供 M002 归属目标校验/识别输入）。"""

    task_id: UUID
    student_id: UUID
    title: str
    subject: str
    group_no: int
    item_count: int
    items: list[TaskItemOut]
