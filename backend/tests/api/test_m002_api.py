"""M002 图片上传/归属 REST 集成测试（API-M002-001~006）。

覆盖：建批次、单张上传、列表、受控取图、归属/驳回、删除、双主体越权。
"""
from __future__ import annotations

import io
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from PIL import Image, ImageDraw

from app.modules.m002.config import M002Settings, get_m002_settings
from tests.conftest import create_student
from tests.m002_support import make_task_row, m002_infra  # noqa: F401 - pytest fixture


@pytest.fixture(autouse=True)
def m002_settings(tmp_path, client):
    """autouse：本模块所有上传用例都把图片存储根目录重定向到临时目录，避免污染 backend/data/images。

    上传/取图/删除的文件路径均来自路由 Depends(get_m002_settings) 注入，
    因此 DI override 即可全覆盖；关联服务内部仅读 limit 等数值，不受影响。
    """
    s = M002Settings(image_store_root=str(tmp_path / "images"))
    client.app.dependency_overrides[get_m002_settings] = lambda: s
    yield s
    client.app.dependency_overrides.pop(get_m002_settings, None)


def _valid_jpeg(bg: int = 205) -> bytes:
    """生成一张可通过质检的合成作业图（JPEG）。"""
    w, h = 640, 480
    img = Image.new("RGB", (w, h), (bg, bg, bg))
    d = ImageDraw.Draw(img)
    y = 60
    while y < h - 60:
        d.rectangle([60, y, w - 60, y + 12], fill=0)
        y += 60
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _dark_jpeg() -> bytes:
    """明显过暗、应触发 too_dark 的图片。"""
    img = Image.new("RGB", (320, 240), (15, 15, 15))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _student_a(world):
    return create_student(
        world["client"],
        world["ha"],
        school_id=world["school_primary"]["school_id"],
        name="小图",
    )


def _open_student_account(client, headers, student_id: str, login_name: str, password: str):
    resp = client.post(
        f"/api/v1/students/{student_id}/account",
        json={"login_name": login_name, "password": password},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _login_student(client, login_name: str, password: str) -> str:
    resp = client.post(
        "/api/v1/student/login", json={"login_name": login_name, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


def _create_batch(client, headers, student_id: str) -> dict:
    resp = client.post(
        "/api/v1/upload-batches",
        json={"student_id": str(student_id)},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _upload_photo(client, headers, batch_id: str, data: bytes) -> dict:
    resp = client.post(
        "/api/v1/photos",
        data={"batch_id": str(batch_id)},
        files={"file": ("page.jpg", data, "image/jpeg")},
        headers=headers,
    )
    return resp


def test_create_batch_family_requires_student(world):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    # 未指定学生 → 422
    r = c.post("/api/v1/upload-batches", json={}, headers=ha)
    assert r.status_code == 422
    # 他家学生 → 404（防探测）
    other = create_student(
        c, world["hb"], school_id=world["school_primary"]["school_id"], name="他家"
    )
    r = c.post("/api/v1/upload-batches", json={"student_id": other["student_id"]}, headers=ha)
    assert r.status_code == 404
    # 成功
    batch = _create_batch(c, ha, stu["student_id"])
    assert batch["student_id"] == stu["student_id"]
    assert batch["created_by_type"] == "family"


def test_student_create_batch_self_only(world):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    _open_student_account(c, ha, stu["student_id"], "xiaotu", "Passw0rd1")
    token = _login_student(c, "xiaotu", "Passw0rd1")
    hs = {"Authorization": f"Bearer {token}"}
    # 学生会话不传递 student_id，强制本人
    batch = _create_batch(c, hs, stu["student_id"])
    assert batch["created_by_type"] == "student"
    # 学生会话显式指向他人 → 404
    other = create_student(
        c, world["hb"], school_id=world["school_primary"]["school_id"], name="他家"
    )
    r = c.post(
        "/api/v1/upload-batches",
        json={"student_id": other["student_id"]},
        headers=hs,
    )
    assert r.status_code == 404


def test_upload_photo_success_and_list(world, m002_settings):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    batch = _create_batch(c, ha, stu["student_id"])
    r = _upload_photo(c, ha, batch["batch_id"], _valid_jpeg())
    assert r.status_code == 201, r.text
    photo = r.json()
    assert photo["status"] == "unassigned"
    assert photo["seq_no"] == 1
    assert photo["quality"]["passed"] is True
    assert photo["content_urls"]["normalized"].endswith("?kind=normalized")
    assert photo["content_urls"]["original"].endswith("?kind=original")

    # 列表
    lst = c.get("/api/v1/photos", headers=ha).json()
    assert lst["total"] == 1
    assert lst["items"][0]["photo_id"] == photo["photo_id"]

    # 受控取图
    url = photo["content_urls"]["normalized"]
    r = c.get(url, headers=ha)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"


def test_upload_photo_quality_rejected_no_residual(world, m002_settings):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    batch = _create_batch(c, ha, stu["student_id"])
    r = _upload_photo(c, ha, batch["batch_id"], _dark_jpeg())
    assert r.status_code == 422
    assert r.json()["code"] == "image_quality_rejected"
    # 行不存在
    assert c.get("/api/v1/photos", headers=ha).json()["total"] == 0
    # 文件无残留
    assert not any(Path(m002_settings.image_root).rglob("*"))


def test_upload_photo_wrong_batch_404(world):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    _create_batch(c, ha, stu["student_id"])
    r = _upload_photo(c, ha, "11111111-1111-1111-1111-111111111111", _valid_jpeg())
    assert r.status_code == 404


def test_upload_photo_other_family_404(world):
    c, ha, hb = world["client"], world["ha"], world["hb"]
    stu = _student_a(world)
    batch = _create_batch(c, ha, stu["student_id"])
    # B 家庭用 A 的 batch_id 上传 → 404
    r = _upload_photo(c, hb, batch["batch_id"], _valid_jpeg())
    assert r.status_code == 404


def test_photo_list_student_scope(world):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    _open_student_account(c, ha, stu["student_id"], "xiaotu2", "Passw0rd1")
    token = _login_student(c, "xiaotu2", "Passw0rd1")
    hs = {"Authorization": f"Bearer {token}"}
    batch = _create_batch(c, hs, stu["student_id"])
    r = _upload_photo(c, hs, batch["batch_id"], _valid_jpeg())
    assert r.status_code == 201

    # 学生会话列表仅本人
    lst = c.get("/api/v1/photos", headers=hs).json()
    assert lst["total"] == 1
    # family 列表也可见
    assert c.get("/api/v1/photos", headers=ha).json()["total"] == 1


def _register_math_group(m002_infra, stu_id: str, *, task_id: str | None = None):
    gs_id = str(uuid4())
    m002_infra.gateway.register_group(
        student_id=stu_id,
        group_key="2026-09-10",
        window_task_id=task_id,
        subjects=[(gs_id, "math")],
    )
    return gs_id


def test_accept_link_assigns_photo_and_marks_task_in_progress(world, m002_infra, factory):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    task_id = make_task_row(
        factory, family_id=world["family_id_a"], student_id=stu["student_id"]
    )
    m002_infra.gateway.add_task(task_id, stu["student_id"])
    _register_math_group(m002_infra, stu["student_id"], task_id=task_id)
    m002_infra.ai.suggest_enabled = True

    batch = _create_batch(c, ha, stu["student_id"])
    photo = _upload_photo(c, ha, batch["batch_id"], _valid_jpeg()).json()
    # 异步建议不阻塞上传响应；随后查询已进入建议态
    assert photo["status"] == "unassigned"
    suggestions = c.get(
        f"/api/v1/photos/{photo['photo_id']}/link-suggestions", headers=ha
    ).json()
    assert suggestions["status"] == "suggested"
    assert len(suggestions["suggestions"]) == 1
    link_id = suggestions["suggestions"][0]["link_id"]

    r = c.post(
        f"/api/v1/photos/{photo['photo_id']}/links",
        json={"action": "accept", "link_id": link_id},
        headers=ha,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "assigned"
    assert data["links"][0]["confirmed_at"] is not None
    assert data["links"][0]["subject"] == "math"
    # 窗口级归属 + 首确认触发 mark_in_progress 恰好一次
    assert data["task_id"] == task_id
    assert m002_infra.gateway.in_progress_calls == [task_id]


def test_reject_suggestion_and_delete_photo(world, m002_infra):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    _register_math_group(m002_infra, stu["student_id"])
    m002_infra.ai.suggest_enabled = True

    batch = _create_batch(c, ha, stu["student_id"])
    photo = _upload_photo(c, ha, batch["batch_id"], _valid_jpeg()).json()
    link_id = c.get(
        f"/api/v1/photos/{photo['photo_id']}/link-suggestions", headers=ha
    ).json()["suggestions"][0]["link_id"]

    r = c.post(
        f"/api/v1/photos/{photo['photo_id']}/links",
        json={"action": "reject", "link_id": link_id},
        headers=ha,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected"

    r = c.delete(f"/api/v1/photos/{photo['photo_id']}", headers=ha)
    assert r.status_code == 204
    assert c.get("/api/v1/photos", headers=ha).json()["total"] == 0


def test_accept_rejected_link_fails(world, m002_infra):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    _register_math_group(m002_infra, stu["student_id"])
    m002_infra.ai.suggest_enabled = True
    batch = _create_batch(c, ha, stu["student_id"])
    photo = _upload_photo(c, ha, batch["batch_id"], _valid_jpeg()).json()
    link_id = c.get(
        f"/api/v1/photos/{photo['photo_id']}/link-suggestions", headers=ha
    ).json()["suggestions"][0]["link_id"]

    c.post(
        f"/api/v1/photos/{photo['photo_id']}/links",
        json={"action": "reject", "link_id": link_id},
        headers=ha,
    )
    r = c.post(
        f"/api/v1/photos/{photo['photo_id']}/links",
        json={"action": "accept", "link_id": link_id},
        headers=ha,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "link_state"


def test_accept_link_to_other_student_target_404(world, m002_infra):
    c, ha = world["client"], world["ha"]
    stu_a = _student_a(world)
    stu_b = create_student(
        c, ha, school_id=world["school_primary"]["school_id"], name="小B"
    )
    other_gs = str(uuid4())
    m002_infra.gateway.register_group(
        student_id=stu_b["student_id"],
        group_key="2026-09-10",
        subjects=[(other_gs, "math")],
    )
    batch = _create_batch(c, ha, stu_a["student_id"])
    photo = _upload_photo(c, ha, batch["batch_id"], _valid_jpeg()).json()

    r = c.post(
        f"/api/v1/photos/{photo['photo_id']}/links",
        json={"action": "accept", "group_subject_id": other_gs},
        headers=ha,
    )
    assert r.status_code == 404


def test_cross_family_photo_access_404(world):
    c, ha, hb = world["client"], world["ha"], world["hb"]
    stu = _student_a(world)
    batch = _create_batch(c, ha, stu["student_id"])
    photo = _upload_photo(c, ha, batch["batch_id"], _valid_jpeg()).json()

    # B 家庭访问 A 的照片内容 → 404（不存在/越权统一 404）
    r = c.get(f"/api/v1/photos/{photo['photo_id']}/content", headers=hb)
    assert r.status_code == 404
