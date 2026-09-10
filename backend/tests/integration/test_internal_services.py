"""集成：内部服务接口（M002 消费方语义，契约 MODULE_API v0.2.0）。

内部越权统一 `PermissionDeniedError`（REST 层对外映射 404）。
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.modules.m001.repositories.group_repo import GroupRepo
from app.modules.m001.services.aggregation_service import (
    TaskAggregationService,
    register_links_migration_hook,
)
from app.modules.m001.services.family_space import FamilySpaceService
from app.modules.m001.services.task_service import TaskQueryService, TaskService
from app.modules.m001.services.task_state import TaskStateService
from app.modules.m001.services.window_resolver import DefaultWindowResolver
from app.shared.exceptions import ConflictError, InvalidTransitionError, PermissionDeniedError
from tests._m001_helpers import DAY, FRIDAY, TEST_TERM_START, create_task_v2, install_fixed_window, task_payload
from tests.conftest import create_student


def _settings(world):
    return world["client"].app.state.settings


def _task(world) -> tuple[dict, dict]:
    """创建 A 家学生 + 任务，返回 (student, task)。"""
    c, ha = world["client"], world["ha"]
    install_fixed_window(c, DAY, term_start=TEST_TERM_START)
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="内部学生")
    task = create_task_v2(c, ha, task_payload(stu["student_id"]))
    return stu, task


def test_family_space_get_student(world, factory):
    c, ha = world["client"], world["ha"]
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="家族空间")
    with factory() as s:
        dto = FamilySpaceService.get_student(s, world["family_id_a"], stu["student_id"])
        assert dto.name == "家族空间" and dto.school.name
        with pytest.raises(PermissionDeniedError):
            FamilySpaceService.get_student(s, world["family_id_b"], stu["student_id"])


def test_state_machine_mark_in_progress(world, factory):
    _, task = _task(world)
    tid = task["task_id"]
    with factory() as s:
        with pytest.raises(ConflictError):
            TaskStateService.mark_in_progress(s, world["family_id_a"], tid)
        TaskStateService.transition(s, world["family_id_a"], tid, "publish")
        _, st = TaskStateService.mark_in_progress(s, world["family_id_a"], tid)
        assert st == "in_progress"
        _, st2 = TaskStateService.mark_in_progress(s, world["family_id_a"], tid)
        assert st2 == "in_progress"
        _, st3 = TaskStateService.transition(s, world["family_id_a"], tid, "close")
        assert st3 == "closed"
        with pytest.raises(ConflictError):
            TaskStateService.mark_in_progress(s, world["family_id_a"], tid)
        with pytest.raises(PermissionDeniedError):
            TaskStateService.mark_in_progress(s, world["family_id_b"], tid)
        s.rollback()


def test_invalid_transition_direct(world, factory):
    _, task = _task(world)
    with factory() as s:
        with pytest.raises(InvalidTransitionError):
            TaskStateService.transition(s, world["family_id_a"], task["task_id"], "close")
        s.rollback()


def test_can_accept_submission(world, factory):
    _, task = _task(world)
    sid, tid = task["student_id"], task["task_id"]
    with factory() as s:
        q = TaskQueryService
        assert q.can_accept_submission(s, world["family_id_a"], tid, sid) is False
        TaskStateService.transition(s, world["family_id_a"], tid, "publish")
        assert q.can_accept_submission(s, world["family_id_a"], tid, sid) is True
        TaskStateService.mark_in_progress(s, world["family_id_a"], tid)
        assert q.can_accept_submission(s, world["family_id_a"], tid, sid) is True
        TaskStateService.transition(s, world["family_id_a"], tid, "close")
        assert q.can_accept_submission(s, world["family_id_a"], tid, sid) is False
        assert q.can_accept_submission(s, world["family_id_a"], tid, "00000000-0000-0000-0000-000000000000") is False
        assert q.can_accept_submission(s, world["family_id_b"], tid, sid) is False
        s.rollback()


def test_task_query_service_read_contract(world, factory):
    _, task = _task(world)
    tid = task["task_id"]
    with factory() as s:
        dto = TaskQueryService.get_task(s, world["family_id_a"], tid)
        assert dto.belong_date == DAY and dto.window_type == "day"
        assert len(dto.contents) == 1 and dto.contents[0].subject == "math"
        assert len(dto.sources) == 1
        with pytest.raises(PermissionDeniedError):
            TaskQueryService.get_task(s, world["family_id_b"], tid)
        lst = TaskQueryService.list_tasks(s, world["family_id_a"], student_id=task["student_id"])
        assert len(lst) == 1 and lst[0].task_id == dto.task_id


def test_get_task_invalid_status_raises(world, factory):
    _, task = _task(world)
    with factory() as s:
        task_row = TaskQueryService.get_task(s, world["family_id_a"], task["task_id"])
        assert task_row.status == "draft"
        s.rollback()


def test_resolve_window_is_pure_preview(world):
    resolver = DefaultWindowResolver(_settings(world))
    info = TaskQueryService.resolve_window(
        datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc), resolver=resolver
    )
    assert info.window_type == "weekend" and info.group_key == "W:2026-09-11"


def test_ensure_group_idempotent_and_policy_locked(world, factory):
    stu, task = _task(world)
    base = _settings(world)
    with factory() as s:
        r1 = DefaultWindowResolver(base.model_copy(update={"term_start": TEST_TERM_START}))
        g1 = TaskQueryService.ensure_group(
            s, world["family_id_a"], stu["student_id"], "school", DAY, resolver=r1
        )
        # 第二解析器配置不同（policy_version 不同）→ 仍命中同一聚合，policy_version 不被覆盖
        r2 = DefaultWindowResolver(base.model_copy(update={"term_start": "2026-01-01"}))
        g2 = TaskQueryService.ensure_group(
            s, world["family_id_a"], stu["student_id"], "school", DAY, resolver=r2
        )
        assert g1.group_id == g2.group_id
        assert g2.policy_version == r1.policy_version
        assert [x.subject for x in g2.subjects] == ["math"]
        assert g2.subjects[0].conclusion_status == "pending"
        s.rollback()


def test_commit_conclusion_roundtrip_and_scope(world, factory):
    stu, task = _task(world)
    with factory() as s:
        group = TaskAggregationService.ensure_group(
            s, world["family_id_a"], stu["student_id"], "school", DAY
        )
        subj_id = str(group.subjects[0].group_subject_id)
        out = TaskAggregationService.commit_conclusion(
            s, world["family_id_a"], subj_id, "pass", status="confirmed"
        )
        assert out.conclusion == "pass" and out.conclusion_status == "confirmed"
        # M002 网关形态（全关键字 + evidence_photo_ids）
        out2 = TaskAggregationService.commit_conclusion(
            s,
            world["family_id_a"],
            subj_id,
            conclusion="partial",
            evidence_photo_ids=["p1"],
            confidence=0.6,
            status="draft",
        )
        assert out2.conclusion == "partial" and out2.conclusion_status == "draft"
        with pytest.raises(PermissionDeniedError):
            TaskAggregationService.commit_conclusion(
                s, world["family_id_b"], subj_id, "pass", status="confirmed"
            )
        s.rollback()


def _swap_hook(fn):
    """注册临时回调并返回原回调（用例结束须原样恢复，避免污染 M002 注册契约用例）。"""
    from app.modules.m001.services import aggregation_service as ag

    original = ag._links_migration_hook
    register_links_migration_hook(fn)
    return original


def test_migrate_links_hook_registry(world, factory):
    calls: list[dict] = []
    original = _swap_hook(lambda **kw: calls.append(kw))
    try:
        _, task = _task(world)
        with factory() as s:
            TaskAggregationService.migrate_links_hook(
                s, world["family_id_a"], task["task_id"], DAY, f"W:{FRIDAY}"
            )
        assert calls and calls[0]["old_group_key"] == DAY and calls[0]["new_group_key"] == f"W:{FRIDAY}"
    finally:
        register_links_migration_hook(original)


def test_migrate_links_hook_skips_when_unregistered(world, factory, caplog):
    """未注册 → 记审计并跳过（不阻断事务）；M001 侧无反向 import 兜底。"""
    import logging

    original = _swap_hook(None)
    try:
        _, task = _task(world)
        with factory() as s:
            with caplog.at_level(logging.INFO):
                TaskAggregationService.migrate_links_hook(
                    s, world["family_id_a"], task["task_id"], DAY, f"W:{FRIDAY}"
                )
        assert "links_migration_skipped" in caplog.text
    finally:
        register_links_migration_hook(original)


def test_change_belong_date_moves_task_and_migrates(world, factory):
    calls: list[dict] = []
    original = _swap_hook(lambda **kw: calls.append(kw))
    try:
        stu, task = _task(world)
        resolver = DefaultWindowResolver(_settings(world))
        with factory() as s:
            dto = TaskService.change_belong_date(
                s, world["family_id_a"], task["task_id"], FRIDAY, resolver=resolver
            )
            assert dto.belong_date == FRIDAY and dto.window_type == "weekend"
            # 源聚合（DAY）因无剩余成员被删除
            assert GroupRepo.get_by_key(s, stu["student_id"], "school", DAY) is None
            new_group = GroupRepo.get_by_key(s, stu["student_id"], "school", f"W:{FRIDAY}")
            assert new_group is not None
            s.commit()
        assert calls and calls[0]["old_group_key"] == DAY
    finally:
        register_links_migration_hook(original)


def test_change_belong_date_rejected_after_consumed(world, factory):
    stu, task = _task(world)
    with factory() as s:
        group = TaskAggregationService.ensure_group(
            s, world["family_id_a"], stu["student_id"], "school", DAY
        )
        TaskAggregationService.commit_conclusion(
            s, world["family_id_a"], str(group.subjects[0].group_subject_id), "pass", status="confirmed"
        )
        with pytest.raises(ConflictError):
            TaskService.change_belong_date(
                s, world["family_id_a"], task["task_id"], FRIDAY, resolver=DefaultWindowResolver(_settings(world))
            )
        s.rollback()


def test_task_service_atomic_create_with_db_failure(world, factory):
    """同一学生/同日/同类型重复建任务 → 撞唯一约束，flush 失败整体回滚。"""
    from sqlalchemy.exc import IntegrityError

    from app.modules.m001.models.orm import Task
    from app.modules.m001.repositories.task_repo import TaskRepo

    c, ha = world["client"], world["ha"]
    stu = create_student(c, ha, school_id=world["school_primary"]["school_id"], name="事务学生")
    with factory() as s:
        kwargs = dict(
            family_id=world["family_id_a"],
            student_id=stu["student_id"],
            category="school",
            belong_date=DAY,
            week_index=2,
            window_type="day",
            title="事务任务",
            grade_level=None,
            deadline=None,
        )
        TaskRepo.create(s, **kwargs)
        with pytest.raises(IntegrityError):
            TaskRepo.create(s, **kwargs)
        s.rollback()
        assert s.scalar(select(Task).where(Task.family_id == world["family_id_a"])) is None
