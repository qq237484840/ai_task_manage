"""DATA-009 调用记录测试：字段完整、追溯、错误记录、Mock 标注、离线跳过。"""
from __future__ import annotations

import json

from app.core.ai import AIService, SourceInput
from app.core.ai.config import AISettings
from app.core.ai.errors import AIError, AIErrorCode
from app.core.ai.records import list_calls_by_request_id, record_call

from tests.unit.ai_stubs import ScriptedProvider, ai_settings, image, make_bundle

PARSE_OK = (
    '{"subjects":[{"subject":"math","contents":[{"text":"口算 20 题"}],"confidence":0.9}],'
    '"confidence":0.9}'
)


def test_record_call_persists_all_data_009_fields(ai_session):
    record = record_call(
        ai_session,
        request_id="trace-1",
        family_id="f1",
        capability="task_spec_parse",
        provider_kind="vision",
        provider_name="scripted",
        model="m1",
        prompt_key="task_spec_parse",
        prompt_version="v1",
        attempt=1,
        latency_ms=12,
        token_usage={"total_tokens": 7},
        result={"subjects": []},
        confidence=0.8,
        status="ok",
        mock=False,
        error=None,
        input_ref={"image_count": 1},
    )
    assert record is not None
    assert record.created_at  # 时间戳必填

    rows = list_calls_by_request_id(ai_session, "trace-1")
    assert len(rows) == 1
    row = rows[0]
    # DATA-009 必填字段：model / prompt_version / request_id / latency / token_usage / result / confidence / error
    assert row.model == "m1"
    assert row.prompt_version == "v1"
    assert row.request_id == "trace-1"
    assert row.latency_ms == 12
    assert json.loads(row.token_usage) == {"total_tokens": 7}
    assert json.loads(row.result) == {"subjects": []}
    assert row.confidence == 0.8
    assert row.error is None
    assert row.status == "ok"
    assert row.mock is False
    assert json.loads(row.input_ref) == {"image_count": 1}
    assert row.family_id == "f1"


def test_record_call_without_session_is_noop():
    assert record_call(None, request_id="trace-null") is None


def test_service_success_writes_traceable_record(ai_session):
    vision = ScriptedProvider(
        model="vision-model", texts=[PARSE_OK], token_usage={"total_tokens": 11}
    )
    service = AIService(ai_settings(), providers=make_bundle(vision=vision))
    outcome = service.parse_task_spec(
        ai_session,
        family_id="f1",
        request_id="trace-svc",
        sources=[SourceInput.image_of(image())],
    )
    assert outcome.ok is True
    assert outcome.request_id == "trace-svc"

    rows = list_calls_by_request_id(ai_session, "trace-svc")
    assert len(rows) == 1
    row = rows[0]
    assert row.capability == "task_spec_parse"
    assert row.provider_kind == "vision"
    assert row.model == "vision-model"
    assert row.prompt_key == "task_spec_parse"
    assert row.prompt_version == "v1"
    assert row.status == "ok"
    assert row.confidence == 0.9
    assert row.latency_ms >= 0
    assert json.loads(row.token_usage) == {"total_tokens": 11}
    assert row.result is not None and row.error is None
    assert row.mock is False
    assert row.attempt == 1


def test_degraded_call_writes_error_record_per_attempt(ai_session):
    vision = ScriptedProvider(errors=[AIError(AIErrorCode.TIMEOUT)])
    service = AIService(
        ai_settings(max_retries=1),
        providers=make_bundle(vision=vision, degraded=True, mock=True),
    )
    outcome = service.parse_task_spec(
        ai_session, request_id="trace-err", sources=[SourceInput.image_of(image())]
    )
    assert outcome.available is False
    assert outcome.attempts == 2

    rows = list_calls_by_request_id(ai_session, "trace-err")
    assert len(rows) == 2  # 每次尝试各一条，可追溯失败次数
    assert [row.attempt for row in rows] == [1, 2]
    assert all(row.status == "error" for row in rows)
    assert json.loads(rows[0].error)["code"] == "timeout"
    assert rows[0].result is None and rows[0].confidence is None
    assert rows[0].mock is True  # 降级 Provider 为 Mock


def test_mock_call_record_is_marked(ai_session):
    service = AIService(AISettings(provider_mode="mock"))
    outcome = service.parse_task_spec(
        ai_session,
        request_id="trace-mock",
        sources=[SourceInput.text_of("数学：口算 20 题")],
    )
    assert outcome.mock is True
    rows = list_calls_by_request_id(ai_session, "trace-mock")
    assert len(rows) == 1
    assert rows[0].mock is True
    assert rows[0].model.startswith("mock-")
    assert rows[0].status == "ok"
