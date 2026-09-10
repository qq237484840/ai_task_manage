"""AIService 三能力接口测试：契约字段、重试、降级信号、防编造。"""
from __future__ import annotations

from app.core.ai import AIService, SourceInput, SubjectCandidate
from app.core.ai.config import AISettings
from app.core.ai.errors import AIError, AIErrorCode
from app.core.ai.providers.registry import UnavailableProvider
from app.core.ai.types import PhotoInput

from tests.unit.ai_stubs import ScriptedProvider, ai_settings, image, make_bundle

PARSE_OK = (
    '{"subjects":[{"subject":"math","contents":[{"text":"口算 20 题"}],"confidence":0.9}],'
    '"confidence":0.9}'
)
LINK_OK = (
    '{"links":[{"group_subject_id":"g1","subject":"math","confidence":0.9},'
    '{"group_subject_id":"ghost","subject":"math","confidence":0.9}],"confidence":0.9}'
)
COMPLETION_OK = '{"conclusion":"完成","evidence_photo_ids":["p1","ghost"],"confidence":0.9}'


def _service(vision=None, llm=None, ocr=None, *, settings=None) -> AIService:
    return AIService(
        settings or ai_settings(),
        providers=make_bundle(vision=vision, llm=llm, ocr=ocr),
    )


# ---------------------------------------------------------------------------
# ① 任务输入源解析
# ---------------------------------------------------------------------------


def test_parse_text_uses_llm_provider_and_returns_contract_fields():
    llm = ScriptedProvider(model="llm-model", texts=[PARSE_OK])
    outcome = _service(llm=llm).parse_task_spec(
        None, family_id="f1", sources=[SourceInput.text_of("数学：口算 20 题")]
    )
    assert outcome.ok is True
    assert outcome.available is True
    assert outcome.model_name == "llm-model"
    assert [s.subject for s in outcome.subjects] == ["math"]
    assert outcome.subjects[0].contents[0].text == "口算 20 题"
    assert outcome.confidence == 0.9
    assert outcome.prompt_key == "task_spec_parse"
    assert outcome.prompt_version == "v1"


def test_parse_image_uses_vision_provider():
    vision = ScriptedProvider(model="vision-model", texts=[PARSE_OK])
    llm = ScriptedProvider(model="llm-model", texts=["{}"])
    outcome = _service(vision=vision, llm=llm).parse_task_spec(
        None, sources=[SourceInput.image_of(image(image_id="s1"))]
    )
    assert outcome.ok is True
    assert outcome.model_name == "vision-model"


def test_parse_without_credentials_returns_marked_mock_result():
    service = AIService(AISettings(provider_mode="auto", retry_backoff_seconds=0.0))
    outcome = service.parse_task_spec(None, sources=[SourceInput.text_of("数学：口算 20 题")])
    assert outcome.ok is True
    assert outcome.mock is True
    assert outcome.degraded is True
    assert outcome.model_name.startswith("mock-")


# ---------------------------------------------------------------------------
# ② 作业照片挂接建议
# ---------------------------------------------------------------------------


def test_suggest_photo_links_returns_n_to_n_and_drops_hallucinated_ids():
    vision = ScriptedProvider(model="vision-model", texts=[LINK_OK])
    outcome = _service(vision=vision).suggest_photo_links(
        None,
        family_id="f1",
        photo=PhotoInput(photo_id="p1", image=image(image_id="p1")),
        candidates=[SubjectCandidate(group_subject_id="g1", subject="math")],
    )
    assert outcome.ok is True
    assert [link.group_subject_id for link in outcome.links] == ["g1"]
    assert outcome.links[0].confidence == 0.9


def test_suggest_photo_links_without_candidates_returns_empty_on_mock():
    service = AIService(AISettings(provider_mode="mock"))
    outcome = service.suggest_photo_links(
        None,
        photo=PhotoInput(photo_id="p1", image=image()),
        candidates=[],
    )
    assert outcome.ok is True
    assert outcome.links == []
    assert outcome.mock is True and outcome.degraded is False


# ---------------------------------------------------------------------------
# ③ 聚合子任务级完成结论
# ---------------------------------------------------------------------------


def test_analyze_completion_filters_ghost_evidence():
    vision = ScriptedProvider(model="vision-model", texts=[COMPLETION_OK])
    outcome = _service(vision=vision).analyze_completion(
        None,
        subject="math",
        contents=["口算 20 题"],
        photos=[PhotoInput(photo_id="p1", image=image())],
    )
    assert outcome.ok is True
    assert outcome.conclusion == "完成"
    assert outcome.evidence_photo_ids == ["p1"]  # ghost 被剔除


def test_analyze_completion_forces_unknown_when_no_evidence():
    vision = ScriptedProvider(model="vision-model", texts=[COMPLETION_OK])
    outcome = _service(vision=vision).analyze_completion(
        None, subject="math", contents=["口算 20 题"], photos=[]
    )
    assert outcome.ok is True
    assert outcome.conclusion == "无法判断"
    assert outcome.evidence_photo_ids == []


def test_analyze_completion_mock_without_photos_returns_unknown():
    service = AIService(AISettings(provider_mode="mock"))
    outcome = service.analyze_completion(None, subject="math", contents=[], photos=[])
    assert outcome.ok is True
    assert outcome.conclusion == "无法判断"


# ---------------------------------------------------------------------------
# 可靠性：超时 / 重试 / 降级信号
# ---------------------------------------------------------------------------


def test_invalid_output_is_retried_then_degrades_with_explicit_signal():
    vision = ScriptedProvider(texts=["这不是 JSON"])
    service = AIService(ai_settings(max_retries=2), providers=make_bundle(vision=vision))
    outcome = service.parse_task_spec(None, sources=[SourceInput.image_of(image())])
    assert outcome.ok is False
    assert outcome.available is False  # 上游据此走手工兜底
    assert outcome.degraded is True
    assert outcome.error == AIErrorCode.INVALID_OUTPUT.value
    assert outcome.attempts == 3
    assert vision.calls == 3


def test_timeout_exhausts_retries_and_degrades():
    vision = ScriptedProvider(errors=[AIError(AIErrorCode.TIMEOUT)])
    service = AIService(ai_settings(max_retries=2), providers=make_bundle(vision=vision))
    outcome = service.parse_task_spec(None, sources=[SourceInput.image_of(image())])
    assert outcome.available is False
    assert outcome.error == AIErrorCode.TIMEOUT.value
    assert outcome.attempts == 3


def test_retry_then_success_is_reported():
    vision = ScriptedProvider(
        model="vision-model",
        texts=[PARSE_OK, PARSE_OK],
        errors=[AIError(AIErrorCode.TIMEOUT), None],
    )
    service = AIService(ai_settings(max_retries=2), providers=make_bundle(vision=vision))
    outcome = service.parse_task_spec(None, sources=[SourceInput.image_of(image())])
    assert outcome.ok is True
    assert outcome.attempts == 2


def test_content_refused_is_permanent_and_not_retried():
    vision = ScriptedProvider(errors=[AIError(AIErrorCode.CONTENT_REFUSED)])
    service = AIService(ai_settings(max_retries=2), providers=make_bundle(vision=vision))
    outcome = service.parse_task_spec(None, sources=[SourceInput.image_of(image())])
    assert outcome.available is False
    assert outcome.error == AIErrorCode.CONTENT_REFUSED.value
    assert vision.calls == 1


def test_unavailable_provider_returns_degradation_signal():
    service = AIService(
        ai_settings(),
        providers=make_bundle(vision=UnavailableProvider("vision"), degraded=True),
    )
    outcome = service.parse_task_spec(None, sources=[SourceInput.image_of(image())])
    assert outcome.available is False
    assert outcome.error == AIErrorCode.PROVIDER_UNAVAILABLE.value


def test_token_usage_passthrough():
    vision = ScriptedProvider(texts=[PARSE_OK], token_usage={"total_tokens": 42})
    outcome = _service(vision=vision).parse_task_spec(
        None, sources=[SourceInput.image_of(image())]
    )
    assert outcome.token_usage == {"total_tokens": 42}


# ---------------------------------------------------------------------------
# OCR 基础设施能力
# ---------------------------------------------------------------------------


def test_ocr_extract_returns_text_and_reliability_metadata():
    ocr = ScriptedProvider(model="ocr-model", texts=["第一行\n第二行"])
    outcome = _service(ocr=ocr).extract_text(None, images=[image()])
    assert outcome.ok is True
    assert outcome.text == "第一行\n第二行"
    assert outcome.model_name == "ocr-model"
    assert outcome.prompt_key == "ocr_extract"
