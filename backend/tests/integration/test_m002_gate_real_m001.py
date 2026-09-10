"""Task-010 / BUG-002 真机回归：M001↔M002 契约内聚合解析与窗口级门控。

与 `tests/api/test_m002_links_api.py` 的关键差异：本文件**不注入 FakeGateway 桩**，M002 全程走
`DefaultM001Gateway` → 真实 M001 `TaskGroupService`（内存 SQLite 内的真实聚合层）；仅注入 M002 的
Mock AI 与内联调度。测试数据经真实 M001 链路构造（`POST /tasks` 事实层 → `ensure_group` 聚合层）。

修复前（BUG-002）：`DefaultM001Gateway.get_group_subject` 消费 M001 **契约外**接口
`get_group_subject`（其 `TaskGroupSubjectDTO` 不含 group 上下文）→ `group_key` 恒为空串 →
`GET /photo-gates` 单桶聚合、`POST /completion-analyses` 门控前置恒不触发（409 不可达）。
`test_gate_multi_window_grouping_real_m001` / `test_gate_precheck_blocks_analysis_real_m001`
在修复前为**红**（修复后为绿）。
"""
from __future__ import annotations

import pytest

from app.modules.m002.clients.ai_client import MockAiClient, set_ai_client
from app.modules.m002.clients.task_client import TaskClient, set_gateway
from app.modules.m002.config import M002Settings, get_m002_settings
from app.modules.m002.services.suggestion_scheduler import set_scheduler
from tests._m001_helpers import (
    TEST_TERM_START,
    create_task_v2,
    install_fixed_window,
    task_payload,
)
from tests.conftest import create_student
from tests.m002_support import valid_jpeg

WED = "2026-09-09"  # 周三 → day 窗口
THU = "2026-09-10"  # 周四 → day 窗口
WEEKEND = "2026-09-11"  # 周五 → weekend 窗口（group_key = W:2026-09-11）


@pytest.fixture
def real_m001(client, tmp_path):
    """真实 M001 网关（不注入桩）+ Mock AI + 内联调度 + 图片根重定向。"""
    set_gateway(None)  # 确保走 DefaultM001Gateway（真实 M001 聚合层）
    ai = MockAiClient()
    set_ai_client(ai)
    set_scheduler(lambda runner: runner())
    settings = M002Settings(image_store_root=str(tmp_path / "images"))
    client.app.dependency_overrides[get_m002_settings] = lambda: settings
    yield ai
    client.app.dependency_overrides.pop(get_m002_settings, None)
    set_gateway(None)
    set_ai_client(None)
    set_scheduler(None)


def _student(world) -> dict:
    return create_student(
        world["client"],
        world["ha"],
        school_id=world["school_primary"]["school_id"],
        name="真机学生",
    )


def _make_window(world, factory, *, student_id, belong_date):
    """经真实 M001 链路造一个聚合窗口：事实层任务（`POST /tasks`）→ 聚合 → 学科子任务。"""
    c = world["client"]
    install_fixed_window(c, belong_date, term_start=TEST_TERM_START)
    create_task_v2(c, world["ha"], task_payload(student_id))
    with factory() as session:
        ref = TaskClient.ensure_group(
            session,
            world["family_id_a"],
            student_id=student_id,
            category="school",
            belong_date=belong_date,
        )
        session.commit()
    assert ref.group_key, "聚合 group_key 不得为空"
    assert ref.subjects, "聚合应含至少一个学科子任务"
    return ref


def _create_batch(client, headers, student_id) -> dict:
    r = client.post(
        "/api/v1/upload-batches",
        json={"student_id": student_id, "kind": "homework"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _upload(client, headers, batch_id) -> dict:
    r = client.post(
        "/api/v1/photos",
        files={"file": ("hw.jpg", valid_jpeg(), "image/jpeg")},
        data={"batch_id": batch_id},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _accept(client, headers, photo_id, *, group_subject_id=None, link_id=None):
    body: dict = {"action": "accept"}
    if group_subject_id:
        body["group_subject_id"] = str(group_subject_id)
    if link_id:
        body["link_id"] = str(link_id)
    return client.post(f"/api/v1/photos/{photo_id}/links", json=body, headers=headers)


def _gates(client, headers, student_id, **params):
    query = "&".join(f"{k}={v}" for k, v in {"student_id": student_id, **params}.items())
    r = client.get(f"/api/v1/photo-gates?{query}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _generate(client, headers, student_id, group_key):
    return client.post(
        "/api/v1/completion-analyses",
        json={"student_id": student_id, "group_key": group_key},
        headers=headers,
    )


# ---------------------------------------------------------------- ① 多窗口分组
def test_gate_multi_window_grouping_real_m001(world, factory, real_m001):
    """① 门控按真实 group_key 分桶：≥2 窗口、group_key 非空且等于 task_groups.group_key。"""
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    win_day = _make_window(world, factory, student_id=stu["student_id"], belong_date=WED)
    win_weekend = _make_window(world, factory, student_id=stu["student_id"], belong_date=WEEKEND)
    assert win_day.group_key == WED and win_day.window_type == "day"
    assert win_weekend.group_key == f"W:{WEEKEND}" and win_weekend.window_type == "weekend"

    batch = _create_batch(c, ha, stu["student_id"])
    p1 = _upload(c, ha, batch["batch_id"])
    p2 = _upload(c, ha, batch["batch_id"])

    # API-M002-005 响应 gate：真实 group_key（不再是空串）
    r1 = _accept(c, ha, p1["photo_id"], group_subject_id=win_day.subjects[0].group_subject_id)
    assert r1.status_code == 200, r1.text
    gate1 = r1.json()["gate"]
    assert gate1 is not None, "M002-005 响应应回带窗口门控"
    assert gate1["group_key"] == win_day.group_key
    assert gate1["total_photos"] == 1 and gate1["pending_photos"] == 0
    assert gate1["satisfied"] is True

    r2 = _accept(c, ha, p2["photo_id"], group_subject_id=win_weekend.subjects[0].group_subject_id)
    assert r2.status_code == 200, r2.text

    gates = _gates(c, ha, stu["student_id"])
    by_key = {g["group_key"]: g for g in gates}
    assert set(by_key) == {win_day.group_key, win_weekend.group_key}, gates
    assert by_key[win_day.group_key]["window_type"] == "day"
    assert by_key[win_weekend.group_key]["window_type"] == "weekend"
    for g in gates:
        assert g["group_key"], "group_key 不得为空串（BUG-002）"
        assert g["total_photos"] == 1 and g["pending_photos"] == 0 and g["satisfied"] is True

    # group_key 与契约内 list_groups 回读一致（真实 task_groups.group_key）
    with factory() as session:
        refs = TaskClient.list_groups(session, world["family_id_a"], student_id=stu["student_id"])
        assert {r.group_key for r in refs} == {win_day.group_key, win_weekend.group_key}

    # ?group_key= 精确命中单桶
    only = _gates(c, ha, stu["student_id"], group_key=win_day.group_key)
    assert len(only) == 1
    assert only[0]["group_key"] == win_day.group_key and only[0]["total_photos"] == 1


# ---------------------------------------------------------------- ② 门控前置生效
def test_gate_precheck_blocks_analysis_real_m001(world, factory, real_m001):
    """② 存在未确认挂接 → 409 gate_not_satisfied（修复前恒 201，门控前置失效）。"""
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    win = _make_window(world, factory, student_id=stu["student_id"], belong_date=WED)
    gs = win.subjects[0].group_subject_id

    real_m001.suggest_enabled = True  # AI 出建议（未确认态）
    batch = _create_batch(c, ha, stu["student_id"])
    p1 = _upload(c, ha, batch["batch_id"])
    p2 = _upload(c, ha, batch["batch_id"])

    assert _accept(c, ha, p1["photo_id"], group_subject_id=gs).status_code == 200
    sug = c.get(
        f"/api/v1/photos/{p2['photo_id']}/link-suggestions?retry=true", headers=ha
    ).json()
    assert [s["group_subject_id"] for s in sug["suggestions"]] == [str(gs)]
    assert sug["status"] == "suggested"

    gates = _gates(c, ha, stu["student_id"])
    assert len(gates) == 1
    assert gates[0]["group_key"] == win.group_key
    assert gates[0]["total_photos"] == 2 and gates[0]["pending_photos"] == 1
    assert gates[0]["satisfied"] is False

    r = _generate(c, ha, stu["student_id"], win.group_key)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "gate_not_satisfied"
    assert "待复核 1 张" in r.json()["message"]


# ---------------------------------------------------------------- ③ 全部确认放行
def test_gate_satisfied_after_all_confirmed_real_m001(world, factory, real_m001):
    """③ 全部确认 → 门控满足 → 201 draft（真实 subject / 依据照片）。"""
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    win = _make_window(world, factory, student_id=stu["student_id"], belong_date=WED)
    gs = win.subjects[0].group_subject_id
    subject = win.subjects[0].subject

    real_m001.suggest_enabled = True
    batch = _create_batch(c, ha, stu["student_id"])
    p1 = _upload(c, ha, batch["batch_id"])
    p2 = _upload(c, ha, batch["batch_id"])

    assert _accept(c, ha, p1["photo_id"], group_subject_id=gs).status_code == 200
    sug = c.get(
        f"/api/v1/photos/{p2['photo_id']}/link-suggestions?retry=true", headers=ha
    ).json()
    link_id = sug["suggestions"][0]["link_id"]
    assert _accept(c, ha, p2["photo_id"], link_id=link_id).status_code == 200

    gates = _gates(c, ha, stu["student_id"])
    assert len(gates) == 1 and gates[0]["satisfied"] is True and gates[0]["pending_photos"] == 0

    r = _generate(c, ha, stu["student_id"], win.group_key)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["group_key"] == win.group_key
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["status"] == "draft"
    assert item["group_subject_id"] == str(gs)
    assert item["subject"] == subject
    assert item["conclusion"] == "完成"
    assert set(item["evidence_photo_ids"]) == {p1["photo_id"], p2["photo_id"]}


# ---------------------------------------------------------------- ④ 空窗口语义
def test_empty_window_stays_satisfied_real_m001(world, factory, real_m001):
    """④ 无挂接照片的窗口：门控语义 = satisfied(total=0)，不阻断生成（契约语义保持）。"""
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    win = _make_window(world, factory, student_id=stu["student_id"], belong_date=THU)

    assert _gates(c, ha, stu["student_id"]) == []  # 无有效挂接 → 无桶
    r = _generate(c, ha, stu["student_id"], win.group_key)
    assert r.status_code == 201, r.text
    assert r.json()["group_key"] == win.group_key
