"""API-M001-018：解析结果确认（显式 / 隐式 / 幂等 / 冲突 409）。"""
from __future__ import annotations

from tests._m001_helpers import DAY, create_task_v2, install_fixed_window, task_payload, text_source
from tests.conftest import create_student


def _setup(world, name: str = "确认学生") -> tuple[dict, dict]:
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY)
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name=name)
    task = create_task_v2(c, ha, task_payload(stu["student_id"]))
    return stu, task


def test_explicit_confirmation_replaces_contents(world):
    c, ha = world["client"], world["ha"]
    _, task = _setup(world)
    tid = task["task_id"]
    r = c.post(
        f"/api/v1/tasks/{tid}/parse-confirmation",
        json={"confirmed": True, "contents": [{"subject": "english", "text": "听写单词 10 个"}]},
        headers=ha,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["spec_status"] == "confirmed"
    assert [(x["subject"], x["text"]) for x in body["contents"]] == [("english", "听写单词 10 个")]
    # 幂等：重复确认（无内容差异）→ 200
    again = c.post(
        f"/api/v1/tasks/{tid}/parse-confirmation",
        json={"confirmed": True, "contents": [{"subject": "english", "text": "听写单词 10 个"}]},
        headers=ha,
    )
    assert again.status_code == 200


def test_confirmation_conflict_409(world):
    c, ha = world["client"], world["ha"]
    _, task = _setup(world)
    tid = task["task_id"]
    c.post(
        f"/api/v1/tasks/{tid}/parse-confirmation",
        json={"confirmed": True, "contents": [{"subject": "math", "text": "A"}]},
        headers=ha,
    )
    r = c.post(
        f"/api/v1/tasks/{tid}/parse-confirmation",
        json={"confirmed": True, "contents": [{"subject": "math", "text": "B"}]},
        headers=ha,
    )
    assert r.status_code == 409


def test_implicit_confirmation_with_digest(world):
    c, ha = world["client"], world["ha"]
    _, task = _setup(world, name="隐式学生")
    r = c.post(
        f"/api/v1/tasks/{task['task_id']}/parse-confirmation",
        json={
            "confirmed": True,
            "implicit": True,
            "digest": {"subjects": ["math"], "content_texts": ["练习册 P23 第 1-10 题"]},
        },
        headers=ha,
    )
    assert r.status_code == 200 and r.json()["spec_status"] == "confirmed"


def test_implicit_confirmation_without_digest_422(world):
    c, ha = world["client"], world["ha"]
    _, task = _setup(world, name="无摘要学生")
    r = c.post(
        f"/api/v1/tasks/{task['task_id']}/parse-confirmation",
        json={"confirmed": True, "implicit": True},
        headers=ha,
    )
    assert r.status_code == 422


def test_confirmation_other_family_404(world):
    c, hb = world["client"], world["hb"]
    _, task = _setup(world, name="他家确认")
    r = c.post(
        f"/api/v1/tasks/{task['task_id']}/parse-confirmation",
        json={"confirmed": True},
        headers=hb,
    )
    assert r.status_code == 404


def test_confirmation_after_reingest_idempotent(world):
    """已确认任务再次上传（追加内容）后确认无差异 → 不重复替换、保持 confirmed。"""
    c, ha = world["client"], world["ha"]
    stu, task = _setup(world, name="重传学生")
    tid = task["task_id"]
    c.post(f"/api/v1/tasks/{tid}/parse-confirmation", json={"confirmed": True}, headers=ha)
    create_task_v2(c, ha, task_payload(stu["student_id"], sources=[text_source("语文：背诵")]))
    body = c.get(f"/api/v1/tasks/{tid}", headers=ha).json()
    assert body["spec_status"] == "confirmed"
    assert {x["subject"] for x in body["contents"]} == {"math", "chinese"}
