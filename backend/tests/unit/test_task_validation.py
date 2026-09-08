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


# —— CR-001 容器化：学科作业段 group_no 结构约束 ——


def gitem(
    seq: int,
    *,
    group_no: int = 0,
    subject: str = "math",
    item_type: str = "objective",
    answer: str | None = "答案",
) -> TaskItemIn:
    return TaskItemIn(
        seq=seq,
        item_type=item_type,
        subject=subject,
        group_no=group_no,
        stem=f"第{seq}题",
        reference_answer=answer,
    )


def test_default_single_segment_mixed_subject_ok():
    """全 0 = 默认单段（旧数据兼容），允许跨科目同段。"""
    out = validate_items([gitem(1, subject="math"), gitem(2, subject="chinese")])
    assert [o["group_no"] for o in out] == [0, 0]


def test_explicit_groups_ok():
    out = validate_items([gitem(1, group_no=1), gitem(2, group_no=1), gitem(3, group_no=2)])
    assert [o["group_no"] for o in out] == [1, 1, 2]


def test_explicit_groups_must_start_at_one():
    with pytest.raises(ValidationAppError):
        validate_items([gitem(1, group_no=2), gitem(2, group_no=2)])


def test_explicit_groups_must_be_contiguous():
    with pytest.raises(ValidationAppError):
        validate_items([gitem(1, group_no=1), gitem(2, group_no=3)])


def test_mixing_group_zero_with_explicit_rejected():
    with pytest.raises(ValidationAppError):
        validate_items([gitem(1, group_no=0), gitem(2, group_no=1)])


def test_group_internal_subject_must_be_uniform():
    with pytest.raises(ValidationAppError):
        validate_items([gitem(1, group_no=1, subject="math"), gitem(2, group_no=1, subject="english")])


def test_group_blocks_must_be_contiguous_no_interleave():
    with pytest.raises(ValidationAppError):
        validate_items([gitem(1, group_no=1), gitem(2, group_no=2), gitem(3, group_no=1)])


def test_group_no_preserved_in_output():
    out = validate_items([gitem(1, group_no=1, subject="math"), gitem(2, group_no=2, subject="chinese")])
    assert out[1]["group_no"] == 2 and out[1]["subject"] == "chinese"
