"""单测：归属引擎 `WindowResolver`（4 点切日 / 周次 / 周末合并 / 学期内与假期）。"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.config import Settings
from app.modules.m001.services.window_resolver import DefaultWindowResolver

SH = timezone(timedelta(hours=8))  # 测试环境可能无 tzdata，用固定 +08:00


def make_resolver(**overrides) -> DefaultWindowResolver:
    base = {"timezone": "Asia/Shanghai", "term_start": "2026-09-01", "term_end": "", "day_cutoff": "04:00"}
    base.update(overrides)
    return DefaultWindowResolver(Settings(**base))


# —— 4 点切日 ——
@pytest.mark.parametrize(
    "hour,minute,expected",
    [(3, 59, "2026-09-08"), (4, 0, "2026-09-09"), (23, 59, "2026-09-09")],
)
def test_day_cutoff_boundary(hour, minute, expected):
    ts = datetime(2026, 9, 9, hour, minute, tzinfo=SH)
    assert make_resolver().resolve(ts).belong_date == expected


def test_timezone_conversion_from_utc():
    # 2026-09-09T20:00Z = 2026-09-10 04:00 (+08) → 归属日 2026-09-10
    from datetime import timezone

    ts = datetime(2026, 9, 9, 20, 0, tzinfo=timezone.utc)
    assert make_resolver().resolve(ts).belong_date == "2026-09-10"


# —— 周次（AT_TERM_START 所在周周一起算） ——
@pytest.mark.parametrize(
    "d,expected",
    [("2026-08-31", 1), ("2026-09-06", 1), ("2026-09-07", 2), ("2026-09-09", 2), ("2026-09-14", 3)],
)
def test_week_index(d, expected):
    assert make_resolver().window_for_date(date.fromisoformat(d)).week_index == expected


def test_week_index_fallback_without_term_start():
    assert make_resolver(term_start="").window_for_date(date(2026, 9, 9)).week_index == 1


# —— 周末合并（周五/六/日 → 同一 group_key） ——
def test_weekend_merged_group_key():
    r = make_resolver()
    fri = r.window_for_date(date(2026, 9, 11))
    sat = r.window_for_date(date(2026, 9, 12))
    sun = r.window_for_date(date(2026, 9, 13))
    assert {fri.window_type, sat.window_type, sun.window_type} == {"weekend"}
    assert len({fri.group_key, sat.group_key, sun.group_key}) == 1
    assert fri.group_key == "W:2026-09-11"
    assert r.member_dates(fri) == ["2026-09-11", "2026-09-12", "2026-09-13"]


def test_monday_before_cutoff_belongs_to_weekend():
    ts = datetime(2026, 9, 14, 3, 0, tzinfo=SH)  # 周一 03:00 → 仍归属周日
    w = make_resolver().resolve(ts)
    assert w.belong_date == "2026-09-13" and w.window_type == "weekend"


def test_monday_after_cutoff_is_day_window():
    ts = datetime(2026, 9, 14, 4, 0, tzinfo=SH)
    w = make_resolver().resolve(ts)
    assert w.belong_date == "2026-09-14" and w.window_type == "day" and w.group_key == "2026-09-14"


# —— 假期（AT_TERM_END 之后按自然周） ——
def test_holiday_natural_week():
    r = make_resolver(term_end="2026-09-11")
    w = r.window_for_date(date(2026, 9, 16))  # 周三，在假期第 2 自然周
    assert w.window_type == "holiday"
    assert w.group_key == "H:2026-09-14.W2"
    assert r.member_dates(w) == [
        "2026-09-14",
        "2026-09-15",
        "2026-09-16",
        "2026-09-17",
        "2026-09-18",
        "2026-09-19",
        "2026-09-20",
    ]


def test_term_end_day_still_school_window():
    r = make_resolver(term_end="2026-09-11")
    assert r.window_for_date(date(2026, 9, 11)).window_type == "weekend"
    assert r.window_for_date(date(2026, 9, 12)).window_type == "holiday"


def test_policy_version_reflects_config():
    r = make_resolver()
    assert r.policy_version == "v1:Asia/Shanghai|2026-09-01||04:00"
