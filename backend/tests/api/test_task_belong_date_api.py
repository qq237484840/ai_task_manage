"""API-M001-021：手工改归属日（幂等 / 校验 / 已消费禁改 409 / 跨聚合迁移）。"""
from __future__ import annotations

from tests._m001_helpers import DAY, MONDAY_NEXT, TEST_TERM_START, create_task_v2, install_fixed_window, task_payload
from tests.conftest import create_student


def _setup(world, name: str = "改归属学生") -> dict:
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name=name)
    return create_task_v2(c, ha, task_payload(stu["student_id"]))


def test_change_belong_date_moves_group(world):
    c, ha = world["client"], world["ha"]
    task = _setup(world)
    r = c.post(
        f"/api/v1/tasks/{task['task_id']}/belong-date",
        json={"belong_date": MONDAY_NEXT},
        headers=ha,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["belong_date"] == MONDAY_NEXT and body["week_index"] == 3 and body["window_type"] == "day"
    groups = c.get("/api/v1/task-groups", headers=ha).json()
    assert groups["total"] == 1
    assert groups["items"][0]["group_key"] == MONDAY_NEXT  # 源聚合已删除，仅剩新聚合


def test_change_belong_date_idempotent(world):
    c, ha = world["client"], world["ha"]
    task = _setup(world)
    r = c.post(f"/api/v1/tasks/{task['task_id']}/belong-date", json={"belong_date": DAY}, headers=ha)
    assert r.status_code == 200 and r.json()["belong_date"] == DAY


def test_change_belong_date_bad_format_422(world):
    c, ha = world["client"], world["ha"]
    task = _setup(world)
    r = c.post(
        f"/api/v1/tasks/{task['task_id']}/belong-date", json={"belong_date": "09/09/2026"}, headers=ha
    )
    assert r.status_code == 422


def test_change_belong_date_other_family_404(world):
    c, hb = world["client"], world["hb"]
    task = _setup(world)
    r = c.post(f"/api/v1/tasks/{task['task_id']}/belong-date", json={"belong_date": MONDAY_NEXT}, headers=hb)
    assert r.status_code == 404


def test_change_belong_date_rejected_after_consumed(world, factory):
    from app.modules.m001.services.aggregation_service import TaskAggregationService

    c, ha = world["client"], world["ha"]
    task = _setup(world, name="已消费学生")
    group = c.get("/api/v1/task-groups", headers=ha).json()["items"][0]
    subj_id = group["subjects"][0]["group_subject_id"]
    with factory() as s:
        TaskAggregationService.commit_conclusion(
            s, world["family_id_a"], subj_id, "pass", status="confirmed"
        )
        s.commit()
    r = c.post(
        f"/api/v1/tasks/{task['task_id']}/belong-date", json={"belong_date": MONDAY_NEXT}, headers=ha
    )
    assert r.status_code == 409
