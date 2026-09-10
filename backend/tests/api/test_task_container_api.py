"""API：聚合任务（契约 v0.2.0）。

原 CR-001「多学科容器/段级」语义已由 ADR-013 作废；本文件同步为聚合层
（`task_groups` / `task_group_subjects`）用例：019 列表 / 020 详情 / 周末合并。
"""
from __future__ import annotations

from tests._m001_helpers import DAY, FRIDAY, TEST_TERM_START, create_task_v2, install_fixed_window, task_payload, text_source
from tests.conftest import create_student

SATURDAY = "2026-09-12"


def _student(world, name: str = "聚合学生") -> dict:
    return create_student(world["client"], world["ha"], school_id=world["school_primary"]["school_id"], name=name)


def test_day_task_generates_aggregation(world):
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)
    stu = _student(world)
    create_task_v2(c, ha, task_payload(stu["student_id"]))
    body = c.get("/api/v1/task-groups", headers=ha).json()
    assert body["total"] == 1
    group = body["items"][0]
    assert group["group_key"] == DAY and group["window_type"] == "day"
    assert group["display_name"] == "09-09 周三"
    assert group["policy_version"]
    assert [s["subject"] for s in group["subjects"]] == ["math"]
    assert len(group["subjects"][0]["content_refs"]) == 1
    detail = c.get(f"/api/v1/task-groups/{group['group_id']}", headers=ha).json()
    assert detail["group_id"] == group["group_id"]


def test_weekend_days_merge_into_single_aggregation(world):
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    install_fixed_window(c, FRIDAY, term_start=TEST_TERM_START)
    create_task_v2(c, ha, task_payload(stu["student_id"], sources=[text_source("数学：周五作业")]))
    install_fixed_window(c, SATURDAY, term_start=TEST_TERM_START)
    create_task_v2(c, ha, task_payload(stu["student_id"], sources=[text_source("数学：周六作业")]))
    body = c.get(f"/api/v1/task-groups?student_id={stu['student_id']}", headers=ha).json()
    assert body["total"] == 1
    group = body["items"][0]
    assert group["group_key"] == f"W:{FRIDAY}" and group["window_type"] == "weekend"
    assert group["display_name"] == "周末作业"
    assert len(group["subjects"][0]["content_refs"]) == 2  # 两天内容项合并


def test_task_groups_filters(world):
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)
    s1, s2 = _student(world, "甲"), _student(world, "乙")
    create_task_v2(c, ha, task_payload(s1["student_id"]))
    create_task_v2(c, ha, task_payload(s2["student_id"]))
    assert c.get("/api/v1/task-groups", headers=ha).json()["total"] == 2
    assert c.get(f"/api/v1/task-groups?student_id={s1['student_id']}", headers=ha).json()["total"] == 1
    assert c.get("/api/v1/task-groups?window_type=day", headers=ha).json()["total"] == 2
    assert c.get("/api/v1/task-groups?window_type=weekend", headers=ha).json()["total"] == 0
    assert c.get("/api/v1/task-groups?week_index=2", headers=ha).json()["total"] == 2
    assert c.get("/api/v1/task-groups?week_index=5", headers=ha).json()["total"] == 0


def test_task_group_scope_and_404(world):
    c, ha, hb = world["client"], world["ha"], world["hb"]
    install_fixed_window(c, DAY)
    stu = _student(world)
    create_task_v2(c, ha, task_payload(stu["student_id"]))
    gid = c.get("/api/v1/task-groups", headers=ha).json()["items"][0]["group_id"]
    assert c.get(f"/api/v1/task-groups/{gid}", headers=hb).status_code == 404
    assert c.get("/api/v1/task-groups/00000000-0000-0000-0000-000000000000", headers=ha).status_code == 404
    assert c.get("/api/v1/task-groups", headers=hb).json()["total"] == 0
