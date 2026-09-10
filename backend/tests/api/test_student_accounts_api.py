"""API：学生子账号与双主体隔离（ACR-001）。

覆盖：开通/停用/改密（家长操作）、学生登录（独立命名空间）、
student 主体仅本人读写（越权一律 404/403）、family 行为向后兼容。
"""
from __future__ import annotations

import pytest

from tests._m001_helpers import task_payload
from tests.conftest import PW, create_student


def open_account(client, headers, student_id, login, password=PW) -> dict:
    resp = client.post(
        f"/api/v1/students/{student_id}/account",
        json={"login_name": login, "password": password},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def login_student(client, login, password=PW) -> str:
    resp = client.post("/api/v1/student/login", json={"login_name": login, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


def make_student(client, headers, school_id, name="小明") -> dict:
    return create_student(client, headers, school_id=school_id, name=name)


# —— 开通 / 停用 / 改密（家长专属） ——


def test_open_student_account_success(world):
    c, ha = world["client"], world["ha"]
    stu = make_student(c, ha, world["school_primary"]["school_id"])
    body = open_account(c, ha, stu["student_id"], "stu_ming")
    assert body["student_id"] == stu["student_id"]
    assert body["login_name"] == "stu_ming"
    assert body["status"] == "active"
    assert body["password_warning"] is None  # 强口令无提示


def test_open_student_account_weak_password_warns(world):
    c, ha = world["client"], world["ha"]
    stu = make_student(c, ha, world["school_primary"]["school_id"])
    body = open_account(c, ha, stu["student_id"], "stu_weak", password="abc123")
    assert body["password_warning"] is not None


def test_open_student_account_duplicate_conflict(world):
    c, ha = world["client"], world["ha"]
    s1 = make_student(c, ha, world["school_primary"]["school_id"], name="孩子甲")
    s2 = make_student(c, ha, world["school_primary"]["school_id"], name="孩子乙")
    open_account(c, ha, s1["student_id"], "stu_dup")
    # 同一学生重复开通 → 409
    r = c.post(
        f"/api/v1/students/{s1['student_id']}/account",
        json={"login_name": "stu_dup2", "password": PW},
        headers=ha,
    )
    assert r.status_code == 409
    # 登录名被他人占用 → 409
    r = c.post(
        f"/api/v1/students/{s2['student_id']}/account",
        json={"login_name": "stu_dup", "password": PW},
        headers=ha,
    )
    assert r.status_code == 409


def test_open_student_account_cross_family_404(world):
    c, ha, hb = world["client"], world["ha"], world["hb"]
    stu = make_student(c, ha, world["school_primary"]["school_id"])
    r = c.post(
        f"/api/v1/students/{stu['student_id']}/account",
        json={"login_name": "intruder", "password": PW},
        headers=hb,
    )
    assert r.status_code == 404


def test_update_student_account_disable_reenable(world):
    c, ha = world["client"], world["ha"]
    stu = make_student(c, ha, world["school_primary"]["school_id"])
    open_account(c, ha, stu["student_id"], "stu_toggle")
    r = c.patch(f"/api/v1/students/{stu['student_id']}/account", json={"status": "disabled"}, headers=ha)
    assert r.status_code == 200 and r.json()["status"] == "disabled"
    r = c.patch(f"/api/v1/students/{stu['student_id']}/account", json={"status": "active"}, headers=ha)
    assert r.status_code == 200 and r.json()["status"] == "active"


def test_update_student_account_rotate_password(world):
    c, ha = world["client"], world["ha"]
    stu = make_student(c, ha, world["school_primary"]["school_id"])
    open_account(c, ha, stu["student_id"], "stu_pwd")
    r = c.patch(
        f"/api/v1/students/{stu['student_id']}/account", json={"password": "NewPassw0rd"}, headers=ha
    )
    assert r.status_code == 200
    # 旧口令失效、新口令可用
    assert c.post("/api/v1/student/login", json={"login_name": "stu_pwd", "password": PW}).status_code == 401
    assert c.post(
        "/api/v1/student/login", json={"login_name": "stu_pwd", "password": "NewPassw0rd"}
    ).status_code == 200


def test_update_student_account_empty_payload_422(world):
    c, ha = world["client"], world["ha"]
    stu = make_student(c, ha, world["school_primary"]["school_id"])
    open_account(c, ha, stu["student_id"], "stu_empty")
    # 无任何显式字段仍合法（PATCH 语义允许 no-op），此处校验非法 status 值
    r = c.patch(
        f"/api/v1/students/{stu['student_id']}/account", json={"status": "banned"}, headers=ha
    )
    assert r.status_code == 422


# —— 学生登录 / 主体信息 / 登出 ——


def test_student_login_and_me(world):
    c, ha = world["client"], world["ha"]
    stu = make_student(c, ha, world["school_primary"]["school_id"], name="朵朵")
    open_account(c, ha, stu["student_id"], "stu_duoduo")
    resp = c.post("/api/v1/student/login", json={"login_name": "stu_duoduo", "password": PW})
    assert resp.status_code == 200
    body = resp.json()
    assert body["subject_type"] == "student"
    assert body["student_id"] == stu["student_id"]
    assert body["student_name"] == "朵朵"
    me = c.get("/api/v1/student/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200
    assert me.json()["student_id"] == stu["student_id"]
    assert me.json()["name"] == "朵朵"


def test_student_login_wrong_password_or_unknown_401(world):
    c, ha = world["client"], world["ha"]
    stu = make_student(c, ha, world["school_primary"]["school_id"])
    open_account(c, ha, stu["student_id"], "stu_secret")
    assert c.post("/api/v1/student/login", json={"login_name": "stu_secret", "password": "Wrong000"}).status_code == 401
    assert c.post("/api/v1/student/login", json={"login_name": "no_such_stu", "password": PW}).status_code == 401


def test_student_login_disabled_401(world):
    c, ha = world["client"], world["ha"]
    stu = make_student(c, ha, world["school_primary"]["school_id"])
    open_account(c, ha, stu["student_id"], "stu_off")
    c.patch(f"/api/v1/students/{stu['student_id']}/account", json={"status": "disabled"}, headers=ha)
    assert c.post("/api/v1/student/login", json={"login_name": "stu_off", "password": PW}).status_code == 401


def test_student_logout_invalidates_token(world):
    c, ha = world["client"], world["ha"]
    stu = make_student(c, ha, world["school_primary"]["school_id"])
    open_account(c, ha, stu["student_id"], "stu_out")
    token = login_student(c, "stu_out")
    hs = {"Authorization": f"Bearer {token}"}
    assert c.get("/api/v1/student/me", headers=hs).status_code == 200
    assert c.post("/api/v1/student/logout", headers=hs).status_code == 204
    assert c.get("/api/v1/student/me", headers=hs).status_code == 401


def test_student_me_rejects_family_token(world):
    c, ha = world["client"], world["ha"]
    assert c.get("/api/v1/student/me", headers=ha).status_code == 403


def test_login_namespace_isolation_between_family_and_student(world):
    """family 与 student 命名空间独立：同名 login_name 可并存且各自可用。"""
    c, ha = world["client"], world["ha"]
    # family_a 已在 conftest 注册（login_name=family_a）；再造一个同 login_name 的学生账号
    stu = make_student(c, ha, world["school_primary"]["school_id"])
    open_account(c, ha, stu["student_id"], "family_a")
    token = login_student(c, "family_a")
    assert c.get("/api/v1/student/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


# —— student 主体越权矩阵 ——


@pytest.fixture
def student_session(world):
    """A 家家长 + 两名学生（老大有子账号并登录）+ 他人任务若干。"""
    c, ha = world["client"], world["ha"]
    s1 = make_student(c, ha, world["school_primary"]["school_id"], name="老大")
    s2 = make_student(c, ha, world["school_primary"]["school_id"], name="老二")
    open_account(c, ha, s1["student_id"], "stu_elder")
    token = login_student(c, "stu_elder")
    hs = {"Authorization": f"Bearer {token}"}
    return {"client": c, "ha": ha, "hs": hs, "s1": s1, "s2": s2, "token": token}


def test_student_list_students_shows_self_only(student_session):
    c, hs = student_session["client"], student_session["hs"]
    names = [s["name"] for s in c.get("/api/v1/students", headers=hs).json()]
    assert names == ["老大"]


def test_student_patch_other_profile_404(student_session):
    c, hs, s2 = student_session["client"], student_session["hs"], student_session["s2"]
    r = c.patch(f"/api/v1/students/{s2['student_id']}", json={"name": "篡改"}, headers=hs)
    assert r.status_code == 404


def test_student_patch_self_profile_ok(student_session):
    c, hs, s1 = student_session["client"], student_session["hs"], student_session["s1"]
    r = c.patch(f"/api/v1/students/{s1['student_id']}", json={"name": "老大大"}, headers=hs)
    assert r.status_code == 200 and r.json()["name"] == "老大大"


def test_student_cannot_create_student_profile_403(student_session):
    c, hs = student_session["client"], student_session["hs"]
    r = c.post(
        "/api/v1/students",
        json={"name": "新档案", "school_id": student_session["s1"]["school"]["school_id"]},
        headers=hs,
    )
    assert r.status_code == 403


def test_student_cannot_manage_account_403(student_session):
    """学生不能开通/停用任何子账号（含本人）。"""
    c, hs, s1 = student_session["client"], student_session["hs"], student_session["s1"]
    assert c.post(
        f"/api/v1/students/{s1['student_id']}/account",
        json={"login_name": "hack", "password": PW},
        headers=hs,
    ).status_code == 403
    assert c.patch(f"/api/v1/students/{s1['student_id']}/account", json={"status": "disabled"}, headers=hs).status_code == 403


def _seed_tasks_for_matrix(world, student_session) -> dict:
    """构造：s1 任务 t1、s2 任务 t2（同家）、B 家任务 t3。"""
    c, ha = world["client"], world["ha"]
    t1 = c.post(
        "/api/v1/tasks", json=task_payload(student_session["s1"]["student_id"]), headers=ha
    )
    assert t1.status_code == 201
    t2 = c.post(
        "/api/v1/tasks",
        json=task_payload(student_session["s2"]["student_id"], sources=[{"seq": 1, "kind": "text", "text_content": "语文：背诵"}]),
        headers=ha,
    )
    assert t2.status_code == 201
    other = create_student(c, world["hb"], school_id=world["school_primary"]["school_id"], name="B家")
    t3 = c.post("/api/v1/tasks", json=task_payload(other["student_id"]), headers=world["hb"])
    assert t3.status_code == 201
    return {"t1": t1.json(), "t2": t2.json(), "t3": t3.json()}


def test_student_task_list_self_only_and_query_other_404(world, student_session):
    tasks = _seed_tasks_for_matrix(world, student_session)
    c, hs, s2 = student_session["client"], student_session["hs"], student_session["s2"]
    listing = c.get("/api/v1/tasks", headers=hs).json()
    assert listing["total"] == 1 and listing["items"][0]["task_id"] == tasks["t1"]["task_id"]
    # 显式查询他人 → 404（防探测）
    assert c.get(f"/api/v1/tasks?student_id={s2['student_id']}", headers=hs).status_code == 404


def test_student_task_crud_other_404(world, student_session):
    tasks = _seed_tasks_for_matrix(world, student_session)
    c, hs = student_session["client"], student_session["hs"]
    other_id = tasks["t2"]["task_id"]
    assert c.get(f"/api/v1/tasks/{other_id}", headers=hs).status_code == 404
    assert c.patch(f"/api/v1/tasks/{other_id}", json={"title": "篡改"}, headers=hs).status_code == 404
    assert c.post(f"/api/v1/tasks/{other_id}/status", json={"action": "close"}, headers=hs).status_code == 404


def test_student_task_detail_own(world, student_session):
    tasks = _seed_tasks_for_matrix(world, student_session)
    c, hs = student_session["client"], student_session["hs"]
    own = tasks["t1"]["task_id"]
    body = c.get(f"/api/v1/tasks/{own}", headers=hs)
    assert body.status_code == 200 and body.json()["student_id"] == student_session["s1"]["student_id"]


def test_student_create_task_self_ok_other_404(world, student_session):
    _seed_tasks_for_matrix(world, student_session)
    c, hs, s1, s2 = (
        student_session["client"],
        student_session["hs"],
        student_session["s1"],
        student_session["s2"],
    )
    own = c.post("/api/v1/tasks", json=task_payload(s1["student_id"]), headers=hs)
    assert own.status_code == 201 and own.json()["status"] == "draft"
    other = c.post("/api/v1/tasks", json=task_payload(s2["student_id"]), headers=hs)
    assert other.status_code == 404


def test_student_status_flow_own_task(world, student_session):
    c, ha, hs, s1 = (
        world["client"],
        world["ha"],
        student_session["hs"],
        student_session["s1"],
    )
    task = c.post("/api/v1/tasks", json=task_payload(s1["student_id"]), headers=ha).json()
    r = c.post(f"/api/v1/tasks/{task['task_id']}/status", json={"action": "publish"}, headers=hs)
    assert r.status_code == 200 and r.json()["status"] == "published"
