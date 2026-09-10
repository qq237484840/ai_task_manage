"""Provider 抽象（Vision / OCR / LLM 三类协议）+ 结构化输出校验工具。

契约（Task-006 §3.1 / ARCHITECTURE「AI Provider 抽象」）：
- 业务只面向接口，不感知具体厂商；Provider 返回**原始文本** + 模型/用量元信息；
- 原始文本一律经 `validate_structured` 落入 pydantic schema；不合规抛 `AIError(INVALID_OUTPUT)`。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ValidationError

from app.core.ai.errors import AIError, AIErrorCode
from app.core.ai.prompts import PromptTemplate
from app.core.ai.types import ImageInput

# ---------------------------------------------------------------------------
# 请求 / 响应载体
# ---------------------------------------------------------------------------


@dataclass
class VisionRequest:
    prompt: PromptTemplate
    images: list[ImageInput]
    context: dict[str, Any] = field(default_factory=dict)
    response_schema: type[BaseModel] | None = None


@dataclass
class LLMRequest:
    prompt: PromptTemplate
    context: dict[str, Any] = field(default_factory=dict)
    response_schema: type[BaseModel] | None = None


@dataclass
class OCRRequest:
    images: list[ImageInput]
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderResponse:
    text: str
    model: str
    provider_name: str
    token_usage: dict[str, int] | None = None
    mock: bool = False


# ---------------------------------------------------------------------------
# 三类 Provider 协议
# ---------------------------------------------------------------------------


@runtime_checkable
class VisionProvider(Protocol):
    """图片理解 Provider（挂接建议 / 完成分析 / 图片任务解析）。"""

    provider_name: str
    model: str

    def analyze(self, request: VisionRequest) -> ProviderResponse: ...


@runtime_checkable
class LLMProvider(Protocol):
    """文本大模型 Provider（纯文本任务解析）。"""

    provider_name: str
    model: str

    def generate(self, request: LLMRequest) -> ProviderResponse: ...


@runtime_checkable
class OCRProvider(Protocol):
    """OCR Provider（图片 → 文字）。"""

    provider_name: str
    model: str

    def extract_text(self, request: OCRRequest) -> ProviderResponse: ...


# ---------------------------------------------------------------------------
# 结构化输出解析
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*\s*|\s*```$", re.MULTILINE)


def extract_json_text(raw: str) -> str:
    """从模型输出中提取 JSON 主体（容忍 Markdown 代码块 / 前后说明文字）。"""
    text = (raw or "").strip()
    if not text:
        raise AIError(AIErrorCode.INVALID_OUTPUT, "模型返回为空")
    text = _FENCE_RE.sub("", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise AIError(AIErrorCode.INVALID_OUTPUT, "模型返回不含 JSON 对象")
    return text[start : end + 1]


def validate_structured(raw: str, schema: type[BaseModel]) -> BaseModel:
    """把 Provider 原始文本解析并校验为 `schema`；失败抛 INVALID_OUTPUT（可重试）。"""
    candidate = extract_json_text(raw)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise AIError(AIErrorCode.INVALID_OUTPUT, f"JSON 解析失败：{exc.msg}") from exc
    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        raise AIError(
            AIErrorCode.INVALID_OUTPUT,
            f"AI 输出不符合 schema（{schema.__name__}）：{exc.error_count()} 处不合法",
        ) from exc


__all__ = [
    "LLMProvider",
    "LLMRequest",
    "OCRProvider",
    "OCRRequest",
    "ProviderResponse",
    "VisionProvider",
    "VisionRequest",
    "extract_json_text",
    "validate_structured",
]
