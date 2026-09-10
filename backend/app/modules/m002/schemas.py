"""M002 契约 DTO / 请求模型（对外 REST 与内部服务共用，v0.4.0）。

文件本地路径绝不进入对外响应：对外 PhotoDTO 不含路径。
挂接（photo_subject_links）与完成分析（completion_analyses）为 v0.4.0 新增契约面。
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.m001.schemas.common import PageMeta

PhotoStatusValue = Literal["unassigned", "suggested", "assigned", "rejected"]
BatchKindValue = Literal["task_spec", "homework"]
LinkSourceValue = Literal["ai", "manual"]
LinkActionValue = Literal["accept", "reject", "relink"]
AnalysisStatusValue = Literal["draft", "confirmed"]
ConclusionValue = Literal["完成", "部分完成", "未完成", "无法判断"]


# ---------------------------------------------------------------- 通用
class ContentUrlsOut(BaseModel):
    """取图入口（REST 相对路径；kind=original|normalized，支持 Range）。"""

    original: str
    normalized: str


class QualityCheckItem(BaseModel):
    id: str
    passed: bool
    value: float | None = None
    threshold: float | None = None
    severity: str


class QualityReportOut(BaseModel):
    ruleset_version: str
    passed: bool
    checks: list[QualityCheckItem] = Field(default_factory=list)


# ---------------------------------------------------------------- 挂接
class LinkDTO(BaseModel):
    """照片↔聚合学科子任务挂接（N:N）。subject 为展示用学科名（解析失败可空）。"""

    link_id: UUID
    group_subject_id: UUID
    subject: str | None = None
    source: LinkSourceValue
    confidence: float | None = None
    confirmed_at: str | None = None
    rejected_at: str | None = None
    created_at: str


class LinkReviewIn(BaseModel):
    """API-M002-005 复核请求（accept/reject/relink）。

    - accept：link_id（确认既有建议）或 group_subject_id（手工兜底新建并确认）；
    - reject：link_id 或 group_subject_id（判无效）；
    - relink：link_id（旧）+ group_subject_id（新）。
    """

    action: LinkActionValue
    link_id: UUID | None = None
    group_subject_id: UUID | None = None


class LinkSuggestionItemOut(BaseModel):
    link_id: UUID
    group_subject_id: UUID
    subject: str | None = None
    confidence: float | None = None
    source: LinkSourceValue
    suggested_at: str


class LinkSuggestionOut(BaseModel):
    """API-M002-007 挂接建议（当前有效、未确认的建议）。"""

    photo_id: UUID
    status: PhotoStatusValue
    suggestions: list[LinkSuggestionItemOut] = Field(default_factory=list)


class GateStatusDTO(BaseModel):
    """API-M002-008 窗口级门控。satisfied = 窗口全部照片已确认挂接。"""

    group_key: str
    window_type: str
    total_photos: int
    pending_photos: int
    satisfied: bool


# ---------------------------------------------------------------- 照片 / 批次
class PhotoDTO(BaseModel):
    """对外照片（不含本地路径）。links 为当前挂接；task_id 仅窗口级冗余。"""

    photo_id: UUID
    batch_id: UUID
    student_id: UUID
    seq_no: int
    kind: BatchKindValue
    status: PhotoStatusValue
    task_id: UUID | None = None
    links: list[LinkDTO] = Field(default_factory=list)
    quality: QualityReportOut
    content_urls: ContentUrlsOut
    created_at: str


class PhotoListResponse(PageMeta):
    items: list[PhotoDTO]


class LinkReviewOut(BaseModel):
    photo_id: UUID
    status: PhotoStatusValue
    task_id: UUID | None = None
    links: list[LinkDTO] = Field(default_factory=list)
    gate: GateStatusDTO | None = None


class BatchBriefOut(BaseModel):
    batch_id: UUID
    student_id: UUID
    kind: BatchKindValue


class UploadPhotoOut(BaseModel):
    """POST /photos 201 响应。"""

    photo_id: UUID
    batch: BatchBriefOut
    seq_no: int
    kind: BatchKindValue
    status: PhotoStatusValue
    quality: QualityReportOut
    content_urls: ContentUrlsOut


class BatchCreateIn(BaseModel):
    """POST /upload-batches 请求体（student 主体会忽略 student_id 强制本人）。

    kind 由菜单入口决定：「任务」→ task_spec，「作业」→ homework；缺省 homework。
    """

    student_id: UUID | None = None
    kind: BatchKindValue = "homework"


class BatchOut(BaseModel):
    batch_id: UUID
    family_id: UUID
    student_id: UUID
    kind: BatchKindValue
    created_by_type: str
    created_by_id: UUID
    created_at: str


# ---------------------------------------------------------------- 完成分析
class AnalysisCreateIn(BaseModel):
    """API-M002-009 生成分析（窗口级）。"""

    student_id: UUID | None = None
    group_key: str


class AnalysisItemOut(BaseModel):
    analysis_id: UUID
    group_subject_id: UUID
    subject: str | None = None
    conclusion: ConclusionValue
    evidence_photo_ids: list[UUID] = Field(default_factory=list)
    confidence: float | None = None
    status: AnalysisStatusValue
    model: str | None = None
    prompt_version: str | None = None
    run_no: int
    confirmed_by: UUID | None = None
    confirmed_at: str | None = None
    created_at: str


class AnalysisGenerateOut(BaseModel):
    group_key: str
    items: list[AnalysisItemOut] = Field(default_factory=list)


class AnalysisConfirmIn(BaseModel):
    """API-M002-010 家长确认（可选覆盖结论）。"""

    conclusion: ConclusionValue | None = None
