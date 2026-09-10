"""AI 返回结构 schema（**所有** AI 输出必须解析为本文件模型，否则丢弃）。

字段边界对齐 M001/M002 契约（v0.2.0 / v0.4.0）：
- `TaskSpecParseResult.subjects[].subject` + `contents[].text` → 落 `task_contents(subject,text)`；
- `PhotoLinkSuggestionResult.links[].group_subject_id` → 对齐 M002 `LinkDTO.group_subject_id`（N:N）；
- `CompletionAnalysisResult.conclusion` → 对齐 `完成/部分完成/未完成/无法判断`。

约束（ADR-003）：只承载可观察描述，schema 层不接受主观标签字段。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ConclusionValue = Literal["完成", "部分完成", "未完成", "无法判断"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")  # 拒绝多余字段，避免未定义输出流入上游


class ParsedContentItem(_StrictModel):
    """解析出的内容项（仅文本；V1 只读展示，不参与判定）。"""

    text: str = Field(min_length=1, max_length=500)


class ParsedSubject(_StrictModel):
    """解析出的学科子任务（草稿）。"""

    subject: str = Field(min_length=1, max_length=32)
    contents: list[ParsedContentItem] = Field(default_factory=list, max_length=100)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("subject")
    @classmethod
    def _norm_subject(cls, v: str) -> str:
        return v.strip().lower()


class TaskSpecParseResult(_StrictModel):
    """① 任务输入源解析结果。"""

    subjects: list[ParsedSubject] = Field(default_factory=list, max_length=30)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class SuggestedLink(_StrictModel):
    """单条挂接建议（对齐 M002 LinkDTO 的 group_subject_id/subject/confidence）。"""

    group_subject_id: str = Field(min_length=1, max_length=64)
    subject: str = Field(min_length=1, max_length=32)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("subject")
    @classmethod
    def _norm_subject(cls, v: str) -> str:
        return v.strip().lower()


class PhotoLinkSuggestionResult(_StrictModel):
    """② 照片 → 聚合学科子任务 N:N 挂接建议。"""

    links: list[SuggestedLink] = Field(default_factory=list, max_length=30)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class CompletionAnalysisResult(_StrictModel):
    """③ 聚合子任务级完成结论（含 `无法判断` 出口）。"""

    conclusion: ConclusionValue
    evidence_photo_ids: list[str] = Field(default_factory=list, max_length=100)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


__all__ = [
    "CompletionAnalysisResult",
    "ConclusionValue",
    "ParsedContentItem",
    "ParsedSubject",
    "PhotoLinkSuggestionResult",
    "SuggestedLink",
    "TaskSpecParseResult",
]
