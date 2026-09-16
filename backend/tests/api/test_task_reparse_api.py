"""API 级：`API-M001-022` 任务重新解析（`CR-005` / `Task-019`）。

覆盖（任务书 §3.4）：

1. **防伪造（判别力，无桩）**：默认测试环境 = Mock Vision → 图片源**不转发** → `placeholder` + `contents==[]`；
2. **转发链路（桩）**：真实判据 + 已注册 provider → `_to_ai_sources` 中**出现 image 源**；
3. `placeholder` + 解析成功 → 写入内容项 → `parsed`；
4. `parsed`（未确认）+ 解析成功 → **整体替换**既有内容项；
5. **AI 不可用（`real` + 禁兜底）→ 不清空**：既有内容项与 `spec_status` **不变**；
6. `confirmed` → **`409 spec_confirmed`**；
7. 图片源 + **槽未注册** → 不转发、不报错（`placeholder`）。

**桩说明（PM 铁律 ①）**：用例 2/7 注入 `task_parser._vision_is_real`（真实性判据）与
`image_provider` 槽（假 provider），仅用于验证「转发/不转发」分支；用例 3/4 注入假 AI parser
以构造**成功**结果。**核心结论（防伪造 / 不清空 / 409 / 槽未注册不报错）均由不依赖桩的用例取得。**
"""
from __future__ import annotations

from app.core.ai.schemas import ParsedContentItem, ParsedSubject
from app.core.ai.types import TaskParseOutcome
from app.modules.m001.services import image_provider as ip
from app.modules.m001.services import task_parser
from tests._m001_helpers import (
    DAY,
    TEST_TERM_START,
    create_task_v2,
    install_fixed_window,
    task_payload,
    text_source,
)
from tests.conftest import create_student

IMAGE_ID = "33333333-3333-3333-3333-333333333333"
_IMAGE_SOURCE = {"seq": 1, "kind": "image", "photo_id": IMAGE_ID}


def _student(world, name="小R"):
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)
    return create_student(c, ha, school_id=world["school_primary"]["school_id"], name=name)


def _reparse(c, ha, task_id: str):
    return c.post(f"/api/v1/tasks/{task_id}/reparse", headers=ha)


def _set_real_no_fallback(monkeypatch) -> None:
    """切到 `real` + 禁兜底（AI 不可用即**如实失败**，`BUG-006` 语义）。"""
    from app.core.ai.config import get_ai_settings
    from app.core.ai.service import get_ai_service

    monkeypatch.setenv("AT_AI_PROVIDER_MODE", "real")
    monkeypatch.setenv("AT_AI_ALLOW_MOCK_FALLBACK", "false")
    get_ai_settings.cache_clear()
    get_ai_service.cache_clear()


def _drafts_parser(subject: str, text: str):
    """假 AI parser：返回**成功**的 `TaskParseOutcome`（桩，仅用于构造成功分支）。"""

    def _parser(session, *, family_id=None, sources=None, **kwargs):
        return TaskParseOutcome(
            capability="task_spec_parse",
            ok=True,
            available=True,
            request_id="req-reparse-test",
            prompt_key="task_spec_parse",
            prompt_version="v-test",
            subjects=[
                ParsedSubject(subject=subject, contents=[ParsedContentItem(text=text)]),
            ],
        )

    return _parser


# ---------------------------------------------------------------- 1) 防伪造（无桩）
def test_image_source_not_forwarded_when_vision_is_mock(world):
    """Mock Vision（默认环境）→ 图片源不转发 → `placeholder` + `contents==[]`（**不伪造**）。"""
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    task = create_task_v2(c, ha, task_payload(stu["student_id"], sources=[_IMAGE_SOURCE]))
    assert task["spec_status"] == "placeholder"
    assert task["contents"] == []

    r = _reparse(c, ha, task["task_id"])

    assert r.status_code == 200, r.text
    assert r.json()["spec_status"] == "placeholder"
    assert r.json()["contents"] == []


def test_no_forgery_when_vision_mock_even_if_provider_registered(world, monkeypatch, tmp_path):
    """**防伪造（判别力核心）**：Mock Vision **且** provider 已注册可取到图 → 仍**不转发**。

    若移除 `_vision_is_real()` 判据（红取证）→ 图片源被转发 → Mock Vision 产出占位草稿
    → `spec_status` 变为 `parsed` ⇒ 本用例**立败**（证明「不伪造」是真判据，非无脑通过）。
    """
    img = tmp_path / "page.jpg"
    img.write_bytes(b"\xff\xd8\xff\xd9")
    ip.register_task_spec_image_provider(
        lambda session, family_id, photo_id: ip.TaskSourceImage(
            mime="image/jpeg", abs_path=str(img)
        )
    )
    try:
        c, ha = world["client"], world["ha"]
        stu = _student(world)
        task = create_task_v2(c, ha, task_payload(stu["student_id"], sources=[_IMAGE_SOURCE]))

        r = _reparse(c, ha, task["task_id"])

        assert r.status_code == 200, r.text
        assert r.json()["spec_status"] == "placeholder", "Mock 下不得转发图片源（防伪造草稿）"
        assert r.json()["contents"] == []
    finally:
        ip.register_task_spec_image_provider(None)


# ---------------------------------------------------------------- 2) 转发链路（桩）
def test_image_source_is_forwarded_when_vision_real_and_provider_registered(
    world, monkeypatch, tmp_path
):
    """桩：真实性判据为真 + provider 已注册 → 适配结果中**出现 image 源**。"""
    img = tmp_path / "page.jpg"
    img.write_bytes(b"\xff\xd8\xff\xd9")
    captured: dict = {}

    def _fake_provider(session, family_id, photo_id):
        return ip.TaskSourceImage(mime="image/jpeg", abs_path=str(img))

    def _spy_parser(session, *, family_id=None, sources=None, **kwargs):
        captured["sources"] = sources
        return None  # 无草稿：只验证「是否转发」，不涉及结果

    ip.register_task_spec_image_provider(_fake_provider)
    monkeypatch.setattr(task_parser, "_vision_is_real", lambda: True)
    monkeypatch.setattr(task_parser, "_ai_parser", lambda: _spy_parser)
    try:
        c, ha = world["client"], world["ha"]
        stu = _student(world)
        task = create_task_v2(c, ha, task_payload(stu["student_id"], sources=[_IMAGE_SOURCE]))

        r = _reparse(c, ha, task["task_id"])

        assert r.status_code == 200, r.text
        sources = captured.get("sources") or []
        assert [s.kind for s in sources] == ["image"], f"sources={sources}"
        assert sources[0].image is not None
        assert sources[0].image.path == str(img)
    finally:
        ip.register_task_spec_image_provider(None)  # 恢复现场（避免污染其它用例）


# ---------------------------------------------------------------- 7) 槽未注册
def test_image_source_not_forwarded_when_provider_absent(world, monkeypatch):
    """判据为真但**槽未注册**（M002 未就绪）→ 不转发、不报错（`placeholder`）。"""
    monkeypatch.setattr(task_parser, "_vision_is_real", lambda: True)
    ip.register_task_spec_image_provider(None)
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    task = create_task_v2(c, ha, task_payload(stu["student_id"], sources=[_IMAGE_SOURCE]))

    r = _reparse(c, ha, task["task_id"])

    assert r.status_code == 200, r.text
    assert r.json()["spec_status"] == "placeholder"
    assert r.json()["contents"] == []


# ---------------------------------------------------------------- 3) placeholder → parsed
def test_reparse_from_placeholder_writes_contents_and_parses(world, monkeypatch):
    """`placeholder` + 解析成功 → 写入内容项 → `parsed`（AI 产物被消费）。

    构造方式：先以 `real` + 禁兜底建任务（ingest **如实失败** → `placeholder`），
    再注入假 AI parser 后 `reparse` → 成功写入。
    """
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    _set_real_no_fallback(monkeypatch)
    task = create_task_v2(
        c, ha, task_payload(stu["student_id"], sources=[text_source("数学：练习册 P23")])
    )
    assert task["spec_status"] == "placeholder" and task["contents"] == []

    monkeypatch.setattr(task_parser, "_ai_parser", lambda: _drafts_parser("math", "口算 20 题"))

    r = _reparse(c, ha, task["task_id"])

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["spec_status"] == "parsed"
    assert [(x["subject"], x["text"]) for x in body["contents"]] == [("math", "口算 20 题")]


# ---------------------------------------------------------------- 4) parsed → 整体替换
def test_reparse_replaces_contents_when_parsed_unconfirmed(world, monkeypatch):
    """`parsed`（未确认）+ 解析成功 → **整体替换**（以本次为准，不追加）。"""
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    task = create_task_v2(
        c, ha, task_payload(stu["student_id"], sources=[text_source("数学：练习册 P23")])
    )
    assert task["spec_status"] == "parsed"
    assert [x["text"] for x in task["contents"]] == ["练习册 P23"]

    monkeypatch.setattr(task_parser, "_ai_parser", lambda: _drafts_parser("chinese", "背诵第三课"))
    r = _reparse(c, ha, task["task_id"])

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["spec_status"] == "parsed"
    assert [(x["subject"], x["text"]) for x in body["contents"]] == [("chinese", "背诵第三课")]


# ---------------------------------------------------------------- 5) 失败不清空
def test_reparse_failure_keeps_existing_contents(world, monkeypatch):
    """AI 不可用（`real` + 禁兜底）→ **不改动**既有内容项与 `spec_status`（**不清空**）。"""
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    task = create_task_v2(
        c, ha, task_payload(stu["student_id"], sources=[text_source("数学：练习册 P23")])
    )
    before = [(x["subject"], x["text"]) for x in task["contents"]]
    assert before == [("math", "练习册 P23")]

    _set_real_no_fallback(monkeypatch)  # AI 不可用 → 如实失败（不兜底）

    r = _reparse(c, ha, task["task_id"])

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["spec_status"] == "parsed", "失败不得改变 spec_status"
    assert [(x["subject"], x["text"]) for x in body["contents"]] == before, "失败不得清空内容项"


# ---------------------------------------------------------------- 6) confirmed → 409
def test_reparse_rejected_when_confirmed(world):
    """`confirmed` → `409 spec_confirmed`（不执行）。"""
    c, ha = world["client"], world["ha"]
    stu = _student(world)
    task = create_task_v2(
        c, ha, task_payload(stu["student_id"], sources=[text_source("数学：练习册 P23")])
    )
    confirm = c.post(
        f"/api/v1/tasks/{task['task_id']}/parse-confirmation",
        json={"confirmed": True},
        headers=ha,
    )
    assert confirm.status_code == 200, confirm.text

    r = _reparse(c, ha, task["task_id"])

    assert r.status_code == 409, r.text
    assert r.json()["code"] == "conflict" or r.json().get("message")
