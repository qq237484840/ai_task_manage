"""集成级：`BUG-009` 端点面 —— DATA-009 写入失败时 `API-M002-007` **不得** 500。

构造思路：使 `record_call`（DATA-009 写入）**必然失败**（**真实删表**，`_ensure_table` 因 bind 已
在 `_ENSURED_BINDS` 而不再建表），再调用 `GET /photos/{id}/link-suggestions?retry=true`：

- 修复后：写入失败 → `session.rollback()` → 主链路继续（AI 建议照常落库）→ **`200`**；
- 修复前（`BUG-009`）：flush 失败不回滚 → Session 进「待回滚」→ 路由 `db.commit()`
  抛 `PendingRollbackError` → **`500`**。

**桩 / 替身说明（PM 铁律 ①）**：仅 `FakeGateway` 充当 **M001 聚合层**契约桩（提供学科子任务候选，
避免依赖 M001 内部数据构造）；**AI 通路为真实** —— `DefaultAiClient` → `app/core/ai` → Mock Provider
→ 真实 `record_call` 写入 DATA-009（本用例的被测对象正是这条写入）。
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.ai.records import dropped_record_count, list_calls_by_request_id
from app.modules.m002.clients.task_client import set_gateway
from app.modules.m002.config import M002Settings, get_m002_settings
from app.modules.m002.services.suggestion_scheduler import set_scheduler
from tests.conftest import create_student
from tests.m002_support import FakeGateway, valid_jpeg

GROUP_KEY = "2026-09-29"


def _settings(tmp_path, **overrides) -> M002Settings:
    return M002Settings(image_store_root=str(tmp_path / "images"), **overrides)


def _override(client, tmp_path, **overrides) -> None:
    client.app.dependency_overrides[get_m002_settings] = lambda: _settings(
        tmp_path, **overrides
    )


@pytest.fixture
def scenario(client, world, tmp_path):
    """真实 AI 通路 + M001 聚合层桩；上传阶段**关闭**建议（保证 `retry` 时才触发 AI）。"""
    from app.core.ai.config import get_ai_settings
    from app.core.ai.service import get_ai_service

    get_ai_settings.cache_clear()
    get_ai_service.cache_clear()
    _override(client, tmp_path, association_suggestion_enabled=False)

    gateway = FakeGateway()
    set_gateway(gateway)
    set_scheduler(lambda runner: runner())

    student = create_student(
        client, world["ha"], school_id=world["school_primary"]["school_id"], name="小锁"
    )
    group = gateway.register_group(
        student_id=student["student_id"],
        group_key=GROUP_KEY,
        subjects=[(str(uuid4()), "math")],
    )
    yield {"client": client, "world": world, "student": student, "group": group}

    client.app.dependency_overrides.pop(get_m002_settings, None)
    set_gateway(None)
    set_scheduler(None)
    get_ai_settings.cache_clear()
    get_ai_service.cache_clear()


def _upload(client, headers, student_id: str) -> dict:
    batch = client.post(
        "/api/v1/upload-batches",
        json={"student_id": student_id, "kind": "homework"},
        headers=headers,
    )
    assert batch.status_code == 201, batch.text
    resp = client.post(
        "/api/v1/photos",
        data={"batch_id": batch.json()["batch_id"]},
        files={"file": ("page.jpg", valid_jpeg(), "image/jpeg")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_link_suggestions_returns_200_when_data009_write_fails(scenario, factory, tmp_path):
    """DATA-009 写入失败 → 端点仍 `200`，业务结果（AI 建议）照常落库（`BUG-009` 根治）。"""
    client = scenario["client"]
    ha = scenario["world"]["ha"]
    student_id = scenario["student"]["student_id"]

    photo = _upload(client, ha, student_id)
    assert not client.get(f"/api/v1/photos/{photo['photo_id']}/link-suggestions", headers=ha).json()[
        "suggestions"
    ], "上传阶段已关闭建议（前置：retry 前无有效挂接）"

    # ① 使 bind 进入 `_ENSURED_BINDS`（建表）→ ② 真实删表 → 后续写入必然失败
    with factory() as session:
        list_calls_by_request_id(session, "prime")
    with factory() as session:
        session.execute(text("DROP TABLE ai_call_records"))
        session.commit()

    _override(client, tmp_path)  # 恢复建议开关（retry 时才触发真实 AI 通路）
    before = dropped_record_count()

    resp = client.get(
        f"/api/v1/photos/{photo['photo_id']}/link-suggestions?retry=true", headers=ha
    )

    assert resp.status_code == 200, f"BUG-009：不得 500 —— {resp.text}"
    body = resp.json()
    # 留痕丢失必须**可观测**（BUG-008）而非静默
    assert dropped_record_count() == before + 1, "写入失败必须计入 dropped_record_count()"
    # 留痕读取失败 → 降级 `null`；业务结果不受影响（回滚未吞掉 AI 建议）
    assert body["last_attempt"] is None, body
    assert body["suggestions"], f"业务结果应照常落库（回滚不得吞掉 AI 建议）：{body}"
    assert body["status"] == "suggested", body
