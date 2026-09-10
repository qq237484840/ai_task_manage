"""AI 能力接口的输出结构（经 pydantic 校验的 AI 结果 + 调用结果信封）。

分层：
- schemas.py：**AI 原始返回**必须解析成的业务结构（schema 校验对象）；
- types.py（本文件）：输入原语 + 供上游（M001/M002）消费的**调用结果信封**（含降级信号）。

信封约定（供上游判定是否走手工兜底）：
- `ok=True`  → AI 返回已通过 schema 校验，`subjects` / `links` / `conclusion` 可用；
- `available=False` → 本层不可用 / 不合规，**上游必须走手工兜底**（不得消费空结果当成功）；
- `degraded=True` → 结果来自 Mock 降级（`mock=True`）或重试后才成功，需提示降级语义。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.ai.schemas import ParsedSubject, SuggestedLink

ConclusionValue = Literal["完成", "部分完成", "未完成", "无法判断"]


@dataclass(frozen=True)
class ImageInput:
    """待送 AI 的图片（内存字节或受控本地路径二选一；不会外发路径本身）。"""

    mime: str = "image/jpeg"
    data: bytes | None = None
    path: str | None = None
    image_id: str | None = None  # 业务侧标识（照片 id），仅用于构建上下文/证据

    def load_bytes(self) -> bytes:
        if self.data is not None:
            return self.data
        if self.path:
            return Path(self.path).read_bytes()
        raise ValueError("ImageInput 既无 data 也无 path")


@dataclass(frozen=True)
class SourceInput:
    """任务输入源（链路 T 多段：文本 / 图片）。"""

    kind: Literal["text", "image"]
    text: str | None = None
    image: ImageInput | None = None

    @classmethod
    def text_of(cls, text: str) -> "SourceInput":
        return cls(kind="text", text=text)

    @classmethod
    def image_of(cls, image: ImageInput) -> "SourceInput":
        return cls(kind="image", image=image)


@dataclass(frozen=True)
class PhotoInput:
    """作业照片（链路 H 挂接建议 / 完成分析取图）。"""

    photo_id: str
    image: ImageInput


@dataclass(frozen=True)
class SubjectCandidate:
    """候选聚合学科子任务（M001 `get_group` 提供）。"""

    group_subject_id: str
    subject: str


class AIOutcome(BaseModel):
    """AI 调用结果信封（三能力共用）。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    capability: str
    ok: bool
    available: bool
    degraded: bool = False
    mock: bool = False
    request_id: str
    provider_name: str | None = None
    model_name: str | None = None
    prompt_key: str
    prompt_version: str
    latency_ms: int = 0
    attempts: int = 1
    confidence: float | None = None
    token_usage: dict[str, int] | None = None
    error: str | None = None  # AIErrorCode.value
    error_message: str | None = None


class TaskParseOutcome(AIOutcome):
    """① 任务输入源解析结果。"""

    subjects: list[ParsedSubject] = Field(default_factory=list)


class PhotoLinkOutcome(AIOutcome):
    """② 作业照片挂接建议结果（N:N）。"""

    links: list[SuggestedLink] = Field(default_factory=list)


class CompletionOutcome(AIOutcome):
    """③ 聚合子任务级完成结论（含 `无法判断` 出口）。"""

    conclusion: ConclusionValue = "无法判断"
    evidence_photo_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class OCRTextOutcome(AIOutcome):
    """OCR 文字提取结果（基础设施能力，供上游可选消费）。"""

    text: str = ""


# 便于上游构造上下文时的占位（不导出为公开契约）
UNKNOWN_CONCLUSION: ConclusionValue = "无法判断"

__all__ = [
    "AIOutcome",
    "CompletionOutcome",
    "ConclusionValue",
    "ImageInput",
    "OCRTextOutcome",
    "PhotoInput",
    "PhotoLinkOutcome",
    "SourceInput",
    "SubjectCandidate",
    "TaskParseOutcome",
    "UNKNOWN_CONCLUSION",
]
