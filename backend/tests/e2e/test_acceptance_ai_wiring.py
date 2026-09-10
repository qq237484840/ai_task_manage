"""Task-011 验收：核心 AI 层（`app/core/ai`）与调用方「接线」核查 —— BUG-003 / BUG-004 取证。

两条缺口都以 `xfail(strict=False)` 记录「应有行为」：
- 当前实测不满足 → 记为 xfailed（**不计入 failed**，不污染回归基线）；
- 若后续修复 → 自动转为 XPASS，可直接看出缺口已闭合。

`*_evidence_*` 用例为**恒通过**的取证（断言当前的真实形状），供 BUG 单引用。
"""
from __future__ import annotations

import logging

import pytest

from app.core.ai import (
    ImageInput,
    PhotoInput,
    SubjectCandidate,
    suggest_photo_links,
)
from app.core.ai.prompts import PROMPT_PHOTO_LINK_SUGGEST, get_prompt
from app.core.ai.providers.base import VisionRequest
from app.core.ai.providers.mock import MockVisionProvider
from app.modules.m001.services import task_parser

_CANDIDATES = [{"group_subject_id": "g1", "subject": "math"}]
_M001_SOURCES = [{"seq": 1, "kind": "text", "text_content": "数学：练习册 P23"}]


def _mock_vision(context: dict) -> str:
    return MockVisionProvider().analyze(
        VisionRequest(
            prompt=get_prompt(PROMPT_PHOTO_LINK_SUGGEST),
            images=[],
            context=context,
            response_schema=None,
        )
    ).text


# ============================================================ BUG-003
@pytest.mark.xfail(
    strict=False,
    reason="BUG-003（已修复，哨兵保留）：修复前经服务装配路径建议恒空故 xfailed；修复后应 XPASS；若再次漂移则回落 xfailed",
)
def test_bug003_mock_link_suggest_echoes_candidates():
    """BUG-003 回归哨兵：经服务装配路径，Mock 应回显请求中的候选学科。

    修复前：`out.links == []` → xfailed；修复后（key 对齐 `candidates`）→ XPASS。
    """
    out = suggest_photo_links(
        None,
        family_id="fam",
        photo=PhotoInput(
            photo_id="p1", image=ImageInput(mime="image/jpeg", path=None, image_id="p1")
        ),
        candidates=[SubjectCandidate(group_subject_id="g1", subject="math")],
    )
    assert out.available and out.ok
    assert [link.group_subject_id for link in out.links] == ["g1"]


def test_bug003_evidence_service_yields_empty_links():
    """取证（按修复后事实改写）：服务调用成功（available/ok=True）且**回显候选**为非空建议。

    注：函数名保留以维持用例追溯性（原语义「恒为空」已随 BUG-003 修复反转）。
    """
    out = suggest_photo_links(
        None,
        family_id="fam",
        photo=PhotoInput(
            photo_id="p1", image=ImageInput(mime="image/jpeg", path=None, image_id="p1")
        ),
        candidates=[SubjectCandidate(group_subject_id="g1", subject="math")],
    )
    assert out.available is True and out.ok is True
    assert [link.group_subject_id for link in out.links] == ["g1"]


def test_bug003_evidence_context_key_mismatch():
    """取证（按修复后事实改写）：键名已对齐 —— `candidates` → 有建议；旧键 `candidate_subjects` → 空。

    注：函数名保留以维持用例追溯性（修复前语义相反：`candidates` 空、`candidate_subjects` 有建议）。
    """
    canonical = _mock_vision({"candidates": _CANDIDATES})
    legacy = _mock_vision({"candidate_subjects": _CANDIDATES})

    assert "g1" in canonical
    assert '"links":[]' in legacy.replace(" ", "")


# ============================================================ BUG-004
@pytest.mark.xfail(
    strict=False,
    reason="BUG-004 已由 Task-012 修复（keyword `sources=` + `SourceInput` 适配）→ 本用例现应 XPASS；保留 xfail 标记作回归哨兵（不得删除/放宽 strict）",
)
def test_bug004_m001_default_parser_reaches_core_ai(monkeypatch):
    """应有行为：M001 链路 T 应真正经 `app/core/ai` 解析（修复前必然抛错并静默回退）。"""
    real = task_parser._ai_parser()
    assert real is not None, "核心 AI 解析入口不可用"
    errors: list[str] = []

    def spy(*args, **kwargs):
        try:
            return real(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - 取证需要捕获全部异常类型
            errors.append(type(exc).__name__)
            raise

    monkeypatch.setattr(task_parser, "_ai_parser", lambda: spy)
    drafts = task_parser.default_parser(_M001_SOURCES)
    assert errors == [], f"核心 AI 通路抛错并被 `except Exception: pass` 静默兜底：{errors}"
    assert [draft.subject for draft in drafts] == ["math"]


def test_bug004_evidence_signature_mismatch_and_silent_fallback(monkeypatch, caplog):
    """取证（按修复后事实改写，Task-012）：

    修复前：本用例断言「位置调用必然 TypeError + `default_parser` 兜底结果**逐字等于**
    `mock_parse_sources`（静默回落）」。修复后该前提失效，改为按新实现取证：
    ① 位置调用**仍**必然 TypeError（说明修复点 = 改走 keyword `sources=`）；
    ② 默认路径经核心 AI 真跑返回（入参已适配为 `SourceInput`，keyword 传递）；
    ③ 降级**可观测**（`logger.warning` + 保留本地兜底，不污染事实层）。

    注：函数名保留以维持用例追溯性（沿用 BUG-003 取证用例的处理约定）。
    """
    # ① 位置调用仍必然 TypeError：`sources` 为 keyword-only
    parser = task_parser._ai_parser()
    assert parser is not None
    with pytest.raises(TypeError) as excinfo:
        parser(list(_M001_SOURCES))
    assert "sources" in str(excinfo.value)

    # ② 修复后：默认路径经核心 AI 真跑（capture 入参形态 + 结果）
    captured: dict = {}

    def spy(session, **kwargs):
        captured["session"] = session
        captured["sources"] = kwargs.get("sources")
        return parser(session, **kwargs)

    monkeypatch.setattr(task_parser, "_ai_parser", lambda: spy)
    drafts = task_parser.default_parser(_M001_SOURCES)
    assert [(draft.subject, draft.text) for draft in drafts] == [("math", "练习册 P23")]
    assert captured["session"] is None  # 便捷入口 session 走位置参数（无会话 → 不落 DATA-009）
    assert captured["sources"] and captured["sources"][0].kind == "text"
    assert captured["sources"][0].text == "数学：练习册 P23"  # 已适配 `SourceInput`（非原始 dict）

    # ③ 降级可观测：AI 抛错 → warning 日志 + 保留本地兜底（不污染事实层）
    def boom(session, **kwargs):
        raise RuntimeError("core-ai-down")

    monkeypatch.setattr(task_parser, "_ai_parser", lambda: boom)
    with caplog.at_level(logging.WARNING, logger="app.modules.m001.services.task_parser"):
        fallback = task_parser.default_parser(_M001_SOURCES)
    assert "核心 AI 解析降级" in caplog.text
    assert fallback == task_parser.mock_parse_sources(_M001_SOURCES)
