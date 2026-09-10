"""API：家庭隔离矩阵与敏感信息不落日志（越权统一 404/401 防探测）。"""
from __future__ import annotations

import logging

from tests._m001_helpers import DAY, create_task_v2, install_fixed_window, task_payload, text_source
from tests.conftest import create_student


def _student_a(world) -> dict:
    return create_student(world["client"], world["ha"], school_id=world["school_primary"]["school_id"], name="越权目标")


def test_cross_family_matrix(world):
    c, ha, hb = world["client"], world["ha"], world["hb"]
    install_fixed_window(c, DAY)
    stu = _student_a(world)
    task = create_task_v2(c, ha, task_payload(stu["student_id"]))
    tid = task["task_id"]
    # B 对 A 任务：详情 / 更新 / 推进 → 一律 404（不泄露存在性）；
    # 归属引擎上线后 include_answers 已随参考答案面退役（未知查询参数被忽略，仍走 404）
    assert c.get(f"/api/v1/tasks/{tid}", headers=hb).status_code == 404
    assert c.patch(f"/api/v1/tasks/{tid}", json={"title": "越权"}, headers=hb).status_code == 404
    assert c.post(f"/api/v1/tasks/{tid}/status", json={"action": "publish"}, headers=hb).status_code == 404
    # B 列表里看不到 A 的任务
    assert c.get("/api/v1/tasks", headers=hb).json()["total"] == 0
    assert c.get("/api/v1/students", headers=hb).json() == []


def test_unauthenticated_access_denied(world):
    c = world["client"]
    for path in ("/api/v1/students", "/api/v1/tasks", "/api/v1/task-groups", "/api/v1/schools"):
        assert c.get(path).status_code == 401
    assert c.post("/api/v1/family/logout").status_code == 401


def test_no_sensitive_data_in_logs(world, caplog):
    """密码 / token / 学生姓名 / 输入源机密文本 不得出现在审计或应用日志（DEVELOPMENT_GUIDE §7）。"""
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY)
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="日志小明")
    payload = task_payload(stu["student_id"], sources=[text_source("数学：S3CR3T-STEM")])
    with caplog.at_level(logging.INFO):
        task = create_task_v2(c, ha, payload)
        c.post("/api/v1/family/login", json={"login_name": "family_a", "password": "Passw0rd1"})
        c.patch(f"/api/v1/tasks/{task['task_id']}", json={"title": "改标题"}, headers=ha)
        c.post("/api/v1/family/logout", headers=world["ha"])
    text = caplog.text
    assert "Passw0rd1" not in text
    assert "S3CR3T-STEM" not in text
    assert "日志小明" not in text
    assert world["token_a"] not in text
    # 审计事件本身应存在
    assert "task_ingested" in text
    assert "family_login" in text
