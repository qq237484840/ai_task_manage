"""API：链路 T **生产路径**（`POST /tasks` → `TaskService.ingest`）核心 AI 真跑取证（`Task-012`）。

`Task-012` §3.5-DoD：取证路径必须为生产路径（非手工注入 session 绕过）——
文本源经 `app/core/ai.parse_task_spec` 解析 → 任务 `spec_status == "parsed"`
且 DATA-009 `ai_call_records` 落条（`capability` / `prompt_version` / `model` 可取原文）。
"""
from __future__ import annotations

from app.core.ai.prompts import PROMPT_TASK_SPEC_PARSE, get_prompt
from app.core.ai.providers.mock import MOCK_LLM_MODEL
from app.core.ai.providers.registry import PROVIDER_KIND_LLM
from app.core.ai.records import AICallRecord
from app.core.ai.service import CAPABILITY_TASK_SPEC_PARSE
from tests._m001_helpers import (
    DAY,
    TEST_TERM_START,
    create_task_v2,
    install_fixed_window,
    task_payload,
    text_source,
)
from tests.conftest import create_student


def test_ingest_text_source_runs_core_ai_and_records_call(world, factory):
    """链路 T 生产路径：`spec_status=parsed` + `contents` 来自 AI + `ai_call_records` 落条。"""
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="小A")

    data = create_task_v2(
        c, ha, task_payload(stu["student_id"], sources=[text_source("数学：练习册 P23")])
    )

    assert data["spec_status"] == "parsed"
    assert [x["subject"] for x in data["contents"]] == ["math"]
    assert [x["text"] for x in data["contents"]] == ["练习册 P23"]

    with factory() as session:
        rows = session.query(AICallRecord).all()
    assert len(rows) == 1, "链路 T 生产路径应写入 1 条 ai_call_records"
    row = rows[0]
    # 逐字取原文（常量引自 `app/core/ai/`，非臆造）
    assert row.capability == CAPABILITY_TASK_SPEC_PARSE
    assert row.status == "ok"
    assert row.provider_kind == PROVIDER_KIND_LLM
    assert row.prompt_key == PROMPT_TASK_SPEC_PARSE
    assert row.prompt_version == get_prompt(PROMPT_TASK_SPEC_PARSE).version
    assert row.model == MOCK_LLM_MODEL
    assert row.mock is True, "Mock 路径须显著标注 mock=True（禁静默冒充真实结果）"
    assert row.request_id, "request_id 不应为空"


def test_ingest_keeps_placeholder_when_mock_fallback_disabled(world, factory, monkeypatch):
    """`BUG-006` / `Task-016`：`real` + `AT_AI_ALLOW_MOCK_FALLBACK=false` 时 AI 失败**不得**产出草稿。

    真实装配路径取证：无三方凭据（测试隔离已清空 `AT_AI_*` 凭据）+ `provider_mode=real`
    + 禁兜底 → Provider 判为「不可用」→ 链路 T 如实失败 → `spec_status` 保持 `placeholder`，
    不再由本地启发式伪造 `parsed`（修复前本用例必败）。
    """
    from app.core.ai.config import get_ai_settings
    from app.core.ai.service import get_ai_service

    monkeypatch.setenv("AT_AI_PROVIDER_MODE", "real")
    monkeypatch.setenv("AT_AI_ALLOW_MOCK_FALLBACK", "false")
    get_ai_settings.cache_clear()
    get_ai_service.cache_clear()

    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="小B")

    data = create_task_v2(
        c, ha, task_payload(stu["student_id"], sources=[text_source("数学：练习册 P23")])
    )

    assert data["spec_status"] == "placeholder", "禁兜底时不得以本地草稿冒充 AI 解析结果"
    assert data["contents"] == []

    with factory() as session:
        rows = session.query(AICallRecord).all()
    if rows:  # 不可用 Provider 在调用前即判定的路径可能不落条 → 以 spec_status 为主断言
        assert rows[0].status == "error"
