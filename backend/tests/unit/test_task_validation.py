"""单测：契约 v0.2.0 入参校验（输入源 seq 连续 / 内容项 / 改归属日 / 隐式确认）。"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.m001.schemas.task import (
    BelongDateChange,
    ContentItemIn,
    ParseConfirmation,
    SourceIn,
    TaskIngest,
)
from app.modules.m001.services.task_service import validate_sources
from app.shared.exceptions import ValidationAppError


def src(seq: int, kind: str = "text", text: str = "数学：练习题", photo_id: str | None = None) -> SourceIn:
    return SourceIn(seq=seq, kind=kind, text_content=text if kind == "text" else None, photo_id=photo_id)


# —— validate_sources ——
def test_empty_sources_rejected():
    with pytest.raises(ValidationAppError):
        validate_sources([])


def test_non_contiguous_seq_rejected():
    with pytest.raises(ValidationAppError):
        validate_sources([src(1), src(3)])


def test_seq_must_start_at_one():
    with pytest.raises(ValidationAppError):
        validate_sources([src(2), src(3)])


def test_unordered_sources_normalized_to_seq_order():
    out = validate_sources([src(2, text="语文：背诵"), src(1)])
    assert [o["seq"] for o in out] == [1, 2]
    assert out[1]["text_content"] == "语文：背诵"


# —— SourceIn 段落契约 ——
def test_text_source_requires_text():
    with pytest.raises(ValidationError):
        SourceIn(seq=1, kind="text", text_content="   ")


def test_image_source_requires_photo_id():
    with pytest.raises(ValidationError):
        SourceIn(seq=1, kind="image")


def test_text_source_ignores_photo_id():
    s = SourceIn(seq=1, kind="text", text_content="数学：题", photo_id="11111111-1111-1111-1111-111111111111")
    assert s.photo_id is None


def test_task_ingest_requires_at_least_one_source():
    with pytest.raises(ValidationError):
        TaskIngest(student_id="11111111-1111-1111-1111-111111111111", sources=[])


# —— 内容项归一化 ——
def test_content_subject_normalized_and_blank_rejected():
    assert ContentItemIn(subject="  Math ", text=" 1+1 ").subject == "math"
    with pytest.raises(ValidationError):
        ContentItemIn(subject="   ", text="x")


# —— 改归属日 ——
@pytest.mark.parametrize("bad", ["2026/09/09", "2026-9-9", "not-a-date", "2026-02-30", ""])
def test_belong_date_change_rejects_bad_format(bad):
    with pytest.raises(ValidationError):
        BelongDateChange(belong_date=bad)


def test_belong_date_change_ok():
    assert BelongDateChange(belong_date="2026-09-09").belong_date == "2026-09-09"


# —— 隐式确认必须携带摘要（防盲确认） ——
def test_implicit_confirmation_requires_digest():
    with pytest.raises(ValidationError):
        ParseConfirmation(implicit=True)
    ok = ParseConfirmation(implicit=True, digest={"subjects": ["math"], "content_texts": ["题"]})
    assert ok.implicit is True
