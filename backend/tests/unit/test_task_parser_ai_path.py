"""单测：链路 T 的 M001 侧 AI 通路（`BUG-004` 修复 / `Task-012`）。

覆盖（修复后取证）：
- 文本源经 `app/core/ai.parse_task_spec` **真跑**（keyword `sources=` + `SourceInput` 适配）；
- 传入 `session` 时 DATA-009 `ai_call_records` 落条（`capability` / `prompt_version` / `model`）
  → 证明「AI 真跑」而非本地启发式兜底；
- AI 产物被真正消费（stub 返回与本地兜底不同的结果，`default_parser` 采用 AI 结果）；
- 降级**可观测**：AI 抛错 → `logger.warning` + 保留本地兜底（不污染事实层）；
- 图片源不伪造草稿（M001 侧 `photo_id` 仅引用、无字节）→ 返回 `None`（上层维持 `placeholder`）。
"""
from __future__ import annotations

import logging

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.ai.records import AICallRecord
from app.core.ai.schemas import ParsedContentItem, ParsedSubject
from app.core.ai.types import TaskParseOutcome
from app.modules.m001.services import task_parser

_TEXT_SOURCE = [{"seq": 1, "kind": "text", "text_content": "数学：练习册 P23"}]
_IMAGE_SOURCE = [{"seq": 1, "kind": "image", "photo_id": "p1"}]


@pytest.fixture
def ai_session():
    """独立内存库会话（仅用于 `ai_call_records` 落条取证）。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    with factory() as session:
        yield session


def test_default_parser_text_source_runs_core_ai_and_records_call(ai_session):
    """文本源经核心 AI 解析并落 DATA-009 记录（证明 AI 真跑）。"""
    drafts = task_parser.default_parser(_TEXT_SOURCE, session=ai_session)

    assert [(d.subject, d.text) for d in drafts] == [("math", "练习册 P23")]

    rows = ai_session.query(AICallRecord).all()
    assert len(rows) == 1, "AI 真跑应写入 1 条 ai_call_records"
    row = rows[0]
    assert row.capability == "task_spec_parse"
    assert row.status == "ok"
    assert row.prompt_version, "prompt 版本化字段不应为空"
    assert row.model, "model 字段不应为空（Mock = mock-llm，显著标注）"
    assert row.mock is True  # 无三方密钥 → Mock 降级且显著标注


def test_default_parser_consumes_ai_outcome_not_local_fallback(monkeypatch):
    """AI 产物被真正消费：stub 返回与本地兜底**不同**的学科/内容。"""
    def fake_parser(session, **kwargs):
        return TaskParseOutcome(
            capability="task_spec_parse",
            ok=True,
            available=True,
            request_id="req-test",
            prompt_key="task_spec_parse",
            prompt_version="v-test",
            subjects=[
                ParsedSubject(
                    subject="physics",
                    contents=[ParsedContentItem(text="AI 产物：浮力实验报告")],
                )
            ],
        )

    monkeypatch.setattr(task_parser, "_ai_parser", lambda: fake_parser)
    drafts = task_parser.default_parser(_TEXT_SOURCE)

    assert [(d.subject, d.text) for d in drafts] == [("physics", "AI 产物：浮力实验报告")]
    # 与本地启发式结果不同 → 证明未回落 `mock_parse_sources`
    assert drafts != task_parser.mock_parse_sources(_TEXT_SOURCE)


def test_default_parser_warns_and_falls_back_on_ai_error(monkeypatch, caplog):
    """降级可观测：AI 抛错 → warning 日志，且保留本地兜底（不污染事实层）。"""
    def boom(session, **kwargs):
        raise RuntimeError("core-ai-down")

    monkeypatch.setattr(task_parser, "_ai_parser", lambda: boom)
    with caplog.at_level(logging.WARNING, logger="app.modules.m001.services.task_parser"):
        drafts = task_parser.default_parser(_TEXT_SOURCE)

    assert "核心 AI 解析降级" in caplog.text
    assert "core-ai-down" in caplog.text
    assert drafts == task_parser.mock_parse_sources(_TEXT_SOURCE)


def test_default_parser_image_source_keeps_placeholder():
    """图片源不伪造草稿：M001 无图片字节（`photo_id` 仅引用）→ `None`（上层维持 placeholder）。"""
    assert task_parser.default_parser(_IMAGE_SOURCE) is None
