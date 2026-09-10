"""Task-011 ④ 验收：剧本 1~6（服务级 / API 级证据）+ 边界抽查。

证据级别约定（本文件）：
- 【服务级】= 直接调用生产解析器/服务，代码路径与运行时同源，**未注入桩**；
- 【API 级】= 经 FastAPI TestClient 打真实 HTTP 路由（真机 M001 聚合层 + 真实 `app/core/ai`）。

真实栈约定：M002 网关 = `DefaultM001Gateway`（默认，未注入 FakeGateway）；AI = 默认 `DefaultAiClient`
→ `app/core/ai`，无三方密钥时按 ADR-011 降级 **Mock Provider**（最低验收线）；建议调度改为**内联**执行
（消除后台线程时序抖动，业务逻辑不变）。

时钟约定：剧本 1~3 涉及「9/9 20:00 / 9/10 03:00 / 周五~周日」等**任意墙钟时刻**，只能用
`tests/_m001_helpers.install_fixed_window`（`FixedResolver`）注入归属日；**日界（4 点）规则本身**
由 `test_scenario1_*_service_level` 用生产 `DefaultWindowResolver` 对真实时间戳直接证明。
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.core.ai.config import get_ai_settings
from app.core.ai.service import get_ai_service
from app.core.config import Settings
from app.modules.m001.repositories.group_repo import GroupRepo
from app.modules.m001.services.aggregation_service import TaskAggregationService
from app.modules.m001.services.window_resolver import DefaultWindowResolver
from app.modules.m002.config import M002Settings, get_m002_settings
from app.modules.m002.services.suggestion_scheduler import set_scheduler
from tests._m001_helpers import (
    DAY,
    TEST_TERM_START,
    create_task_v2,
    image_source,
    install_fixed_window,
    task_payload,
    text_source,
)
from tests.conftest import create_student
from tests.m002_support import valid_jpeg

WEEKEND_DATES = ("2026-09-11", "2026-09-12", "2026-09-13")  # 周五 / 周六 / 周日
WEEKEND_KEY = "W:2026-09-11"
SUBJECTS = {"math", "chinese"}


# --------------------------------------------------------------------------- fixtures
@pytest.fixture
def real_stack(client, tmp_path):
    """真实栈：真机 M001 聚合（默认网关）+ 真实 app/core/ai（Mock 兜底）+ 内联建议调度。"""
    clear = getattr(get_ai_service, "cache_clear", None)
    clear_settings = getattr(get_ai_settings, "cache_clear", None)
    if clear is not None:
        clear()
    if clear_settings is not None:
        clear_settings()
    set_scheduler(lambda runner: runner())
    settings = M002Settings(image_store_root=str(tmp_path / "images"))
    client.app.dependency_overrides[get_m002_settings] = lambda: settings
    yield settings
    client.app.dependency_overrides.pop(get_m002_settings, None)
    set_scheduler(None)
    if clear is not None:
        clear()
    if clear_settings is not None:
        # 不得把测试内注入的 AI 配置（如 scenario6 的 real + 禁兜底）泄漏给后续用例
        clear_settings()


# --------------------------------------------------------------------------- helpers
def _student(world, name="验收学生") -> dict:
    return create_student(
        world["client"],
        world["ha"],
        school_id=world["school_primary"]["school_id"],
        name=name,
    )


def _groups(client, headers, student_id) -> list[dict]:
    r = client.get(f"/api/v1/task-groups?student_id={student_id}", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    return data["items"] if isinstance(data, dict) else data


def _batch(client, headers, student_id, kind="homework") -> dict:
    r = client.post(
        "/api/v1/upload-batches",
        json={"student_id": student_id, "kind": kind},
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


def _gates(client, headers, student_id, **params) -> list[dict]:
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


def _seed_window_day(world, *, student_id, belong_date=DAY) -> str:
    """造一个 day 窗口（真机链路）并返回其学科子任务 id。"""
    install_fixed_window(world["client"], belong_date, term_start=TEST_TERM_START)
    create_task_v2(
        world["client"],
        world["ha"],
        task_payload(student_id, sources=[text_source("数学：练习册 P23 第 1-10 题")]),
    )
    groups = _groups(world["client"], world["ha"], student_id)
    target = [g for g in groups if g["group_key"] == belong_date]
    assert len(target) == 1, groups
    return target[0]["subjects"][0]["group_subject_id"]


# =========================================================== 剧本 1：日界（凌晨 4 点）
def test_scenario1_day_cutoff_4am_service_level():
    """【服务级】剧本 1：9/9 20:00 与 9/10 03:00 同属 2026-09-09；04:00 起转次日。"""
    tz = ZoneInfo("Asia/Shanghai")
    resolver = DefaultWindowResolver(
        Settings(term_start=TEST_TERM_START, day_cutoff="04:00")
    )
    late = resolver.resolve(datetime(2026, 9, 9, 20, 0, tzinfo=tz))
    early = resolver.resolve(datetime(2026, 9, 10, 3, 0, tzinfo=tz))
    boundary = resolver.resolve(datetime(2026, 9, 10, 4, 0, tzinfo=tz))

    assert late.belong_date == "2026-09-09"
    assert early.belong_date == "2026-09-09"
    assert boundary.belong_date == "2026-09-10"
    assert late.group_key == early.group_key == DAY
    assert late.window_type == early.window_type == "day"
    assert resolver.policy_version == "v1:Asia/Shanghai|2026-09-01||04:00"


def test_scenario1_same_day_ingest_is_idempotent_api_level(world, real_stack):
    """【API 级】剧本 1：两批输入（模拟 20:00 / 03:00，同一归属日）→ 同一天任务幂等归集。"""
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)  # = 20:00 与 03:00 的共同归属日

    t1 = create_task_v2(c, ha, task_payload(stu["student_id"], sources=[text_source("数学：练习册 P23")]))
    t2 = create_task_v2(
        c, ha, task_payload(stu["student_id"], sources=[text_source("语文：背诵《静夜思》")])
    )

    assert t1["belong_date"] == t2["belong_date"] == DAY
    assert t1["task_id"] == t2["task_id"], "同日同类型应幂等归集，不新建任务"
    assert t1["window_type"] == "day"
    groups = _groups(c, ha, stu["student_id"])
    assert [g["group_key"] for g in groups] == [DAY]
    assert groups[0]["window_type"] == "day"


# =========================================================== 剧本 2：周五~周日合并
def test_scenario2_weekend_three_days_merge_service_and_api_level(world, factory, real_stack):
    """【服务级+API 级】剧本 2：周五/周六/周日 三次布置 → 单一「周末作业」聚合（3 天成员）。"""
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    resolver = None
    for index, day in enumerate(WEEKEND_DATES):
        resolver = install_fixed_window(c, day, term_start=TEST_TERM_START)
        create_task_v2(
            c,
            ha,
            task_payload(
                stu["student_id"],
                sources=[text_source(f"数学：周末练习册 P{20 + index}", seq=1)],
            ),
        )

    groups = _groups(c, ha, stu["student_id"])
    assert len(groups) == 1, f"三天应合并为 1 个聚合，实测 {[g['group_key'] for g in groups]}"
    group = groups[0]
    assert group["group_key"] == WEEKEND_KEY
    assert group["window_type"] == "weekend"
    assert group["display_name"] == "周末作业"
    assert {s["subject"] for s in group["subjects"]} == {"math"}

    # 成员任务 = 三天（服务级确证合并范围）
    with factory() as session:
        row = GroupRepo.get_by_key(session, stu["student_id"], "school", WEEKEND_KEY)
        assert row is not None
        members = TaskAggregationService.member_tasks(session, row, resolver=resolver)
        assert sorted(t.belong_date for t in members) == sorted(WEEKEND_DATES)
        assert len(row.policy_version) > 0


# =========================================================== 剧本 3：配置锁定
def test_scenario3_policy_version_locked_after_config_change_api_level(world, real_stack):
    """【API 级】剧本 3：已聚合对象的 policy_version 不随后续配置变更重算。"""
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)  # day_cutoff 默认 04:00
    create_task_v2(c, ha, task_payload(stu["student_id"], sources=[text_source("数学：练习册 P23")]))

    before = _groups(c, ha, stu["student_id"])[0]
    assert before["group_key"] == DAY
    assert before["policy_version"].endswith("|04:00")

    # 模拟「部署侧修改 AT_DAY_CUTOFF=03:00」后再写入 → 已存在聚合不得改写
    install_fixed_window(c, DAY, term_start=TEST_TERM_START, day_cutoff="03:00")
    create_task_v2(c, ha, task_payload(stu["student_id"], sources=[text_source("语文：背诵课文")]))

    after = _groups(c, ha, stu["student_id"])[0]
    assert after["group_key"] == DAY
    assert after["policy_version"] == before["policy_version"], "已聚合对象不得被重算"
    assert after["policy_version"].endswith("|04:00")
    assert before["group_id"] == after["group_id"]


# =========================================================== 剧本 4：任务解析 → 家长确认 → 落库
def test_scenario4_task_entry_parse_draft_then_family_confirm_api_level(world, real_stack):
    """【API 级】剧本 4：任务入口（文本/图片源）解析出草稿 → 家长确认 → 学科子任务落库。"""
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)

    task = create_task_v2(
        c,
        ha,
        task_payload(
            stu["student_id"],
            sources=[
                text_source("数学：练习册 P23 第 1-10 题", seq=1),
                text_source("语文：背诵《静夜思》", seq=2),
            ],
        ),
    )
    assert task["spec_status"] == "parsed"
    draft_subjects = {item["subject"] for item in task["contents"]}
    assert draft_subjects <= SUBJECTS, f"解析草稿学科异常：{draft_subjects}"

    confirm = c.post(
        f"/api/v1/tasks/{task['task_id']}/parse-confirmation",
        json={
            "confirmed": True,
            "contents": [
                {"subject": "math", "text": "练习册 P23 第 1-10 题"},
                {"subject": "chinese", "text": "背诵《静夜思》"},
            ],
        },
        headers=ha,
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["spec_status"] == "confirmed"

    groups = _groups(c, ha, stu["student_id"])
    assert [g["group_key"] for g in groups] == [DAY]
    assert {s["subject"] for s in groups[0]["subjects"]} == SUBJECTS


def test_scenario4_task_entry_image_source_mock_parse_api_level(world, real_stack):
    """【API 级】剧本 4（单照片原样）：任务入口传照片 → Mock 无法读图 → 不伪造草稿 → 家长确认后落库。

    去替身复审（`Task-014`）：`BUG-004` 修复后**文本源**已真跑 `app/core/ai`（链路 T）；本用例的
    **图片源**在无三方视觉密钥下仍**必然降级**（Mock Provider 不读图）→ 保持 `placeholder` 且
    `contents == []`（不伪造草稿）。该边界断言为**修复后事实**，未放宽。
    """
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)

    batch = _batch(c, ha, stu["student_id"], kind="task_spec")
    photo = _upload(c, ha, batch["batch_id"])
    task = create_task_v2(
        c, ha, task_payload(stu["student_id"], sources=[image_source(photo["photo_id"])])
    )

    # 无三方视觉密钥 → Mock 无法读图：不得伪造草稿，保持 placeholder 且 contents 为空（待人工确认）
    assert task["spec_status"] == "placeholder", task
    assert task["sources"][0]["kind"] == "image"
    assert task["sources"][0]["photo_id"] == photo["photo_id"]
    assert task["contents"] == [], f"图片源在 Mock 下不得伪造草稿：{task['contents']}"

    confirm = c.post(
        f"/api/v1/tasks/{task['task_id']}/parse-confirmation",
        json={
            "confirmed": True,
            "contents": [{"subject": "math", "text": "老师布置单照片（人工确认）"}],
        },
        headers=ha,
    )
    assert confirm.status_code == 200, confirm.text
    groups = _groups(c, ha, stu["student_id"])
    assert {s["subject"] for s in groups[0]["subjects"]} == {"math"}


# =========================================================== 剧本 5：作业挂接 → 门控 → 完成分析 → 确认
def test_scenario5_photo_link_gate_analysis_confirm_api_level(world, real_stack):
    """【API 级】剧本 5：3 张作业照片 → 逐张挂接确认 → 门控满足 → 201 草稿 → 家长确认。"""
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    gs = _seed_window_day(world, student_id=stu["student_id"])

    batch = _batch(c, ha, stu["student_id"])
    photos = [_upload(c, ha, batch["batch_id"]) for _ in range(3)]
    assert len({p["photo_id"] for p in photos}) == 3

    # AI 建议（真实链路 app/core/ai）；Mock 下的实测结果见 test_acceptance_ai_wiring.py
    sug = c.get(
        f"/api/v1/photos/{photos[0]['photo_id']}/link-suggestions?retry=true", headers=ha
    )
    assert sug.status_code == 200, sug.text
    body = sug.json()
    assert set(body) == {"photo_id", "status", "suggestions"}
    # 【API 面证据 / BUG-003】Mock Provider 必须经**真实装配路径**回显候选学科。
    # 修复前：`suggestions == []` 且 `status == "unassigned"`；仅断言响应形状**不足以**覆盖本缺陷
    # （形状断言修复前后都通过）→ 本组断言为 `Task-013-D1` 在 API 面的唯一证据。
    assert body["status"] == "suggested", body
    assert body["suggestions"], f"BUG-003：Mock 挂接建议不得为空：{body}"
    assert [s["group_subject_id"] for s in body["suggestions"]] == [gs], body

    for photo in photos:
        r = _accept(c, ha, photo["photo_id"], group_subject_id=gs)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "assigned"
        assert r.json()["links"][0]["confirmed_at"] is not None

    gates = _gates(c, ha, stu["student_id"])
    assert len(gates) == 1
    assert gates[0]["group_key"] == DAY and gates[0]["window_type"] == "day"
    assert gates[0]["total_photos"] == 3
    assert gates[0]["pending_photos"] == 0 and gates[0]["satisfied"] is True

    gen = _generate(c, ha, stu["student_id"], DAY)
    assert gen.status_code == 201, gen.text
    item = gen.json()["items"][0]
    assert item["status"] == "draft"
    assert item["conclusion"] == "完成"
    assert set(item["evidence_photo_ids"]) == {p["photo_id"] for p in photos}

    done = c.post(
        f"/api/v1/completion-analyses/{item['analysis_id']}/confirmation", json={}, headers=ha
    )
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "confirmed"
    assert done.json()["confirmed_at"] is not None


# =========================================================== 剧本 6：LLM 停用降级
def test_scenario6_llm_unavailable_keeps_unassigned_then_manual_link_api_level(
    world, real_stack, monkeypatch
):
    """【API 级】剧本 6：停用 LLM（real 模式 + 禁止 Mock 兜底）→ 照片 unassigned → 手工挂接可行。"""
    monkeypatch.setenv("AT_AI_PROVIDER_MODE", "real")
    monkeypatch.setenv("AT_AI_ALLOW_MOCK_FALLBACK", "false")
    # 必须同时清 settings 缓存：否则 `get_ai_settings()` 沿用前序用例缓存的 auto（Mock 兜底）
    # 配置，本用例不再真正走「real + 禁兜底」路径（BUG-003 修复前因 Mock 恒返回空建议而假通过）。
    get_ai_settings.cache_clear()
    get_ai_service.cache_clear()

    c, ha = world["client"], world["ha"]
    stu = _student(world)
    gs = _seed_window_day(world, student_id=stu["student_id"])

    batch = _batch(c, ha, stu["student_id"])
    photo = _upload(c, ha, batch["batch_id"])

    sug = c.get(
        f"/api/v1/photos/{photo['photo_id']}/link-suggestions?retry=true", headers=ha
    )
    assert sug.status_code == 200, sug.text
    assert sug.json()["suggestions"] == [], "LLM 不可用不得产生建议"
    assert sug.json()["status"] == "unassigned", "AI 失败必须保持 unassigned（可手工挂接）"

    # 不阻断：家长手工挂接仍可用
    manual = _accept(c, ha, photo["photo_id"], group_subject_id=gs)
    assert manual.status_code == 200, manual.text
    assert manual.json()["status"] == "assigned"
    assert manual.json()["links"][0]["source"] == "manual"

    gates = _gates(c, ha, stu["student_id"])
    assert len(gates) == 1 and gates[0]["total_photos"] == 1 and gates[0]["satisfied"] is True
    assert _generate(c, ha, stu["student_id"], DAY).status_code == 201


# =========================================================== 边界抽查
def test_boundary_cross_family_and_student_scope_404(world, real_stack):
    """【API 级】边界：跨家庭 404 防探测 + student 主体仅本人。"""
    c, ha, hb = world["client"], world["ha"], world["hb"]
    stu_a = _student(world, name="甲学生")
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)
    create_task_v2(c, ha, task_payload(stu_a["student_id"], sources=[text_source("数学：练习册 P23")]))
    batch = _batch(c, ha, stu_a["student_id"])
    photo = _upload(c, ha, batch["batch_id"])

    # 跨家庭：B 家庭读 A 家庭的照片 → 404（不得 403 泄露存在性）
    cross = c.get(f"/api/v1/photos/{photo['photo_id']}/link-suggestions", headers=hb)
    assert cross.status_code == 404, cross.text
    # 跨家庭门控：不得泄露任何窗口/计数（实测返回 200 + 空列表）
    cross_gate = c.get(f"/api/v1/photo-gates?student_id={stu_a['student_id']}", headers=hb)
    assert cross_gate.status_code == 200, cross_gate.text
    assert cross_gate.json() == [], cross_gate.text
    cross_batch = c.post(
        "/api/v1/upload-batches",
        json={"student_id": stu_a["student_id"], "kind": "homework"},
        headers=hb,
    )
    assert cross_batch.status_code == 404, cross_batch.text


def test_boundary_gate_not_satisfied_409_api_level(world, real_stack):
    """【API 级｜AI 建议**经真实装配路径**】边界：存在未确认挂接 → 门控未满足 → 409。

    去替身复审（`Task-014`）：原 `m002_ai_port` 端口替身（`MockAiClient` / `set_ai_client`）**已移除**；
    本用例的「AI 建议」由 **`app/core/ai` 真实装配路径**（`DefaultAiClient` → `app/core/ai` →
    Mock Provider 兜底）产出。

    证据形态 = **真实 AI 通路（Mock Provider，`mock=True`），非三方联调**（无三方密钥，既有已知边界）。
    判别力：断言 `status == "suggested"` 且 `suggestions` 非空且 `group_subject_id` 与播种一致 ——
    修复前（`BUG-003`）该链路建议恒空（`unassigned` + `[]`），故本组断言同时覆盖「去替身」与缺陷回归。
    """
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    gs = _seed_window_day(world, student_id=stu["student_id"])

    batch = _batch(c, ha, stu["student_id"])
    p1 = _upload(c, ha, batch["batch_id"])
    p2 = _upload(c, ha, batch["batch_id"])

    assert _accept(c, ha, p1["photo_id"], group_subject_id=gs).status_code == 200
    sug = c.get(f"/api/v1/photos/{p2['photo_id']}/link-suggestions?retry=true", headers=ha).json()
    # 【去替身复审】建议必须来自真实装配路径（app/core/ai → Mock Provider）；修复前为 []/unassigned
    assert sug["status"] == "suggested" and sug["suggestions"], sug
    assert [s["group_subject_id"] for s in sug["suggestions"]] == [gs], sug

    gates = _gates(c, ha, stu["student_id"], group_key=DAY)
    assert gates[0]["total_photos"] == 2
    assert gates[0]["pending_photos"] == 1
    assert gates[0]["satisfied"] is False

    blocked = _generate(c, ha, stu["student_id"], DAY)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["code"] == "gate_not_satisfied"


def test_boundary_analysis_confirmed_is_terminal_api_level(world, real_stack):
    """【API 级｜AI 建议**经真实装配路径**】边界：门控未满足 409 → 确认后可生成 → 已确认不可再确认 409。

    去替身复审（`Task-014`）：原 `m002_ai_port` 端口替身**已移除**；建议由 **`app/core/ai` 真实装配路径**
    产出（Mock Provider，`mock=True`；**非三方联调**）。链接 `link_id` 亦取自真实通路回传的建议。
    """
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    gs = _seed_window_day(world, student_id=stu["student_id"])

    batch = _batch(c, ha, stu["student_id"])
    photo = _upload(c, ha, batch["batch_id"])
    sug = c.get(
        f"/api/v1/photos/{photo['photo_id']}/link-suggestions?retry=true", headers=ha
    ).json()
    # 【去替身复审】建议来自真实装配路径（非端口替身）；修复前为 []/unassigned
    assert sug["status"] == "suggested", sug
    assert sug["suggestions"], f"BUG-003：真实装配路径下建议不得为空：{sug}"
    assert [s["group_subject_id"] for s in sug["suggestions"]] == [gs], sug

    blocked = _generate(c, ha, stu["student_id"], DAY)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["code"] == "gate_not_satisfied"

    link_id = sug["suggestions"][0]["link_id"]
    assert _accept(c, ha, photo["photo_id"], link_id=link_id).status_code == 200

    gen = _generate(c, ha, stu["student_id"], DAY)
    assert gen.status_code == 201, gen.text
    analysis_id = gen.json()["items"][0]["analysis_id"]

    first = c.post(
        f"/api/v1/completion-analyses/{analysis_id}/confirmation", json={}, headers=ha
    )
    assert first.status_code == 200, first.text
    second = c.post(
        f"/api/v1/completion-analyses/{analysis_id}/confirmation", json={}, headers=ha
    )
    assert second.status_code == 409, second.text
    assert second.json()["code"] in {"analysis_confirmed", "analysis_state"}
    assert gs
