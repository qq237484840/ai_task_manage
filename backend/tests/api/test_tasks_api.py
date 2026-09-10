"""API：作业任务（契约 v0.2.0）—— 007 上传输入源 / 008 列表 / 009 详情 / 010 更新 / 011 推进。"""
from __future__ import annotations

from uuid import uuid4

from tests._m001_helpers import (
    DAY,
    TEST_TERM_START,
    create_task_v2,
    image_source,
    install_fixed_window,
    task_payload,
    text_source,
)
from tests.conftest import create_student


def _family_a_student(world, name: str = "小A") -> dict:
    return create_student(
        world["client"], world["ha"], school_id=world["school_primary"]["school_id"], name=name
    )


def test_create_task_from_text_sources(world):
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)
    stu = _family_a_student(world)
    data = create_task_v2(
        c,
        ha,
        task_payload(
            stu["student_id"],
            sources=[text_source("数学：练习册 P23\n语文：背诵《静夜思》")],
        ),
    )
    assert data["belong_date"] == DAY
    assert data["week_index"] == 2
    assert data["window_type"] == "day"
    assert data["spec_status"] == "parsed"
    assert data["status"] == "draft"
    assert [x["subject"] for x in data["contents"]] == ["math", "chinese"]
    assert len(data["sources"]) == 1 and data["sources"][0]["kind"] == "text"


def test_create_task_validation_errors(world):
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY)
    stu = _family_a_student(world)
    sid = stu["student_id"]
    # 空输入源
    r = c.post("/api/v1/tasks", json=task_payload(sid, sources=[]), headers=ha)
    assert r.status_code == 422
    # seq 不连续
    r = c.post(
        "/api/v1/tasks",
        json=task_payload(sid, sources=[text_source("数学：a", seq=1), text_source("语文：b", seq=3)]),
        headers=ha,
    )
    assert r.status_code == 422
    # 文本源缺内容
    r = c.post(
        "/api/v1/tasks",
        json=task_payload(sid, sources=[{"seq": 1, "kind": "text", "text_content": "  "}]),
        headers=ha,
    )
    assert r.status_code == 422
    # 图片源缺 photo_id
    r = c.post(
        "/api/v1/tasks",
        json=task_payload(sid, sources=[{"seq": 1, "kind": "image"}]),
        headers=ha,
    )
    assert r.status_code == 422


def test_create_task_with_other_family_student_404(world):
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY)
    other = create_student(c, world["hb"], school_id=world["school_primary"]["school_id"], name="他家")
    r = c.post("/api/v1/tasks", json=task_payload(other["student_id"]), headers=ha)
    assert r.status_code == 404


def test_same_day_same_student_idempotent_collect(world):
    """同日同类型重复上传 → 同一任务，输入源与内容项**追加**（不新建、不去重）。"""
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY)
    stu = _family_a_student(world)
    t1 = create_task_v2(c, ha, task_payload(stu["student_id"], sources=[text_source("数学：练习册 P23")]))
    t2 = create_task_v2(c, ha, task_payload(stu["student_id"], sources=[text_source("数学：口算 20 题")]))
    assert t1["task_id"] == t2["task_id"]
    assert len(t2["sources"]) == 2
    assert [x["text"] for x in t2["contents"]] == ["练习册 P23", "口算 20 题"]


def test_image_only_source_stays_placeholder(world):
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY)
    stu = _family_a_student(world)
    data = create_task_v2(c, ha, task_payload(stu["student_id"], sources=[image_source(str(uuid4()))]))
    assert data["spec_status"] == "placeholder"
    assert data["contents"] == []
    assert data["sources"][0]["kind"] == "image"


def test_task_list_pagination_and_filters(world):
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)
    stu1 = _family_a_student(world, name="甲")
    stu2 = _family_a_student(world, name="乙")
    create_task_v2(c, ha, task_payload(stu1["student_id"]))
    create_task_v2(c, ha, task_payload(stu2["student_id"], sources=[text_source("语文：背诵")]))
    page = c.get("/api/v1/tasks?page=1&page_size=1", headers=ha).json()
    assert page["total"] == 2 and len(page["items"]) == 1
    only = c.get(f"/api/v1/tasks?student_id={stu2['student_id']}", headers=ha).json()
    assert only["total"] == 1 and only["items"][0]["student_name"] == "乙"
    by_date = c.get(f"/api/v1/tasks?belong_date={DAY}", headers=ha).json()
    assert by_date["total"] == 2
    assert c.get("/api/v1/tasks?week_index=2", headers=ha).json()["total"] == 2
    assert c.get("/api/v1/tasks?week_index=1", headers=ha).json()["total"] == 0


def test_task_detail_returns_contents_and_sources(world):
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY)
    stu = _family_a_student(world)
    task = create_task_v2(c, ha, task_payload(stu["student_id"]))
    detail = c.get(f"/api/v1/tasks/{task['task_id']}", headers=ha).json()
    assert detail["spec_status"] == "parsed" and detail["contents"][0]["subject"] == "math"


def test_task_update_title_contents_and_clear_deadline(world):
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY)
    stu = _family_a_student(world)
    task = create_task_v2(c, ha, task_payload(stu["student_id"]))
    tid = task["task_id"]
    r = c.patch(
        f"/api/v1/tasks/{tid}",
        json={"title": "改过的标题", "contents": [{"subject": "english", "text": "听写单词"}]},
        headers=ha,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"] == "改过的标题"
    assert [(x["subject"], x["text"]) for x in body["contents"]] == [("english", "听写单词")]
    # 设置 + 清除截止时间
    r = c.patch(f"/api/v1/tasks/{tid}", json={"deadline": "2026-09-10T20:00:00Z"}, headers=ha)
    assert r.status_code == 200 and r.json()["deadline"] is not None
    r = c.patch(f"/api/v1/tasks/{tid}", json={"deadline": None}, headers=ha)
    assert r.status_code == 200 and r.json()["deadline"] is None


def test_task_state_machine(world):
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY)
    stu = _family_a_student(world)
    t1 = create_task_v2(c, ha, task_payload(stu["student_id"]))
    tid = t1["task_id"]
    assert c.post(f"/api/v1/tasks/{tid}/status", json={"action": "publish"}, headers=ha).json()["status"] == "published"
    r = c.post(f"/api/v1/tasks/{tid}/status", json={"action": "publish"}, headers=ha)
    assert r.status_code == 409 and r.json()["code"] == "INVALID_TRANSITION"
    # 草稿阶段不允许 close（换一名学生以取得独立的草稿任务）
    stu2 = _family_a_student(world, name="小B")
    t2 = create_task_v2(c, ha, task_payload(stu2["student_id"], sources=[text_source("语文：背诵")]))
    assert c.post(f"/api/v1/tasks/{t2['task_id']}/status", json={"action": "close"}, headers=ha).status_code == 409
    # published -> close -> reopen
    assert c.post(f"/api/v1/tasks/{tid}/status", json={"action": "close"}, headers=ha).json()["status"] == "closed"
    assert c.post(f"/api/v1/tasks/{tid}/status", json={"action": "close"}, headers=ha).status_code == 409
    assert c.post(f"/api/v1/tasks/{tid}/status", json={"action": "reopen"}, headers=ha).json()["status"] == "published"
    # 未知 action → 422
    r = c.post(f"/api/v1/tasks/{tid}/status", json={"action": "banana"}, headers=ha)
    assert r.status_code == 422


def test_task_edit_frozen_after_started(world, factory):
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY)
    stu = _family_a_student(world)
    task = create_task_v2(c, ha, task_payload(stu["student_id"]))
    tid = task["task_id"]
    assert c.post(f"/api/v1/tasks/{tid}/status", json={"action": "publish"}, headers=ha).json()["status"] == "published"
    # 已发布未开始 → 仍可编辑
    assert c.patch(f"/api/v1/tasks/{tid}", json={"title": "未开始可改"}, headers=ha).status_code == 200
    # 模拟 M002 首传 → in_progress，此后冻结
    with factory() as s:
        from app.modules.m001.services.task_state import TaskStateService

        TaskStateService.mark_in_progress(s, world["family_id_a"], tid)
        s.commit()
    r = c.patch(f"/api/v1/tasks/{tid}", json={"title": "不该成功"}, headers=ha)
    assert r.status_code == 409
