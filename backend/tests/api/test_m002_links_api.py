"""M002 v0.4.0 挂接/门控/完成分析 REST 集成测试（API-M002-005/007~011）。

覆盖：N:N 挂接、手工兜底、改挂、上限/状态门控、异步建议幂等、窗口门控、
分析 draft→确认→重跑、AI 降级兜底、migrate_links 迁移、入口 kind。
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.modules.m002.clients.task_client import migrate_photo_links
from app.modules.m002.config import M002Settings, get_m002_settings
from tests.conftest import create_student
from tests.m002_support import make_task_row, m002_infra, valid_jpeg  # noqa: F401


@pytest.fixture(autouse=True)
def m002_settings(tmp_path, client):
    s = M002Settings(image_store_root=str(tmp_path / "images"))
    client.app.dependency_overrides[get_m002_settings] = lambda: s
    yield s
    client.app.dependency_overrides.pop(get_m002_settings, None)


def _student_a(world):
    return create_student(
        world["client"], world["ha"], school_id=world["school_primary"]["school_id"], name="小图"
    )


def _create_batch(client, headers, student_id, kind="homework"):
    r = client.post(
        "/api/v1/upload-batches",
        json={"student_id": student_id, "kind": kind},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _upload(client, headers, batch_id):
    r = client.post(
        "/api/v1/photos",
        files={"file": ("hw.jpg", valid_jpeg(), "image/jpeg")},
        data={"batch_id": batch_id},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _register_group(m002_infra, stu_id, *, subjects, group_key="2026-09-10", task_status="published", window_task_id=None):
    return m002_infra.gateway.register_group(
        student_id=stu_id,
        group_key=group_key,
        window_task_id=window_task_id,
        task_status=task_status,
        subjects=subjects,
    )


# ---------------------------------------------------------------- 挂接
def test_manual_accept_without_ai_suggestion(world, m002_infra):
    """手工兜底：AI 未建议也可直接挂接（不得移除人工路径）。"""
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    gs = str(uuid4())
    _register_group(m002_infra, stu["student_id"], subjects=[(gs, "math")])
    batch = _create_batch(c, ha, stu["student_id"])
    photo = _upload(c, ha, batch["batch_id"])

    r = c.post(
        f"/api/v1/photos/{photo['photo_id']}/links",
        json={"action": "accept", "group_subject_id": gs},
        headers=ha,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "assigned"
    assert r.json()["links"][0]["source"] == "manual"
    assert r.json()["links"][0]["confirmed_at"] is not None


def test_relink_moves_confirmed_link(world, m002_infra):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    gs_math, gs_cn = str(uuid4()), str(uuid4())
    _register_group(m002_infra, stu["student_id"], subjects=[(gs_math, "math"), (gs_cn, "chinese")])
    batch = _create_batch(c, ha, stu["student_id"])
    photo = _upload(c, ha, batch["batch_id"])

    accept = c.post(
        f"/api/v1/photos/{photo['photo_id']}/links",
        json={"action": "accept", "group_subject_id": gs_math},
        headers=ha,
    ).json()
    link_id = accept["links"][0]["link_id"]

    r = c.post(
        f"/api/v1/photos/{photo['photo_id']}/links",
        json={"action": "relink", "link_id": link_id, "group_subject_id": gs_cn},
        headers=ha,
    )
    assert r.status_code == 200, r.text
    by_subject = {link["group_subject_id"]: link for link in r.json()["links"]}
    assert by_subject[gs_math]["rejected_at"] is not None
    assert by_subject[gs_cn]["confirmed_at"] is not None
    assert r.json()["status"] == "assigned"


def test_subject_photo_limit_conflict(world, m002_infra, client, tmp_path):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    gs = str(uuid4())
    _register_group(m002_infra, stu["student_id"], subjects=[(gs, "math")])
    client.app.dependency_overrides[get_m002_settings] = lambda: M002Settings(
        image_store_root=str(tmp_path / "images"), association_max_photos_per_subject=1
    )
    batch = _create_batch(c, ha, stu["student_id"])
    p1 = _upload(c, ha, batch["batch_id"])
    p2 = _upload(c, ha, batch["batch_id"])

    assert c.post(
        f"/api/v1/photos/{p1['photo_id']}/links",
        json={"action": "accept", "group_subject_id": gs},
        headers=ha,
    ).status_code == 200
    r = c.post(
        f"/api/v1/photos/{p2['photo_id']}/links",
        json={"action": "accept", "group_subject_id": gs},
        headers=ha,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "subject_photo_limit"


def test_accept_to_closed_window_task_conflict(world, m002_infra):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    gs = str(uuid4())
    _register_group(m002_infra, stu["student_id"], subjects=[(gs, "math")], task_status="closed")
    batch = _create_batch(c, ha, stu["student_id"])
    photo = _upload(c, ha, batch["batch_id"])
    r = c.post(
        f"/api/v1/photos/{photo['photo_id']}/links",
        json={"action": "accept", "group_subject_id": gs},
        headers=ha,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "task_not_acceptable"


# ---------------------------------------------------------------- 建议 / 门控
def test_suggestion_idempotent_and_retry(world, m002_infra):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    gs = str(uuid4())
    _register_group(m002_infra, stu["student_id"], subjects=[(gs, "math")])
    batch = _create_batch(c, ha, stu["student_id"])
    photo = _upload(c, ha, batch["batch_id"])  # AI 未开启 → 无建议
    assert c.get(
        f"/api/v1/photos/{photo['photo_id']}/link-suggestions", headers=ha
    ).json()["suggestions"] == []

    m002_infra.ai.suggest_enabled = True
    out = c.get(
        f"/api/v1/photos/{photo['photo_id']}/link-suggestions?retry=true", headers=ha
    ).json()
    assert len(out["suggestions"]) == 1
    # 再次 retry 幂等：不重复建链
    out2 = c.get(
        f"/api/v1/photos/{photo['photo_id']}/link-suggestions?retry=true", headers=ha
    ).json()
    assert len(out2["suggestions"]) == 1


def test_photo_gate_blocks_until_all_confirmed(world, m002_infra):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    gs = str(uuid4())
    _register_group(m002_infra, stu["student_id"], subjects=[(gs, "math")])
    m002_infra.ai.suggest_enabled = True
    batch = _create_batch(c, ha, stu["student_id"])
    p1 = _upload(c, ha, batch["batch_id"])
    p2 = _upload(c, ha, batch["batch_id"])

    gates = c.get(f"/api/v1/photo-gates?student_id={stu['student_id']}", headers=ha).json()
    assert gates[0]["total_photos"] == 2
    assert gates[0]["pending_photos"] == 2
    assert gates[0]["satisfied"] is False

    for p in (p1, p2):
        link_id = c.get(
            f"/api/v1/photos/{p['photo_id']}/link-suggestions", headers=ha
        ).json()["suggestions"][0]["link_id"]
        c.post(
            f"/api/v1/photos/{p['photo_id']}/links",
            json={"action": "accept", "link_id": link_id},
            headers=ha,
        )
    gates = c.get(f"/api/v1/photo-gates?student_id={stu['student_id']}", headers=ha).json()
    assert gates[0]["satisfied"] is True
    assert gates[0]["pending_photos"] == 0


# ---------------------------------------------------------------- 完成分析
def test_generate_analysis_gate_blocks_with_pending(world, m002_infra):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    gs = str(uuid4())
    _register_group(m002_infra, stu["student_id"], subjects=[(gs, "math")])
    m002_infra.ai.suggest_enabled = True
    batch = _create_batch(c, ha, stu["student_id"])
    _upload(c, ha, batch["batch_id"])  # 建议未确认 → 待复核 1 张

    r = c.post(
        "/api/v1/completion-analyses",
        json={"student_id": stu["student_id"], "group_key": "2026-09-10"},
        headers=ha,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "gate_not_satisfied"
    assert "待复核 1 张" in r.json()["message"]


def test_analysis_draft_confirm_consumes_and_rerun(world, m002_infra):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    gs = str(uuid4())
    _register_group(m002_infra, stu["student_id"], subjects=[(gs, "math")])
    m002_infra.ai.suggest_enabled = True
    batch = _create_batch(c, ha, stu["student_id"])
    photo = _upload(c, ha, batch["batch_id"])
    link_id = c.get(
        f"/api/v1/photos/{photo['photo_id']}/link-suggestions", headers=ha
    ).json()["suggestions"][0]["link_id"]
    c.post(
        f"/api/v1/photos/{photo['photo_id']}/links",
        json={"action": "accept", "link_id": link_id},
        headers=ha,
    )

    gen = c.post(
        "/api/v1/completion-analyses",
        json={"student_id": stu["student_id"], "group_key": "2026-09-10"},
        headers=ha,
    )
    assert gen.status_code == 201, gen.text
    item = gen.json()["items"][0]
    assert item["status"] == "draft"
    assert item["conclusion"] == "完成"
    assert item["subject"] == "math"
    assert item["evidence_photo_ids"] == [photo["photo_id"]]
    analysis_id = item["analysis_id"]

    # 确认 → 回写 M001 + 消费锁定
    r = c.post(
        f"/api/v1/completion-analyses/{analysis_id}/confirmation", json={}, headers=ha
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "confirmed"
    assert m002_infra.gateway.conclusions[0]["status"] == "confirmed"
    assert m002_infra.gateway.conclusions[0]["conclusion"] == "完成"
    # 已消费：删除被拒
    assert c.delete(f"/api/v1/photos/{photo['photo_id']}", headers=ha).status_code == 409
    # 已确认：重跑被拒
    rr = c.post(f"/api/v1/completion-analyses/{analysis_id}/rerun", headers=ha)
    assert rr.status_code == 409
    assert rr.json()["code"] == "analysis_state"


def test_rerun_increments_run_no(world, m002_infra):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    gs = str(uuid4())
    _register_group(m002_infra, stu["student_id"], subjects=[(gs, "math")])
    batch = _create_batch(c, ha, stu["student_id"])
    photo = _upload(c, ha, batch["batch_id"])
    c.post(
        f"/api/v1/photos/{photo['photo_id']}/links",
        json={"action": "accept", "group_subject_id": gs},
        headers=ha,
    )
    gen = c.post(
        "/api/v1/completion-analyses",
        json={"student_id": stu["student_id"], "group_key": "2026-09-10"},
        headers=ha,
    ).json()
    assert gen["items"][0]["run_no"] == 1
    rr = c.post(
        f"/api/v1/completion-analyses/{gen['items'][0]['analysis_id']}/rerun", headers=ha
    )
    assert rr.status_code == 201, rr.text
    assert rr.json()["run_no"] == 2


# ---------------------------------------------------------------- AI 降级兜底
def test_ai_suggest_failure_keeps_unassigned(world, m002_infra):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    gs = str(uuid4())
    _register_group(m002_infra, stu["student_id"], subjects=[(gs, "math")])
    m002_infra.ai.fail_suggest = True
    batch = _create_batch(c, ha, stu["student_id"])
    photo = _upload(c, ha, batch["batch_id"])
    out = c.get(f"/api/v1/photos/{photo['photo_id']}/link-suggestions", headers=ha).json()
    assert out["status"] == "unassigned"
    assert out["suggestions"] == []


def test_ai_analysis_failure_falls_back_to_unknown(world, m002_infra):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    gs = str(uuid4())
    _register_group(m002_infra, stu["student_id"], subjects=[(gs, "math")])
    batch = _create_batch(c, ha, stu["student_id"])
    photo = _upload(c, ha, batch["batch_id"])
    c.post(
        f"/api/v1/photos/{photo['photo_id']}/links",
        json={"action": "accept", "group_subject_id": gs},
        headers=ha,
    )
    m002_infra.ai.fail_analysis = True
    gen = c.post(
        "/api/v1/completion-analyses",
        json={"student_id": stu["student_id"], "group_key": "2026-09-10"},
        headers=ha,
    )
    assert gen.status_code == 201
    assert gen.json()["items"][0]["conclusion"] == "无法判断"


# ---------------------------------------------------------------- migrate_links
def test_migrate_links_moves_confirmed_link_to_new_window(world, m002_infra, factory):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    old_gs, new_gs = str(uuid4()), str(uuid4())
    _register_group(m002_infra, stu["student_id"], subjects=[(old_gs, "math")], group_key="2026-09-10")
    _register_group(m002_infra, stu["student_id"], subjects=[(new_gs, "math")], group_key="2026-09-11")
    task_id = make_task_row(
        factory, family_id=world["family_id_a"], student_id=stu["student_id"]
    )
    m002_infra.gateway.add_task(task_id, stu["student_id"])
    batch = _create_batch(c, ha, stu["student_id"])
    photo = _upload(c, ha, batch["batch_id"])
    c.post(
        f"/api/v1/photos/{photo['photo_id']}/links",
        json={"action": "accept", "group_subject_id": old_gs},
        headers=ha,
    )

    with factory() as session:
        migrate_photo_links(
            session, world["family_id_a"], task_id, "2026-09-10", "2026-09-11"
        )
        session.commit()

    assert c.get(
        f"/api/v1/photos?group_subject_id={new_gs}", headers=ha
    ).json()["total"] == 1
    assert c.get(
        f"/api/v1/photos?group_subject_id={old_gs}", headers=ha
    ).json()["total"] == 0


# ---------------------------------------------------------------- 入口 kind
def test_entry_kind_roundtrip_and_filter(world, m002_infra):
    c, ha = world["client"], world["ha"]
    stu = _student_a(world)
    batch = _create_batch(c, ha, stu["student_id"], kind="task_spec")
    assert batch["kind"] == "task_spec"
    photo = _upload(c, ha, batch["batch_id"])
    assert photo["kind"] == "task_spec"
    assert c.get("/api/v1/photos?kind=task_spec", headers=ha).json()["total"] == 1
    assert c.get("/api/v1/photos?kind=homework", headers=ha).json()["total"] == 0


# ---------------------------------------------------------------- 迁移回调注册契约
def test_links_migration_hook_registered_on_import():
    """导入期注册 = 唯一来源：M001 槽位必须指向 M002 的 migrate_photo_links。

    M001 侧已删除反向 import 兜底（分层违规），本断言固化「导入即注册」这一契约。
    """
    from app.modules.m001.services import aggregation_service as ag
    from app.modules.m002.clients import task_client as tc

    assert ag._links_migration_hook is tc.migrate_photo_links


def test_ensure_links_migration_hook_registered_idempotent():
    """幂等 + 自愈：连续调用恒 True；槽位被清空后再次调用可自愈；用完恢复现场。"""
    from app.modules.m001.services import aggregation_service as ag
    from app.modules.m002.clients.task_client import ensure_links_migration_hook_registered

    original = ag._links_migration_hook
    try:
        # 连续两次调用：均 True，槽位保持
        assert ensure_links_migration_hook_registered() is True
        assert ensure_links_migration_hook_registered() is True
        assert ag._links_migration_hook is migrate_photo_links

        # 模拟首次导入时 M001 未就绪导致槽位为空 → 启动期调用应自愈
        ag.register_links_migration_hook(None)
        assert ag._links_migration_hook is None
        assert ensure_links_migration_hook_registered() is True
        assert ag._links_migration_hook is migrate_photo_links
    finally:
        ag.register_links_migration_hook(original)  # 恢复现场，避免污染其他用例
