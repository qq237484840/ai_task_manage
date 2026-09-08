"""API：作业任务（API-M001-007 创建 / 008 列表 / 009 详情 / 010 更新 / 011 推进）。"""

from tests.conftest import create_student, create_task, valid_task_payload


def _family_a_student(world) -> dict:
    return create_student(world["client"], world["ha"], school_id=world["school_primary"]["school_id"], name="小A")


def test_create_task_draft_masks_answers(world):
    c, ha = world["client"], world["ha"]
    stu = _family_a_student(world)
    body = valid_task_payload(stu["student_id"])
    resp = c.post("/api/v1/tasks", json=body, headers=ha)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"
    assert [i["seq"] for i in data["items"]] == [1, 2]
    # 创建/普通详情默认不返回参考答案（即使属主也须 include_answers=true）
    assert data["items"][0]["reference_answer"] is None


def test_create_task_validation_errors(world):
    c, ha = world["client"], world["ha"]
    stu = _family_a_student(world)
    # 空题目集
    r = c.post("/api/v1/tasks", json=valid_task_payload(stu["student_id"], items=[]), headers=ha)
    assert r.status_code == 422
    # seq 重复
    dup_items = [
        {"seq": 1, "item_type": "objective", "subject": "math", "stem": "a", "reference_answer": "1"},
        {"seq": 1, "item_type": "objective", "subject": "math", "stem": "b", "reference_answer": "2"},
    ]
    r = c.post("/api/v1/tasks", json=valid_task_payload(stu["student_id"], items=dup_items), headers=ha)
    assert r.status_code == 422
    # 主观题带参考答案 → 422（防误导）
    bad_items = [
        {"seq": 1, "item_type": "subjective", "subject": "math", "stem": "写出思路", "reference_answer": "某答案"}
    ]
    r = c.post("/api/v1/tasks", json=valid_task_payload(stu["student_id"], items=bad_items), headers=ha)
    assert r.status_code == 422


def test_create_task_with_other_family_student_404(world):
    c, ha = world["client"], world["ha"]
    other = create_student(world["client"], world["hb"], school_id=world["school_primary"]["school_id"], name="他家")
    r = c.post("/api/v1/tasks", json=valid_task_payload(other["student_id"]), headers=ha)
    assert r.status_code == 404


def test_task_detail_include_answers(world):
    c, ha = world["client"], world["ha"]
    stu = _family_a_student(world)
    task = create_task(c, ha, valid_task_payload(stu["student_id"]))
    # 默认不返回
    masked = c.get(f"/api/v1/tasks/{task['task_id']}", headers=ha).json()
    assert masked["items"][0]["reference_answer"] is None
    # 显式 include_answers=true → 客观题参考答案
    full = c.get(f"/api/v1/tasks/{task['task_id']}?include_answers=true", headers=ha).json()
    assert full["items"][0]["reference_answer"] == "96"
    # 主观题始终无参考答案
    assert full["items"][1]["reference_answer"] is None


def test_task_list_pagination_and_filters(world):
    c, ha = world["client"], world["ha"]
    stu1 = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="甲")
    stu2 = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="乙")
    for i in range(3):
        create_task(c, ha, valid_task_payload(stu1["student_id"], title=f"甲-任务{i}"))
    create_task(c, ha, valid_task_payload(stu2["student_id"], title="乙-任务"))
    # 默认分页
    page = c.get("/api/v1/tasks?page=1&page_size=2", headers=ha).json()
    assert page["total"] == 4 and len(page["items"]) == 2
    # 按学生过滤
    only = c.get(f"/api/v1/tasks?student_id={stu2['student_id']}", headers=ha).json()
    assert only["total"] == 1 and only["items"][0]["student_name"] == "乙"
    # 按状态过滤
    draft_only = c.get("/api/v1/tasks?status=draft", headers=ha).json()
    assert draft_only["total"] == 4
    # 降序（最新在前）
    titles = [i["title"] for i in c.get("/api/v1/tasks?page_size=100", headers=ha).json()["items"]]
    assert titles.index("甲-任务2") < titles.index("甲-任务1")


def test_task_edit_frozen_after_started(world, factory):
    c, ha = world["client"], world["ha"]
    stu = _family_a_student(world)
    task = create_task(c, ha, valid_task_payload(stu["student_id"]))
    # 发布
    r = c.post(f"/api/v1/tasks/{task['task_id']}/status", json={"action": "publish"}, headers=ha)
    assert r.status_code == 200 and r.json()["status"] == "published"
    # 已发布（未开始上传）仍可编辑
    r = c.patch(f"/api/v1/tasks/{task['task_id']}", json={"title": "改过的标题"}, headers=ha)
    assert r.status_code == 200 and r.json()["title"] == "改过的标题"
    # 模拟 M002 首传 → in_progress（内部状态机），此后题目冻结
    with factory() as s:
        from app.modules.m001.services.task_state import TaskStateService
        TaskStateService.mark_in_progress(s, world["family_id_a"], task["task_id"])
        s.commit()
    r = c.patch(f"/api/v1/tasks/{task['task_id']}", json={"title": "不该成功"}, headers=ha)
    assert r.status_code == 409


def test_task_state_machine(world):
    c, ha = world["client"], world["ha"]
    stu = _family_a_student(world)
    task = create_task(c, ha, valid_task_payload(stu["student_id"]))
    tid = task["task_id"]
    # draft -> publish
    assert c.post(f"/api/v1/tasks/{tid}/status", json={"action": "publish"}, headers=ha).json()["status"] == "published"
    # 重复发布：非法（INVALID_TRANSITION 409）
    r = c.post(f"/api/v1/tasks/{tid}/status", json={"action": "publish"}, headers=ha)
    assert r.status_code == 409 and r.json()["code"] == "INVALID_TRANSITION"
    # 草稿阶段不允许 close（新建另一条验证）
    t2 = create_task(c, ha, valid_task_payload(stu["student_id"], title="第二任务"))
    r = c.post(f"/api/v1/tasks/{t2['task_id']}/status", json={"action": "close"}, headers=ha)
    assert r.status_code == 409
    # published -> close
    assert c.post(f"/api/v1/tasks/{tid}/status", json={"action": "close"}, headers=ha).json()["status"] == "closed"
    # closed -> close 再关闭非法
    r = c.post(f"/api/v1/tasks/{tid}/status", json={"action": "close"}, headers=ha)
    assert r.status_code == 409
    # closed -> reopen -> 再 close
    assert c.post(f"/api/v1/tasks/{tid}/status", json={"action": "reopen"}, headers=ha).json()["status"] == "published"
    assert c.post(f"/api/v1/tasks/{tid}/status", json={"action": "close"}, headers=ha).json()["status"] == "closed"
    # 未知 action
    r = c.post(f"/api/v1/tasks/{tid}/status", json={"action": "banana"}, headers=ha)
    assert r.status_code == 422


def test_closed_task_cannot_be_edited(world):
    c, ha = world["client"], world["ha"]
    stu = _family_a_student(world)
    task = create_task(c, ha, valid_task_payload(stu["student_id"]))
    c.post(f"/api/v1/tasks/{task['task_id']}/status", json={"action": "publish"}, headers=ha)
    c.post(f"/api/v1/tasks/{task['task_id']}/status", json={"action": "close"}, headers=ha)
    r = c.patch(f"/api/v1/tasks/{task['task_id']}", json={"title": "不能改"}, headers=ha)
    assert r.status_code == 409


def test_task_update_replace_items(world):
    c, ha = world["client"], world["ha"]
    stu = _family_a_student(world)
    task = create_task(c, ha, valid_task_payload(stu["student_id"]))
    new_items = [
        {"seq": 1, "item_type": "objective", "subject": "math", "stem": "替换后题目", "reference_answer": "ok"},
    ]
    r = c.patch(f"/api/v1/tasks/{task['task_id']}", json={"items": new_items}, headers=ha)
    assert r.status_code == 200
    assert [i["stem"] for i in r.json()["items"]] == ["替换后题目"]


def test_task_update_clear_deadline(world):
    c, ha = world["client"], world["ha"]
    stu = _family_a_student(world)
    task = create_task(c, ha, valid_task_payload(stu["student_id"]))
    r = c.patch(f"/api/v1/tasks/{task['task_id']}", json={"deadline": None}, headers=ha)
    assert r.status_code == 200 and r.json()["deadline"] is None
