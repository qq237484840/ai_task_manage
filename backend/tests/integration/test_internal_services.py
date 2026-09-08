"""集成：内部服务接口（M002/M004/M005/M007 消费方语义，契约 MODULE_API）。

内部越权统一 PermissionDenied（403 语义），REST 层对外映射 404。
"""

import pytest
from sqlalchemy import select

from app.modules.m001.services.family_space import FamilySpaceService
from app.modules.m001.services.task_service import TaskQueryService
from app.modules.m001.services.task_state import TaskStateService
from app.shared.exceptions import ConflictError, InvalidTransitionError, PermissionDeniedError
from tests.conftest import create_student, create_task, valid_task_payload


def _task(world) -> tuple[dict, dict]:
    """创建 A 家学生 + 任务，返回 (student, task)。"""
    c, ha = world["client"], world["ha"]
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="内部学生")
    task = create_task(c, ha, valid_task_payload(stu["student_id"]))
    return stu, task


def test_family_space_get_student(world):
    c, ha = world["client"], world["ha"]
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="家族空间")
    with world["client"].app.state.session_factory() as s:
        dto = FamilySpaceService.get_student(s, world["family_id_a"], stu["student_id"])
        assert dto.name == "家族空间" and dto.school.name
        with pytest.raises(PermissionDeniedError):
            FamilySpaceService.get_student(s, world["family_id_b"], stu["student_id"])


def test_state_machine_mark_in_progress(world, factory):
    _, task = _task(world)
    tid = task["task_id"]
    with factory() as s:
        # draft 不可直接开始上传
        with pytest.raises(ConflictError):
            TaskStateService.mark_in_progress(s, world["family_id_a"], tid)
        # publish 后可以
        TaskStateService.transition(s, world["family_id_a"], tid, "publish")
        tid2, st = TaskStateService.mark_in_progress(s, world["family_id_a"], tid)
        assert st == "in_progress"
        # 幂等：重复调用不变
        _, st2 = TaskStateService.mark_in_progress(s, world["family_id_a"], tid)
        assert st2 == "in_progress"
        # in_progress 可 close
        _, st3 = TaskStateService.transition(s, world["family_id_a"], tid, "close")
        assert st3 == "closed"
        # 已关闭后不能再开始上传
        with pytest.raises(ConflictError):
            TaskStateService.mark_in_progress(s, world["family_id_a"], tid)
        # 其他家庭访问 → PermissionDenied
        with pytest.raises(PermissionDeniedError):
            TaskStateService.mark_in_progress(s, world["family_id_b"], tid)
        s.rollback()


def test_invalid_transition_direct(world, factory):
    _, task = _task(world)
    with factory() as s:
        with pytest.raises(InvalidTransitionError):
            TaskStateService.transition(s, world["family_id_a"], task["task_id"], "close")  # draft->close 非法


def test_can_accept_submission(world, factory):
    _, task = _task(world)
    sid, tid = task["student_id"], task["task_id"]
    with factory() as s:
        q = TaskQueryService
        assert q.can_accept_submission(s, world["family_id_a"], tid, sid) is False  # draft
        TaskStateService.transition(s, world["family_id_a"], tid, "publish")
        assert q.can_accept_submission(s, world["family_id_a"], tid, sid) is True  # published
        TaskStateService.mark_in_progress(s, world["family_id_a"], tid)
        assert q.can_accept_submission(s, world["family_id_a"], tid, sid) is True  # in_progress（继续上传）
        TaskStateService.transition(s, world["family_id_a"], tid, "close")
        assert q.can_accept_submission(s, world["family_id_a"], tid, sid) is False  # closed
        # 其他学生档案 → False；不存在任务 → False
        assert q.can_accept_submission(s, world["family_id_a"], tid, "00000000-0000-0000-0000-000000000000") is False
        assert q.can_accept_submission(s, world["family_id_b"], tid, sid) is False
        s.rollback()


def test_task_query_service_read_contract(world, factory):
    _, task = _task(world)
    sid, tid = task["student_id"], task["task_id"]
    with factory() as s:
        dto = TaskQueryService.get_task(s, world["family_id_a"], tid)
        assert dto.task_id and len(dto.items) == 2
        # 默认不带参考答案
        assert all(i.reference_answer is None for i in dto.items)
        # include_answers=true → 客观题参考答案
        full = TaskQueryService.get_task(s, world["family_id_a"], tid, include_answers=True)
        assert full.items[0].reference_answer == "96"
        # 越权 → PermissionDenied
        with pytest.raises(PermissionDeniedError):
            TaskQueryService.get_task(s, world["family_id_b"], tid)
        # 列表
        lst = TaskQueryService.list_tasks(s, world["family_id_a"])
        assert lst and all(len(x.items) == 2 for x in lst)


def test_task_service_atomic_create_with_db_failure(world, factory):
    """任务+题目集同事务：flush 阶段 DB 失败（重复 seq 撞唯一约束）→ 整单回滚。"""
    from sqlalchemy.exc import IntegrityError

    from app.modules.m001.models.orm import Task
    from app.modules.m001.repositories.task_repo import TaskRepo

    c, ha = world["client"], world["ha"]
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="事务学生")
    with factory() as s:
        task = TaskRepo.create(
            s, family_id=world["family_id_a"], student_id=stu["student_id"], title="事务任务",
            subject="math", grade_level=None, content=None, deadline=None,
        )
        dup_seq_items = [
            {"seq": 1, "item_type": "objective", "subject": "math", "stem": "x", "reference_answer": "1"},
            {"seq": 1, "item_type": "objective", "subject": "math", "stem": "y", "reference_answer": "2"},
        ]
        with pytest.raises(IntegrityError):  # 同一 seq 两次 → UNIQUE(task_id, seq) 失败
            TaskRepo.replace_items(s, task.task_id, dup_seq_items)
        s.rollback()
        # 任务未落库（半途失败整体回滚）
        assert s.scalar(select(Task).where(Task.family_id == world["family_id_a"])) is None
