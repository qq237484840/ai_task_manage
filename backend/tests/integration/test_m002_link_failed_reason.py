"""集成级（真实装配）：`CR-006` 子项 B —— `API-M002-007` 暴露 AI 失败原因（`last_attempt`）。

覆盖（`Task-024 §4` 清单）：

1. **成功 → `null`**：真实 `app/core/ai`（Mock 兜底）产出建议并留痕 `status=ok`
   → `last_attempt` 为 `None`（**成功记录不得暴露**）；
2. **失败分支（核心）**：`real` + 禁 Mock 兜底（无三方凭据）→ 真实 Provider 判为不可用
   → DATA-009 落 `status=error` → `last_attempt` 暴露 `code` / `message`（**红→绿判别力用例**）；
3. **脱敏 + 截断**：DATA-009 的既有安全约束（`BUG-005` / `Task-015`）在**对外响应**上成立
   （`sk-` 已剔除、三方摘要 ≤200 字）；
4. **无记录 → `null` + 向后兼容**：响应键集 = 基线 + 新增 1 字段；既有消费者无视新字段仍 OK。

**桩 / 替身说明（PM 铁律 ①）**：本文件**不注入任何 AI 替身** —— 用例 1/2 走真实
`DefaultAiClient` → 真实 `app/core/ai` → 真实 DATA-009 写入；用例 3 以 DATA-009 的**生产写入 API**
（`record_call` + `from_http_status`，与生产链路同源）落一条历史留痕，用于验证「对外暴露面」的
安全约束（非替身）。

**检索键（本子项关键实现点）**：`input_ref.photo_id` —— `input_ref` 为 JSON `TEXT` 且**无独立列**，
故用 SQLite JSON1 `json_extract` 检索（写入侧见 `app/core/ai/service.py::suggest_photo_links`）。
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import func

from app.core.ai.errors import from_http_status
from app.core.ai.records import AICallRecord, record_call
from app.core.ai.service import CAPABILITY_PHOTO_LINK_SUGGEST
from app.modules.m002.config import M002Settings, get_m002_settings
from app.modules.m002.services.suggestion_scheduler import set_scheduler
from tests._m001_helpers import (
    DAY,
    TEST_TERM_START,
    create_task_v2,
    install_fixed_window,
    task_payload,
    text_source,
)
from tests.conftest import create_student
from tests.m002_support import valid_jpeg

BASELINE_KEYS = {"photo_id", "status", "suggestions"}  # v0.4.2 基线键集（CR-004）


# --------------------------------------------------------------------------- fixtures / helpers
def _settings(tmp_path, **overrides) -> M002Settings:
    return M002Settings(image_store_root=str(tmp_path / "images"), **overrides)


def _override_settings(client, tmp_path, **overrides) -> M002Settings:
    s = _settings(tmp_path, **overrides)
    client.app.dependency_overrides[get_m002_settings] = lambda: s
    return s


@pytest.fixture
def ai_stack(client, tmp_path):
    """真实栈：真实 `app/core/ai`（**无替身**）+ 内联建议调度 + 临时图片根。

    与 `tests/e2e/test_acceptance_scenarios.py::real_stack` 同构（pytest fixture 不跨模块共享）。
    """
    from app.core.ai.config import get_ai_settings
    from app.core.ai.service import get_ai_service

    get_ai_settings.cache_clear()
    get_ai_service.cache_clear()
    set_scheduler(lambda runner: runner())
    _override_settings(client, tmp_path)
    yield
    client.app.dependency_overrides.pop(get_m002_settings, None)
    set_scheduler(None)
    get_ai_settings.cache_clear()
    get_ai_service.cache_clear()


def _set_real_no_fallback(monkeypatch) -> None:
    """切到 `real` + 禁 Mock 兜底（无凭据 → Provider 判为**不可用**，`BUG-006` 语义）。"""
    from app.core.ai.config import get_ai_settings
    from app.core.ai.service import get_ai_service

    monkeypatch.setenv("AT_AI_PROVIDER_MODE", "real")
    monkeypatch.setenv("AT_AI_ALLOW_MOCK_FALLBACK", "false")
    get_ai_settings.cache_clear()
    get_ai_service.cache_clear()


def _student(world, name: str) -> dict:
    return create_student(
        world["client"], world["ha"], school_id=world["school_primary"]["school_id"], name=name
    )


def _seed_window_day(world, *, student_id: str) -> str:
    """造一个 day 窗口（真机 M001 链路）并返回其学科子任务 id（`real` 模式前必须完成）。"""
    install_fixed_window(world["client"], DAY, term_start=TEST_TERM_START)
    create_task_v2(
        world["client"],
        world["ha"],
        task_payload(student_id, sources=[text_source("数学：练习册 P23 第 1-10 题")]),
    )
    r = world["client"].get(f"/api/v1/task-groups?student_id={student_id}", headers=world["ha"])
    assert r.status_code == 200, r.text
    groups = r.json()["items"] if isinstance(r.json(), dict) else r.json()
    target = [g for g in groups if g["group_key"] == DAY]
    assert len(target) == 1, groups
    return target[0]["subjects"][0]["group_subject_id"]


def _upload(world, student_id: str) -> dict:
    c, ha = world["client"], world["ha"]
    batch = c.post(
        "/api/v1/upload-batches",
        json={"student_id": student_id, "kind": "homework"},
        headers=ha,
    )
    assert batch.status_code == 201, batch.text
    resp = c.post(
        "/api/v1/photos",
        data={"batch_id": batch.json()["batch_id"]},
        files={"file": ("page.jpg", valid_jpeg(), "image/jpeg")},
        headers=ha,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _suggestions(world, photo_id: str, *, retry: bool = False) -> dict:
    suffix = "?retry=true" if retry else ""
    resp = world["client"].get(
        f"/api/v1/photos/{photo_id}/link-suggestions{suffix}", headers=world["ha"]
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _records(factory, photo_id: str) -> list[AICallRecord]:
    """数据面复核：按 `input_ref.photo_id` 实读 DATA-009（**不采信响应自述**）。"""
    with factory() as session:
        return (
            session.query(AICallRecord)
            .filter(
                func.json_extract(AICallRecord.input_ref, "$.photo_id") == str(photo_id),
                AICallRecord.capability == CAPABILITY_PHOTO_LINK_SUGGEST,
            )
            .all()
        )


# ---------------------------------------------------------------- 1) 成功 → null
def test_last_attempt_is_null_when_latest_attempt_succeeds(world, factory, ai_stack):
    """真实 AI 通路**成功**（Mock 兜底，`status=ok`）→ `last_attempt` 必须为 `null`。

    先断言数据面确有该照片的**成功**留痕（否则「null」无法区分「成功」与「没读到」）。
    """
    stu = _student(world, "小S")
    _seed_window_day(world, student_id=stu["student_id"])

    photo = _upload(world, stu["student_id"])
    body = _suggestions(world, photo["photo_id"], retry=True)

    rows = _records(factory, photo["photo_id"])
    assert rows, "真实 AI 通路应产生 DATA-009 留痕"
    assert {r.status for r in rows} == {"ok"}, [(r.status, r.error) for r in rows]

    assert body["last_attempt"] is None, body
    assert len(body["suggestions"]) >= 1, body


# ---------------------------------------------------------------- 2) 失败分支（红→绿判别力）
def test_last_attempt_exposes_failure_from_data009(world, factory, ai_stack, monkeypatch):
    """`real` + 禁兜底（无凭据）→ AI 不可用 → `last_attempt` 暴露真实失败原因。

    **红→绿判别力**：修复前实现以不存在的 `photo.upload_request_id` 检索（并被宽 `except` 吞掉）
    → 本用例必败（`last_attempt` 恒 `null`）。
    """
    stu = _student(world, "小F")
    _seed_window_day(world, student_id=stu["student_id"])
    _set_real_no_fallback(monkeypatch)

    photo = _upload(world, stu["student_id"])
    body = _suggestions(world, photo["photo_id"], retry=True)

    # 主流程不受影响（既有降级语义不变）
    assert body["suggestions"] == [], body
    assert body["status"] == "unassigned", body

    # 新增字段：暴露真实失败原因
    last_attempt = body["last_attempt"]
    assert last_attempt is not None, body
    assert last_attempt["code"] == "provider_unavailable", last_attempt
    assert last_attempt["message"], last_attempt

    # 数据面复核：响应内容 = DATA-009 实读内容（同一来源，不额外加工）
    rows = _records(factory, photo["photo_id"])
    assert rows and all(r.status == "error" for r in rows), rows
    stored = json.loads(rows[-1].error or "{}")
    assert last_attempt["code"] == stored["code"]
    assert last_attempt["message"] == stored["message"]


# ---------------------------------------------------------------- 3) 脱敏 + 截断
def test_last_attempt_message_is_redacted_and_bounded(world, factory, client, tmp_path):
    """对外暴露的 `message` 继承 `BUG-005` / `Task-015` 的**脱敏 + 截断**约束。

    本用例**关闭「上传即建议」**（避免同照片产生其它留痕），再以 DATA-009 的**生产写入 API**
    落一条含密钥特征串 + 超长正文的失败留痕 → 断言响应面不泄密、三方摘要 ≤200 字。

    `quota_exhausted` 同时验证 `BUG-005` 的配额线索映射仍是**下游可见**的（本子项的下游消费）。
    """
    from app.core.ai.config import get_ai_settings
    from app.core.ai.service import get_ai_service

    get_ai_settings.cache_clear()
    get_ai_service.cache_clear()
    _override_settings(client, tmp_path, association_suggestion_enabled=False)

    stu = _student(world, "小R")
    photo = _upload(world, stu["student_id"])

    secret = "sk-liveSECRET0123456789"
    body_403 = json.dumps(
        {"error": {"code": "insufficient_quota", "message": f"{secret} 账户余额不足，请充值" + "超长正文" * 60}}
    )
    err = from_http_status(403, body_403)
    assert err.code.value == "quota_exhausted", err.as_dict()

    with factory() as session:
        record_call(
            session,
            request_id="rid-cr006b-redaction",
            capability=CAPABILITY_PHOTO_LINK_SUGGEST,
            provider_kind="vision",
            provider_name="openai_compatible",
            model="qwen3.8-flash",
            prompt_key="photo_link_suggest",
            prompt_version="v1",
            status="error",
            mock=False,
            error=err.as_dict(),
            input_ref={"photo_id": photo["photo_id"], "candidate_count": 1},
        )
        session.commit()

    last_attempt = _suggestions(world, photo["photo_id"])["last_attempt"]
    assert last_attempt is not None, last_attempt
    assert last_attempt["code"] == "quota_exhausted", last_attempt

    msg = last_attempt["message"]
    assert secret not in msg and "sk-" not in msg, msg
    assert "[REDACTED]" in msg, msg
    summary = msg.split("三方摘要: ", 1)[-1]
    assert len(summary) <= 201, len(summary)  # ≤200 字 + 省略号（写入侧单一来源约束）
    assert len(msg) <= 300, len(msg)


# ---------------------------------------------------------------- 4) 无记录 + 向后兼容
def test_last_attempt_is_null_without_records_and_keys_are_backward_compatible(
    world, factory, client, tmp_path
):
    """无 DATA-009 记录 / **DATA-009 表缺失** → `null`，且**主流程不报错**（`200`）。

    同时充当**向后兼容哨兵**：响应键集 = v0.4.2 基线 3 键 + 新增 1 字段（多=[] 少=[]）。

    **覆盖补强（`Task-025` 验收发现）**：`create_all` 已建出 `ai_call_records`，故「无记录」**不会**
    触达 `_last_attempt` 的 `except` 分支 —— 原断言（仅「无记录」）**不能证明「读取失败不阻断」**。
    本用例**显式 `DROP TABLE`**（真实失败模式：库回滚/表未建）→ 读取必然抛错 → 才能验证容错。
    """
    from app.core.ai.config import get_ai_settings
    from app.core.ai.service import get_ai_service
    from sqlalchemy import text

    get_ai_settings.cache_clear()
    get_ai_service.cache_clear()
    _override_settings(client, tmp_path, association_suggestion_enabled=False)

    stu = _student(world, "小N")
    photo = _upload(world, stu["student_id"])

    body = _suggestions(world, photo["photo_id"])
    assert body["last_attempt"] is None, body
    assert set(body) == BASELINE_KEYS | {"last_attempt"}, set(body)

    # 真造「DATA-009 读取失败」：表缺失 → 查询抛 `no such table` → 必须降级 `null` + 仍 `200`
    with factory() as session:
        session.execute(text("DROP TABLE IF EXISTS ai_call_records"))
        session.commit()

    degraded = _suggestions(world, photo["photo_id"])
    assert degraded["last_attempt"] is None, degraded
    assert degraded["suggestions"] == [] and degraded["status"] == "unassigned", degraded
