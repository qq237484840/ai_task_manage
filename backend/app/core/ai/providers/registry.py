"""Provider 注册与选择（业务代码不感知厂商，切换只改配置）。

选择策略（ADR-011：真实三方默认 + Mock 降级）：
- `provider_mode=mock`  → 全部走 Mock（测试桩/离线演示；`mock=True` 但非降级）；
- `provider_mode=auto`  → 某类 Provider 真实三方配置齐备则用真实，否则 Mock 降级（`degraded=True`）；
- `provider_mode=real`  → 优先真实；缺配置时若允许降级则 Mock（`degraded=True`），否则返回「不可用」Provider。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.ai.config import (
    PROVIDER_MODE_AUTO,
    PROVIDER_MODE_MOCK,
    PROVIDER_MODE_REAL,
    AISettings,
    get_ai_settings,
)
from app.core.ai.errors import AIError, AIErrorCode
from app.core.ai.providers.base import LLMRequest, OCRRequest, VisionRequest
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

PROVIDER_KIND_VISION = "vision"
PROVIDER_KIND_OCR = "ocr"
PROVIDER_KIND_LLM = "llm"


class UnavailableProvider:
    """显式「不可用」Provider：不降级 Mock 时使用；调用即抛 PROVIDER_UNAVAILABLE。"""

    provider_name = "unavailable"

    def __init__(self, kind: str) -> None:
        self.model = f"unavailable-{kind}"
        self._kind = kind

    def _raise(self) -> None:
        raise AIError(
            AIErrorCode.PROVIDER_UNAVAILABLE,
            f"{self._kind} Provider 未配置且未允许 Mock 降级",
            retryable=False,
        )

    def analyze(self, request: VisionRequest):  # pragma: no cover - 触发即抛
        self._raise()

    def generate(self, request: LLMRequest):  # pragma: no cover - 触发即抛
        self._raise()

    def extract_text(self, request: OCRRequest):  # pragma: no cover - 触发即抛
        self._raise()


@dataclass(frozen=True)
class ResolvedProvider:
    """一次 Provider 选择结果（供调用记录与降级信号使用）。"""

    provider: object
    kind: str
    mock: bool
    degraded: bool
    reason: str

    @property
    def model(self) -> str:
        return str(getattr(self.provider, "model", ""))

    @property
    def provider_name(self) -> str:
        return str(getattr(self.provider, "provider_name", "unknown"))


@dataclass(frozen=True)
class ProviderBundle:
    vision: ResolvedProvider
    ocr: ResolvedProvider
    llm: ResolvedProvider
    mode: str


def _build_real(kind: str, settings: AISettings):
    cls = {
        PROVIDER_KIND_VISION: OpenAICompatibleVisionProvider,
        PROVIDER_KIND_OCR: OpenAICompatibleOCRProvider,
        PROVIDER_KIND_LLM: OpenAICompatibleLLMProvider,
    }[kind]
    return cls(
        model=getattr(settings, f"{kind}_model"),
        api_key=getattr(settings, f"{kind}_api_key"),
        base_url=getattr(settings, f"{kind}_base_url"),
        timeout_seconds=settings.request_timeout_seconds,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
    )


def _build_mock(kind: str, settings: AISettings):
    cls = {
        PROVIDER_KIND_VISION: MockVisionProvider,
        PROVIDER_KIND_OCR: MockOCRProvider,
        PROVIDER_KIND_LLM: MockLLMProvider,
    }[kind]
    return cls(latency_ms=settings.mock_latency_ms)


def _resolve_one(kind: str, mode: str, settings: AISettings) -> ResolvedProvider:
    if mode == PROVIDER_MODE_MOCK:
        return ResolvedProvider(
            provider=_build_mock(kind, settings),
            kind=kind,
            mock=True,
            degraded=False,
            reason="mock-mode",
        )
    if settings.provider_configured(kind):
        return ResolvedProvider(
            provider=_build_real(kind, settings),
            kind=kind,
            mock=False,
            degraded=False,
            reason="real",
        )
    fallback_allowed = settings.allow_mock_fallback or mode == PROVIDER_MODE_AUTO
    if fallback_allowed:
        return ResolvedProvider(
            provider=_build_mock(kind, settings),
            kind=kind,
            mock=True,
            degraded=True,
            reason="no-credentials",
        )
    return ResolvedProvider(
        provider=UnavailableProvider(kind),
        kind=kind,
        mock=False,
        degraded=True,
        reason="unavailable",
    )


def build_providers(settings: AISettings | None = None) -> ProviderBundle:
    settings = settings or get_ai_settings()
    mode = (settings.provider_mode or PROVIDER_MODE_AUTO).strip().lower()
    if mode not in (PROVIDER_MODE_REAL, PROVIDER_MODE_MOCK, PROVIDER_MODE_AUTO):
        mode = PROVIDER_MODE_AUTO
    return ProviderBundle(
        vision=_resolve_one(PROVIDER_KIND_VISION, mode, settings),
        ocr=_resolve_one(PROVIDER_KIND_OCR, mode, settings),
        llm=_resolve_one(PROVIDER_KIND_LLM, mode, settings),
        mode=mode,
    )


__all__ = [
    "PROVIDER_KIND_LLM",
    "PROVIDER_KIND_OCR",
    "PROVIDER_KIND_VISION",
    "ProviderBundle",
    "ResolvedProvider",
    "UnavailableProvider",
    "build_providers",
]
