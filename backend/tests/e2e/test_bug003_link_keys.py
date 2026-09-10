"""BUG-003 防漂移：挂接建议必须经 `AIService` **真实装配路径**验证。

漏检根因（`Task-006`）：既有 AI 层用例「直调 `MockVisionProvider` + **手写** context key」，
绕过了 `AIService.suggest_photo_links` 的装配路径 —— 于是 service 注入 key（`candidates`）
与 Mock 读取 key（原 `candidate_subjects`）错位未被发现，建议恒为空而 `ok=True` 静默失效。

本文件约定（防复发）：
- 正确性断言**一律**经 `AIService.suggest_photo_links` / 模块级 `suggest_photo_links` 触发，
  以**输出**（`out.links`）为证据，**不得**手写 context key；
- 仅保留一处「键位合同一致性」核验：其 context **取自真实装配上下文**（由捕获 Provider 记录），
  再交给 `MockVisionProvider` 消费 —— 键值来自服务、非手写，若两处约定再次漂移即失败。
"""
from __future__ import annotations

from app.core.ai import (
    AIService,
    ImageInput,
    PhotoInput,
    SubjectCandidate,
    suggest_photo_links,
)
from app.core.ai.prompts import PROMPT_PHOTO_LINK_SUGGEST, get_prompt
from app.core.ai.providers.base import ProviderResponse, VisionRequest
from app.core.ai.providers.mock import MockVisionProvider
from app.core.ai.providers.registry import (
    PROVIDER_KIND_VISION,
    ProviderBundle,
    ResolvedProvider,
)
from app.core.ai.service import CAPABILITY_PHOTO_LINK_SUGGEST


def _photo(photo_id: str = "p1") -> PhotoInput:
    """与生产一致的照片输入（Mock 不读字节，仅取结构）。"""
    return PhotoInput(
        photo_id=photo_id,
        image=ImageInput(mime="image/jpeg", path=None, image_id=photo_id),
    )


def _candidates() -> list[SubjectCandidate]:
    return [SubjectCandidate(group_subject_id="g1", subject="math")]


# ---------------------------------------------------------------------------
# 装配路径（AIService 实例）
# ---------------------------------------------------------------------------
def test_mock_link_suggest_via_service_assembly_echoes_candidates():
    """防漂移：经 `AIService.suggest_photo_links` 装配，Mock 应回显候选 g1（BUG-003 未修时必失败）。"""
    service = AIService()
    out = service.suggest_photo_links(
        None,
        family_id="fam",
        photo=_photo("p1"),
        candidates=_candidates(),
    )
    assert out.available and out.ok
    assert out.capability == CAPABILITY_PHOTO_LINK_SUGGEST
    assert out.mock is True
    assert [link.group_subject_id for link in out.links] == ["g1"]
    assert out.links[0].subject == "math"
    assert out.confidence == 0.8


# ---------------------------------------------------------------------------
# 模块级便捷入口（与 Task-011 验收同一调用面）
# ---------------------------------------------------------------------------
def test_module_level_suggest_photo_links_assembly_echoes_candidates():
    """防漂移：模块级入口与 Task-011 验收同调用面，Mock 下候选应被回显为建议。"""
    out = suggest_photo_links(
        None,
        family_id="fam",
        photo=_photo("p1"),
        candidates=_candidates(),
    )
    assert out.available and out.ok
    assert [link.group_subject_id for link in out.links] == ["g1"]


# ---------------------------------------------------------------------------
# N:N（多候选 / 顺序保持）
# ---------------------------------------------------------------------------
def test_mock_link_suggest_assembly_returns_all_candidates_nn():
    """防漂移：N:N 场景下所有候选均被回显且顺序与入参一致。"""
    service = AIService()
    out = service.suggest_photo_links(
        None,
        family_id="fam",
        photo=_photo("p9"),
        candidates=[
            SubjectCandidate(group_subject_id="g1", subject="math"),
            SubjectCandidate(group_subject_id="g2", subject="chinese"),
            SubjectCandidate(group_subject_id="g3", subject="english"),
        ],
    )
    assert out.available and out.ok
    assert [link.group_subject_id for link in out.links] == ["g1", "g2", "g3"]
    assert [link.subject for link in out.links] == ["math", "chinese", "english"]


# ---------------------------------------------------------------------------
# 空候选：可用但不得编造建议
# ---------------------------------------------------------------------------
def test_mock_link_suggest_assembly_empty_candidates_stays_empty():
    """防漂移：无候选时调用仍成功，但不得编造建议（与上游「不猜」原则一致）。"""
    service = AIService()
    out = service.suggest_photo_links(None, family_id="fam", photo=_photo("p1"), candidates=[])
    assert out.available and out.ok
    assert out.links == []


# ---------------------------------------------------------------------------
# 键位合同一致性：键值取自真实装配上下文（非手写），再交 Mock 消费
# ---------------------------------------------------------------------------
class _ContextCapturingVision:
    """捕获 `AIService` 真实注入的 context（用于键位一致性核验）。"""

    provider_name = "capturing"
    model = "capturing-model"

    def __init__(self) -> None:
        self.contexts: list[dict] = []

    def analyze(self, request: VisionRequest) -> ProviderResponse:  # noqa: ANN001
        self.contexts.append(dict(request.context))
        return ProviderResponse(
            text='{"links":[],"confidence":0.0}',
            model=self.model,
            provider_name=self.provider_name,
            token_usage=None,
            mock=False,
        )


def _bundle_with(vision: object) -> ProviderBundle:
    return ProviderBundle(
        vision=ResolvedProvider(
            provider=vision, kind=PROVIDER_KIND_VISION, mock=False, degraded=False, reason="test"
        ),
        ocr=ResolvedProvider(provider=vision, kind="ocr", mock=False, degraded=False, reason="test"),
        llm=ResolvedProvider(provider=vision, kind="llm", mock=False, degraded=False, reason="test"),
        mode="real",
    )


def test_service_injected_context_key_is_consumed_by_mock_provider():
    """防漂移：以服务**实际注入**的 context 驱动 Mock —— 键位约定两处必须一致。

    断言不手写 key：先由捕获 Provider 记录 `AIService` 真实注入的 context，
    再原样交给 `MockVisionProvider`，若 Mock 能从中读出候选 g1，则键位一致。
    """
    capturing = _ContextCapturingVision()
    service = AIService(providers=_bundle_with(capturing))
    service.suggest_photo_links(
        None,
        family_id="fam",
        photo=_photo("p1"),
        candidates=_candidates(),
    )
    assert len(capturing.contexts) == 1, "应恰好触发一次视觉调用"
    real_context = capturing.contexts[0]

    text = MockVisionProvider().analyze(
        VisionRequest(
            prompt=get_prompt(PROMPT_PHOTO_LINK_SUGGEST),
            images=[],
            context=real_context,  # 键值取自真实装配上下文，非手写
            response_schema=None,
        )
    ).text
    assert "g1" in text, f"服务注入 context 与 Mock 读取 key 再次漂移：{real_context}"


__all__: list[str] = []
