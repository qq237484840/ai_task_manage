"""AI 返回结构校验测试：合规通过、不合规必须拦截（不得流入上游）。"""
from __future__ import annotations

import pytest

from app.core.ai.errors import AIError, AIErrorCode
from app.core.ai.providers.base import extract_json_text, validate_structured
from app.core.ai.schemas import (
    CompletionAnalysisResult,
    PhotoLinkSuggestionResult,
    TaskSpecParseResult,
)

VALID_PARSE = (
    '{"subjects":[{"subject":"Math","contents":[{"text":"口算 20 题"}],"confidence":0.9}],'
    '"confidence":0.9}'
)


def test_extract_json_tolerates_code_fence_and_prose():
    raw = '好的，结果如下：\n```json\n{"a": 1}\n```\n以上。'
    assert extract_json_text(raw) == '{"a": 1}'


def test_validate_plain_json_ok():
    result = validate_structured(VALID_PARSE, TaskSpecParseResult)
    assert isinstance(result, TaskSpecParseResult)
    assert result.subjects[0].subject == "math"  # 归一化为小写
    assert result.subjects[0].contents[0].text == "口算 20 题"


def test_validate_fenced_json_ok():
    raw = '```json\n{"links":[],"confidence":0.0}\n```'
    assert isinstance(validate_structured(raw, PhotoLinkSuggestionResult), PhotoLinkSuggestionResult)


def test_rejects_empty_output():
    with pytest.raises(AIError) as exc:
        validate_structured("", TaskSpecParseResult)
    assert exc.value.code is AIErrorCode.INVALID_OUTPUT


def test_rejects_non_json_output():
    with pytest.raises(AIError) as exc:
        validate_structured("模型拒绝回答", TaskSpecParseResult)
    assert exc.value.code is AIErrorCode.INVALID_OUTPUT


def test_rejects_confidence_out_of_range():
    bad = '{"subjects":[],"confidence":2.0}'
    with pytest.raises(AIError) as exc:
        validate_structured(bad, TaskSpecParseResult)
    assert exc.value.code is AIErrorCode.INVALID_OUTPUT


def test_rejects_missing_required_conclusion():
    with pytest.raises(AIError) as exc:
        validate_structured('{"evidence_photo_ids":[],"confidence":0.5}', CompletionAnalysisResult)
    assert exc.value.code is AIErrorCode.INVALID_OUTPUT


def test_rejects_illegal_conclusion_value():
    bad = '{"conclusion":"很棒","evidence_photo_ids":[],"confidence":0.5}'
    with pytest.raises(AIError) as exc:
        validate_structured(bad, CompletionAnalysisResult)
    assert exc.value.code is AIErrorCode.INVALID_OUTPUT


def test_rejects_unknown_extra_field():
    """extra=forbid：模型多输出未定义字段（可能是主观标签）必须被拦截。"""
    bad = '{"conclusion":"完成","evidence_photo_ids":[],"confidence":0.5,"attitude":"认真"}'
    with pytest.raises(AIError) as exc:
        validate_structured(bad, CompletionAnalysisResult)
    assert exc.value.code is AIErrorCode.INVALID_OUTPUT


def test_illegal_output_is_retryable():
    err = AIError(AIErrorCode.INVALID_OUTPUT)
    assert err.retryable is True


def test_permanent_codes_not_retryable():
    assert AIError(AIErrorCode.CONTENT_REFUSED).retryable is False
    assert AIError(AIErrorCode.AUTH_ERROR).retryable is False
    assert AIError(AIErrorCode.CONFIG_ERROR).retryable is False
