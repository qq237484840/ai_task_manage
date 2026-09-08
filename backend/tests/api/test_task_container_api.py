"""API：多学科作业登记单容器（CR-001：subject 放宽 + 学科作业段 group_no）。"""
from __future__ import annotations

from tests.conftest import create_student, valid_task_payload


def _item(seq: int, *, subject: str, group_no: int = 0, item_type: str = "objective") -> dict:
    return {
        "seq": seq,
        "item_type": item_type,
        "subject": subject,
        "group_no": group_no,
        "stem": f"第{seq}题",
        "reference_answer": "1" if item_type == "objective" else None,
    }


def _a_student(world) -> dict:
    return create_student(world["client"], world["ha"], school_id=world["school_primary"]["school_id"], name="多科生")


def test_create_multi_subject_container_task_without_subject(world):
    """多学科登记单：task.subject 留空（NULL）+ 题目按 (subject, group_no) 显式分段。"""
    c, ha = world["client"], world["ha"]
    stu = _a_student(world)
    items = [_item(1, subject="math", group_no=1), _item(2, subject="math", group_no=1),
             _item(3, subject="chinese", group_no=2, item_type="subjective")]
    resp = c.post(
        "/api/v1/tasks",
        json=valid_task_payload(stu["student_id"], title="多科登记单", subject=None, items=items),
        headers=ha,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["subject"] is None
    assert [(i["subject"], i["group_no"]) for i in data["items"]] == [
        ("math", 1),
        ("math", 1),
        ("chinese", 2),
    ]


def test_create_mixed_subject_container_task(world):
    """subject='mixed' 保留字面语义（多学科登记单标注）。"""
    c, ha = world["client"], world["ha"]
    stu = _a_student(world)
    items = [_item(1, subject="math", group_no=1), _item(2, subject="english", group_no=2)]
    resp = c.post(
        "/api/v1/tasks",
        json=valid_task_payload(stu["student_id"], subject="mixed", items=items),
        headers=ha,
    )
    assert resp.status_code == 201
    assert resp.json()["subject"] == "mixed"


def test_create_task_group_structure_violations_422(world):
    """显式分组结构违规 → 422（混入 0 / 组号不连续 / 交错 / 组内科目不一）。"""
    c, ha = world["client"], world["ha"]
    stu = _a_student(world)
    cases = [
        [_item(1, subject="math", group_no=0), _item(2, subject="math", group_no=1)],          # 混 0
        [_item(1, subject="math", group_no=1), _item(2, subject="math", group_no=3)],          # 不连续
        [_item(1, subject="math", group_no=1), _item(2, subject="math", group_no=2),
         _item(3, subject="math", group_no=1)],                                                # 交错
        [_item(1, subject="math", group_no=1), _item(2, subject="english", group_no=1)],       # 组内科目不一
    ]
    for items in cases:
        resp = c.post(
            "/api/v1/tasks",
            json=valid_task_payload(stu["student_id"], title="非法分组", items=items),
            headers=ha,
        )
        assert resp.status_code == 422, resp.text


def test_legacy_single_subject_task_default_group_ok(world):
    """旧单学科任务（无 group_no）默认收敛为 0 段，行为向后兼容。"""
    c, ha = world["client"], world["ha"]
    stu = _a_student(world)
    resp = c.post("/api/v1/tasks", json=valid_task_payload(stu["student_id"], title="旧单科"), headers=ha)
    assert resp.status_code == 201
    assert resp.json()["subject"] == "math"
    assert all(i["group_no"] == 0 for i in resp.json()["items"])
