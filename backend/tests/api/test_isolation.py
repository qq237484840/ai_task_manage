"""API：家庭隔离矩阵与敏感信息不落日志（越权统一 404/401 防探测）。"""

import logging

from tests.conftest import create_student, create_task, valid_task_payload


def _student_a(world) -> dict:
    return create_student(world["client"], world["ha"], school_id=world["school_primary"]["school_id"], name="越权目标")


def test_cross_family_matrix(world):
    c, ha, hb = world["client"], world["ha"], world["hb"]
    stu = _student_a(world)
    task = create_task(c, ha, valid_task_payload(stu["student_id"]))
    tid = task["task_id"]
    # B 改 A 学生 → 404（覆盖于 test_students_api；此处复核列表隔离）
    # B 对 A 任务：详情 / 更新 / 推进 / 携 include_answers 探测 → 一律 404（不泄露存在性）
    assert c.get(f"/api/v1/tasks/{tid}", headers=hb).status_code == 404
    assert c.get(f"/api/v1/tasks/{tid}?include_answers=true", headers=hb).status_code == 404
    assert c.patch(f"/api/v1/tasks/{tid}", json={"title": "越权"}, headers=hb).status_code == 404
    assert c.post(f"/api/v1/tasks/{tid}/status", json={"action": "publish"}, headers=hb).status_code == 404
    # B 列表里看不到 A 的任务
    assert c.get("/api/v1/tasks", headers=hb).json()["total"] == 0
    assert c.get("/api/v1/students", headers=hb).json() == []


def test_unauthenticated_access_denied(world):
    c = world["client"]
    for path in ("/api/v1/students", "/api/v1/tasks", "/api/v1/schools"):
        assert c.get(path).status_code == 401
    # 登出必须认证（POST 匹配，GET 无此路径）
    assert c.post("/api/v1/family/logout").status_code == 401


def test_no_sensitive_data_in_logs(world, caplog):
    """密码 / token / 学生姓名 / 参考答案 不得出现在审计或应用日志（DEVELOPMENT_GUIDE §7）。"""
    c, ha = world["client"], world["ha"]
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="日志小明")
    payload = valid_task_payload(
        stu["student_id"], items=[{"seq": 1, "item_type": "objective", "subject": "math", "stem": "S3CR3T-STEM", "reference_answer": "S3CR3T-ANS"}]
    )
    with caplog.at_level(logging.INFO):
        create_task(c, ha, payload)
        c.post("/api/v1/family/login", json={"login_name": "family_a", "password": "Passw0rd1"})
        c.patch(f"/api/v1/tasks/{create_task(c, ha, payload)['task_id']}", json={"title": "改标题"}, headers=ha)
        c.post("/api/v1/family/logout", headers=world["ha"])
    text = caplog.text
    assert "Passw0rd1" not in text
    assert "S3CR3T-STEM" not in text
    assert "S3CR3T-ANS" not in text
    assert "日志小明" not in text
    assert world["token_a"] not in text
    # 审计事件本身应存在
    assert "task_created" in text
    assert "family_login" in text
