"""API：家庭认证（API-M001-001 注册 / 002 登录 / 003 登出 + 防爆破）。"""

from uuid import UUID

from tests.conftest import PW, auth, login_family, register_family


def test_register_success(client):
    data = register_family(client, "unique_family")
    UUID(data["family_id"])
    assert data["display_name"] == "unique_family 家庭"


def test_register_duplicate_login_409(client):
    register_family(client, "dup_family")
    resp = client.post(
        "/api/v1/family/register",
        json={"login_name": "dup_family", "password": PW, "display_name": "重复"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "CONFLICT"


def test_register_weak_password_422(client):
    resp = client.post(
        "/api/v1/family/register",
        json={"login_name": "weak_pw", "password": "short1a", "display_name": "弱密码"},  # 过短
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"
    # 仅字母（无数字）也不满足强度
    resp = client.post(
        "/api/v1/family/register",
        json={"login_name": "weak_pw", "password": "abcdefgh", "display_name": "弱密码"},
    )
    assert resp.status_code == 422


def test_login_success_and_logout_invalidate(client):
    register_family(client, "logout_fam")
    token = login_family(client, "logout_fam")
    # 登出后 token 立即失效
    resp = client.post("/api/v1/family/logout", headers=auth(token))
    assert resp.status_code == 204
    resp = client.get("/api/v1/students", headers=auth(token))
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_login_wrong_password_401(client):
    register_family(client, "wrongpw_fam")
    resp = client.post(
        "/api/v1/family/login", json={"login_name": "wrongpw_fam", "password": "WrongPw00"}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_login_unknown_account_401(client):
    resp = client.post("/api/v1/family/login", json={"login_name": "no_such_fam", "password": PW})
    assert resp.status_code == 401


def test_login_bruteforce_locks_account(client):
    register_family(client, "lock_fam")
    for _ in range(5):  # 5 次失败 → 锁定
        client.post("/api/v1/family/login", json={"login_name": "lock_fam", "password": "BadPw000"})
    # 第 5 次触发锁定即 403
    resp = client.post("/api/v1/family/login", json={"login_name": "lock_fam", "password": "BadPw000"})
    assert resp.status_code == 403
    # 即使密码正确也被锁（渐进退避语义）
    resp = client.post("/api/v1/family/login", json={"login_name": "lock_fam", "password": PW})
    assert resp.status_code == 403


def test_protected_routes_require_auth(client):
    for path in ("/api/v1/students", "/api/v1/tasks", "/api/v1/schools"):
        resp = client.get(path)
        assert resp.status_code == 401, path
