"""单测：链路 T Mock 解析器（无 `app/core/ai` 时的最低验收路径）。"""
from __future__ import annotations

from app.modules.m001.services.task_parser import ContentDraft, default_parser, mock_parse_sources


def test_mock_parses_subject_labeled_lines():
    drafts = mock_parse_sources(
        [{"kind": "text", "text_content": "数学：练习册 P23\n语文：背诵《静夜思》"}]
    )
    assert drafts == [
        ContentDraft(subject="math", text="练习册 P23"),
        ContentDraft(subject="chinese", text="背诵《静夜思》"),
    ]


def test_mock_splits_on_semicolon_and_marks_unknown_subject():
    drafts = mock_parse_sources([{"kind": "text", "text_content": "英语：听写单词；自由阅读 20 分钟"}])
    assert drafts is not None
    assert drafts[0].subject == "english"
    assert drafts[1].subject == "other"
    assert drafts[1].text == "自由阅读 20 分钟"


def test_mock_image_only_returns_none():
    assert mock_parse_sources([{"kind": "image", "photo_id": "p1"}]) is None


def test_mock_blank_text_returns_none():
    assert mock_parse_sources([{"kind": "text", "text_content": "   "}]) is None


def test_default_parser_falls_back_to_mock():
    # 本任务阶段 `app/core/ai` 未就绪 → 走 Mock 兜底
    drafts = default_parser([{"kind": "text", "text_content": "数学：口算 20 题"}])
    assert drafts is not None and drafts[0].subject == "math"
