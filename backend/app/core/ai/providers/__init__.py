"""Provider 层：Vision / OCR / LLM 协议 + Mock 测试桩 + 真实三方 + 注册选择。"""
from __future__ import annotations

from app.core.ai.providers.base import (
    LLMProvider,
    LLMRequest,
    OCRProvider,
    OCRRequest,
    ProviderResponse,
    VisionProvider,
    VisionRequest,
    extract_json_text,
    validate_structured,
)
from app.core.ai.providers.mock import (
    MockLLMProvider,
    MockOCRProvider,
    MockVisionProvider,
)
from app.core.ai.providers.openai_compatible import (
    OpenAICompatibleLLMProvider,
    OpenAICompatibleOCRProvider,
    OpenAICompatibleVisionProvider,
)
from app.core.ai.providers.registry import (
    PROVIDER_KIND_LLM,
    PROVIDER_KIND_OCR,
    PROVIDER_KIND_VISION,
    ProviderBundle,
    ResolvedProvider,
    build_providers,
)

__all__ = [
    "LLMProvider",
    "LLMRequest",
    "MockLLMProvider",
    "MockOCRProvider",
    "MockVisionProvider",
    "OCRProvider",
    "OCRRequest",
    "OpenAICompatibleLLMProvider",
    "OpenAICompatibleOCRProvider",
    "OpenAICompatibleVisionProvider",
    "PROVIDER_KIND_LLM",
    "PROVIDER_KIND_OCR",
    "PROVIDER_KIND_VISION",
    "ProviderBundle",
    "ProviderResponse",
    "ResolvedProvider",
    "VisionProvider",
    "VisionRequest",
    "build_providers",
    "extract_json_text",
    "validate_structured",
]
