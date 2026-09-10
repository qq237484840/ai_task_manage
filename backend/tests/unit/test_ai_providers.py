"""Provider 抽象 / Mock 桩 / 注册选择测试：切换只靠配置，业务代码无感知。"""
from __future__ import annotations

from app.core.ai.config import AISettings
from app.core.ai.prompts import get_prompt
from app.core.ai.providers.base import (
    LLMProvider,
    OCRProvider,
    ProviderResponse,
    VisionProvider,
    VisionRequest,
)
from app.core.ai.providers.mock import (
    MockLLMProvider,
    MockOCRProvider,
    MockVisionProvider,
)
from app.core.ai.providers.openai_compatible import OpenAICompatibleVisionProvider
from app.core.ai.providers.registry import UnavailableProvider, build_providers
from app.core.ai.schemas import PhotoLinkSuggestionResult


def test_protocols_are_runtime_checkable():
    assert isinstance(MockVisionProvider(), VisionProvider)
    assert isinstance(MockLLMProvider(), LLMProvider)
    assert isinstance(MockOCRProvider(), OCRProvider)


def test_auto_mode_without_credentials_falls_back_to_mock():
    bundle = build_providers(AISettings(provider_mode="auto"))
    assert isinstance(bundle.vision.provider, MockVisionProvider)
    assert bundle.vision.mock is True
    assert bundle.vision.degraded is True  # 降级（非显式 mock）


def test_explicit_mock_mode_is_not_degraded():
    bundle = build_providers(AISettings(provider_mode="mock"))
    assert isinstance(bundle.vision.provider, MockVisionProvider)
    assert bundle.vision.mock is True
    assert bundle.vision.degraded is False


def test_configured_vision_selects_real_provider_only_for_that_kind():
    settings = AISettings(
        provider_mode="auto",
        vision_model="some-vision-model",
        vision_api_key="secret",
        vision_base_url="https://example.invalid/v1",
    )
    bundle = build_providers(settings)
    assert isinstance(bundle.vision.provider, OpenAICompatibleVisionProvider)
    assert bundle.vision.mock is False and bundle.vision.degraded is False
    # 其余类型未配置 → Mock 降级
    assert isinstance(bundle.llm.provider, MockLLMProvider)
    assert isinstance(bundle.ocr.provider, MockOCRProvider)


def test_real_mode_without_fallback_yields_unavailable_provider():
    settings = AISettings(provider_mode="real", allow_mock_fallback=False)
    bundle = build_providers(settings)
    assert isinstance(bundle.vision.provider, UnavailableProvider)
    assert bundle.vision.mock is False and bundle.vision.degraded is True


def test_mock_vision_is_deterministic_and_marked():
    # 纯 Provider 级「确定性 / 显著标注」测试：context key 必须与 AIService 注入一致（`candidates`）。
    # 装配路径正确性由 tests/e2e/test_bug003_link_keys.py 经 AIService 断言，**不得**以本用例替代。
    provider = MockVisionProvider()
    request = VisionRequest(
        prompt=get_prompt("photo_link_suggest"),
        images=[],
        context={"candidates": [{"group_subject_id": "g1", "subject": "math"}]},
        response_schema=PhotoLinkSuggestionResult,
    )
    first = provider.analyze(request)
    second = provider.analyze(request)
    assert isinstance(first, ProviderResponse)
    assert first.text == second.text
    assert first.mock is True
    assert first.model.startswith("mock-")
    assert "g1" in first.text


def test_mock_llm_parses_subject_lines():
    provider = MockLLMProvider()
    from app.core.ai.providers.base import LLMRequest

    response = provider.generate(
        LLMRequest(
            prompt=get_prompt("task_spec_parse"),
            context={"source_texts": ["数学：口算 20 题", "语文：抄写第 3 课生字"], "image_count": 0},
        )
    )
    assert '"subject": "math"' in response.text
    assert '"subject": "chinese"' in response.text


def test_mock_ocr_returns_configured_text():
    provider = MockOCRProvider()
    from app.core.ai.providers.base import OCRRequest

    response = provider.extract_text(OCRRequest(images=[], context={"mock_ocr_text": "第 3 课 生字"}))
    assert response.text == "第 3 课 生字"
    assert response.mock is True
