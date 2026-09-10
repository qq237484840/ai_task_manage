"""AI 接入层测试桩：脚本化 Provider + 配置/装配工厂（确定性、无外部依赖）。"""
from __future__ import annotations

from typing import Any

from app.core.ai.config import AISettings
from app.core.ai.errors import AIError
from app.core.ai.providers.base import ProviderResponse
from app.core.ai.providers.registry import ProviderBundle, ResolvedProvider
from app.core.ai.types import ImageInput


def ai_settings(**overrides: Any) -> AISettings:
    """构造测试配置（默认强制 Mock 模式 + 零退避，避免时序抖动）。"""
    base: dict[str, Any] = {
        "provider_mode": "mock",
        "retry_backoff_seconds": 0.0,
        "mock_latency_ms": 0,
    }
    base.update(overrides)
    return AISettings(**base)


def image(data: bytes = b"\xff\xd8\xff\xe0mock", mime: str = "image/jpeg", image_id: str | None = None) -> ImageInput:
    return ImageInput(mime=mime, data=data, image_id=image_id)


class ScriptedProvider:
    """按调用次序返回预设文本或抛预设异常；`errors`/`texts` 末位复用。"""

    provider_name = "scripted"

    def __init__(
        self,
        *,
        model: str = "scripted-model",
        texts: list[str] | None = None,
        errors: list[AIError | None] | None = None,
        token_usage: dict[str, int] | None = None,
    ) -> None:
        self.model = model
        self._texts = list(texts or [])
        self._errors = list(errors or [])
        self._token_usage = token_usage
        self.calls = 0

    def _respond(self) -> ProviderResponse:
        idx = self.calls
        self.calls += 1
        if self._errors:
            failure = self._errors[min(idx, len(self._errors) - 1)]
            if failure is not None:
                raise failure
        text = self._texts[min(idx, len(self._texts) - 1)] if self._texts else "{}"
        return ProviderResponse(
            text=text,
            model=self.model,
            provider_name=self.provider_name,
            token_usage=self._token_usage,
            mock=False,
        )

    def analyze(self, request):  # noqa: ANN001
        return self._respond()

    def generate(self, request):  # noqa: ANN001
        return self._respond()

    def extract_text(self, request):  # noqa: ANN001
        return self._respond()


def make_bundle(
    *,
    vision: Any = None,
    llm: Any = None,
    ocr: Any = None,
    mode: str = "real",
    mock: bool = False,
    degraded: bool = False,
) -> ProviderBundle:
    """构造注入用 ProviderBundle（未给定的类型用默认脚本 Provider）。"""

    def resolved(provider: Any, kind: str) -> ResolvedProvider:
        return ResolvedProvider(
            provider=provider if provider is not None else ScriptedProvider(model=f"{kind}-model"),
            kind=kind,
            mock=mock,
            degraded=degraded,
            reason="test",
        )

    return ProviderBundle(
        vision=resolved(vision, "vision"),
        ocr=resolved(ocr, "ocr"),
        llm=resolved(llm, "llm"),
        mode=mode,
    )
