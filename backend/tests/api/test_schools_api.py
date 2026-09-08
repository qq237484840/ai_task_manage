"""API：学校字典只读（API-M001-012 / DATA-011 公共只读 / ADR-008）。"""

from tests.conftest import login_family, register_family


def _auth_headers(client):
    register_family(client, "school_fam")
    return {"Authorization": f"Bearer {login_family(client, 'school_fam')}"}


def test_list_schools_requires_login(client):
    assert client.get("/api/v1/schools").status_code == 401


def test_list_schools_returns_seed(client):
    h = _auth_headers(client)
    resp = client.get("/api/v1/schools", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] > 0
    stages = {s["stage"] for s in body["items"]}
    assert stages <= {"primary", "junior", "senior"}


def test_filter_by_stage(client):
    h = _auth_headers(client)
    body = client.get("/api/v1/schools?stage=primary&page_size=100", headers=h).json()
    assert body["items"] and all(s["stage"] == "primary" for s in body["items"])
    assert body["total"] == len(body["items"])


def test_filter_by_keyword(client):
    h = _auth_headers(client)
    body = client.get("/api/v1/schools?keyword=实验小学", headers=h).json()
    assert body["items"] and all("实验小学" in s["name"] for s in body["items"])


def test_invalid_stage_query_422(client):
    h = _auth_headers(client)
    assert client.get("/api/v1/schools?stage=university", headers=h).status_code == 422


def test_schools_are_readonly(client):
    """无写路径：POST /schools → 405；PATCH/DELETE 路径不存在 → 404/405（一律非成功）。"""
    h = _auth_headers(client)
    assert client.post("/api/v1/schools", headers=h, json={}).status_code == 405
    for method in ("patch", "delete"):
        resp = getattr(client, method)(
            "/api/v1/schools/00000000-0000-0000-0000-000000000000", headers=h
        )
        assert resp.status_code in (404, 405)
