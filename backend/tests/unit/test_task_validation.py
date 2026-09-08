"""单测：题目集业务校验（seq 连续唯一 + 主客观参考答案规则）。"""

import pytest
from pydantic import ValidationError

from app.modules.m001.schemas.task import TaskItemIn
from app.modules.m001.services.task_service import validate_items
from app.shared.exceptions import ValidationAppError


def item(seq: int, item_type: str = "objective", answer: str | None = "答案") -> TaskItemIn:
    return TaskItemIn(
        seq=seq,
        item_type=item_type,
        subject="math",
        stem=f"第{seq}题",
        reference_answer=answer,
    )


def test_empty_items_rejected():
    with pytest.raises(ValidationAppError):
        validate_items([])


def test_duplicate_seq_rejected():
    with pytest.raises(ValidationAppError):
        validate_items([item(1), item(1)])


def test_non_contiguous_seq_rejected():
    with pytest.raises(ValidationAppError):
        validate_items([item(1), item(3)])


def test_unordered_items_normalized_to_seq_order():
    out = validate_items([item(2), item(1)])
    assert [o["seq"] for o in out] == [1, 2]
    assert out[0]["stem"] == "第1题"


def test_subjective_item_rejects_reference_answer():
    with pytest.raises(ValidationError):
        item(1, item_type="subjective", answer="有答案")


def test_subjective_item_without_answer_ok():
    it = TaskItemIn(seq=1, item_type="subjective", subject="math", stem="写出计算过程", reference_answer=None)
    out = validate_items([it])[0]
    assert out["reference_answer"] is None


def test_objective_item_without_answer_allowed():
    it = TaskItemIn(seq=1, item_type="objective", subject="math", stem="1+1=?", reference_answer=None)
    out = validate_items([it])[0]
    assert out["reference_answer"] is None
