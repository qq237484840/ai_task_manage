"""聚合层服务 `TaskAggregationService`（A6/A7/A8；MODULE_DESIGN §聚合生成）。

- `ensure_group`：**惰性 + 幂等**取/建 `task_groups`（`UNIQUE(student_id, category, group_key)`），
  新建时写 `policy_version` = 生成时生效配置；命中时**不覆盖**（追加数据不改）。
- `refresh_group`：按 `subject` 合并聚合内各天 `task_contents` → upsert `task_group_subjects`
  （★判定单元；`content_refs` = 确定性重算，保证幂等）。
- `commit_conclusion`：M002 回写判定结论的**唯一写入口**（DATA-013）。
- `migrate_links_hook`：改归属日跨聚合迁移时回调 M002 迁移 `photo_subject_links`（回调注册，
  M001 不 import M002，保持分层）。
"""
from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import audit_event
from app.modules.m001.models.orm import TaskGroup, TaskGroupSubject
from app.modules.m001.repositories.group_repo import GroupRepo
from app.modules.m001.repositories.task_repo import TaskRepo
from app.modules.m001.schemas.task_group import (
    TaskGroupDTO,
    TaskGroupSubjectDTO,
    WindowInfo,
)
from app.modules.m001.services.window_resolver import (
    DefaultWindowResolver,
    group_display_name,
    get_default_resolver,
)
from app.shared.exceptions import PermissionDeniedError, ValidationAppError

# —— M001 → M002 挂接迁移回调（注册式，M001 不反向 import M002） ——
_links_migration_hook: Callable[..., None] | None = None


def register_links_migration_hook(fn: Callable[..., None] | None) -> None:
    """M002 侧注册 `photo_subject_links` 迁移函数；传 None 注销。"""
    global _links_migration_hook
    _links_migration_hook = fn


def _parse_group_key_date(group: TaskGroup) -> date:
    """由 `group_key` 反解代表归属日（day=自身；weekend=周五；holiday=周一）。"""
    if group.window_type == "weekend":
        return date.fromisoformat(group.group_key.removeprefix("W:"))
    if group.window_type == "holiday":
        return date.fromisoformat(group.group_key.split(":")[1].split(".")[0])
    return date.fromisoformat(group.group_key)


def _window_from_group(resolver: DefaultWindowResolver, group: TaskGroup) -> WindowInfo:
    belong = _parse_group_key_date(group)
    return WindowInfo(
        belong_date=belong.isoformat(),
        week_index=resolver.week_index_for_date(belong),
        window_type=group.window_type,  # type: ignore[arg-type]
        group_key=group.group_key,
    )


def _subject_dto(row: TaskGroupSubject) -> TaskGroupSubjectDTO:
    refs: list[UUID] = []
    if row.content_refs:
        try:
            refs = [UUID(x) for x in json.loads(row.content_refs)]
        except (ValueError, TypeError, json.JSONDecodeError):
            refs = []
    return TaskGroupSubjectDTO(
        group_subject_id=UUID(row.group_subject_id),
        subject=row.subject,
        content_refs=refs,
        conclusion=row.conclusion,
        conclusion_status=row.conclusion_status,  # type: ignore[arg-type]
    )


def build_group_dto(session: Session, group: TaskGroup) -> TaskGroupDTO:
    subjects = GroupRepo.list_subjects(session, group.group_id)
    return TaskGroupDTO(
        group_id=UUID(group.group_id),
        student_id=UUID(group.student_id),
        category=group.category,
        group_key=group.group_key,
        display_name=group.display_name,
        window_type=group.window_type,  # type: ignore[arg-type]
        policy_version=group.policy_version,
        subjects=[_subject_dto(s) for s in subjects],
        created_at=group.created_at,
    )


class TaskAggregationService:
    """聚合层（`task_groups` + `task_group_subjects`）。"""

    @staticmethod
    def ensure_group(
        session: Session,
        family_id: str,
        student_id: str,
        category: str,
        belong_date: str,
        *,
        resolver: DefaultWindowResolver | None = None,
        window: WindowInfo | None = None,
    ) -> TaskGroupDTO:
        """幂等取/建聚合（写路径）。不覆盖已存在聚合的 `policy_version`。"""
        resolver = resolver or get_default_resolver()
        window = window or resolver.window_for_date(date.fromisoformat(belong_date))
        group = GroupRepo.get_by_key(session, student_id, category, window.group_key)
        if group is None:
            group = GroupRepo.create(
                session,
                family_id=family_id,
                student_id=student_id,
                category=category,
                group_key=window.group_key,
                display_name=group_display_name(window),
                window_type=window.window_type,
                policy_version=resolver.policy_version,
            )
            audit_event(
                "group_ensured",
                family_id=family_id,
                student_id=student_id,
                detail=f"group_key={window.group_key} window={window.window_type}",
            )
        TaskAggregationService.refresh_group(session, group, resolver=resolver)
        return build_group_dto(session, group)

    @staticmethod
    def member_tasks(
        session: Session, group: TaskGroup, *, resolver: DefaultWindowResolver | None = None
    ) -> list:
        """聚合窗口内的成员任务（按归属日升序）。"""
        resolver = resolver or get_default_resolver()
        dates = resolver.member_dates(_window_from_group(resolver, group))
        return TaskRepo.list_by_belong_dates(
            session, group.family_id, group.student_id, group.category, dates
        )

    @staticmethod
    def refresh_group(
        session: Session, group: TaskGroup, *, resolver: DefaultWindowResolver | None = None
    ) -> None:
        """按学科合并聚合成员任务的内容项 → upsert 判定单元（确定性重算，幂等）。"""
        resolver = resolver or get_default_resolver()
        tasks = TaskAggregationService.member_tasks(session, group, resolver=resolver)
        merged: dict[str, list[str]] = {}
        for task in tasks:
            for content in TaskRepo.list_contents(session, task.task_id):
                merged.setdefault(content.subject, []).append(content.content_id)
        existing = {s.subject: s for s in GroupRepo.list_subjects(session, group.group_id)}
        for subject, refs in merged.items():
            GroupRepo.upsert_subject(session, group.group_id, subject, sorted(set(refs)))
        for subject, row in existing.items():  # 成员移出后清空引用（保留结论，避免数据丢失）
            if subject not in merged:
                row.content_refs = json.dumps([], ensure_ascii=False)
        session.flush()

    @staticmethod
    def get_group_subject(
        session: Session, family_id: str, group_subject_id: str
    ) -> TaskGroupSubjectDTO:
        found = GroupRepo.get_subject_by_id(session, family_id, group_subject_id)
        if found is None:
            raise PermissionDeniedError("聚合学科子任务不存在或无权访问")
        return _subject_dto(found[0])

    @staticmethod
    def commit_conclusion(
        session: Session,
        family_id: str,
        group_subject_id: str,
        conclusion: str | None = None,
        evidence: object | None = None,
        confidence: float | None = None,
        status: str = "confirmed",
        *,
        evidence_photo_ids: list[str] | None = None,
    ) -> TaskGroupSubjectDTO:
        """M002 回写判定结论（DATA-013 唯一写入口）。

        `evidence`/`confidence`/`evidence_photo_ids` 属 DATA-017（M002 自有），此处仅作签名兼容
        与审计关联，不在 M001 落库（避免双写）。
        """
        if status not in ("pending", "draft", "confirmed"):
            raise ValidationAppError("conclusion_status 非法")
        found = GroupRepo.get_subject_by_id(session, family_id, group_subject_id)
        if found is None:
            raise PermissionDeniedError("聚合学科子任务不存在或无权访问")
        row, _group = found
        row.conclusion = conclusion
        row.conclusion_status = status
        session.flush()
        audit_event(
            "group_conclusion_committed",
            family_id=family_id,
            student_id=_group.student_id,
            detail=f"group_subject={row.group_subject_id} status={status}",
        )
        return _subject_dto(row)

    @staticmethod
    def migrate_links_hook(
        session: Session,
        family_id: str,
        task_id: str,
        old_group_key: str,
        new_group_key: str,
    ) -> None:
        """改归属日跨聚合迁移：回调 M002 迁移 `photo_subject_links` 挂接目标。

        回调**唯一来源为注册**（M002 导入期调用 `register_links_migration_hook`；
        `app/main.py` 启动期由 PM 幂等自愈再调用一次）。M001 不 import M002（分层）。
        未注册时记审计并跳过（不阻断改归属日事务）；
        已注册且实现抛错 → 异常上抛，令整体事务回滚（保持一致性）。
        """
        hook = _links_migration_hook
        if hook is None:
            audit_event(
                "links_migration_skipped",
                family_id=family_id,
                task_id=task_id,
                detail=f"{old_group_key}->{new_group_key} (m002 hook 未注册)",
            )
            return
        hook(
            session=session,
            family_id=family_id,
            task_id=task_id,
            old_group_key=old_group_key,
            new_group_key=new_group_key,
        )


# 契约命名别名（MODULE_API 内部接口表 = `TaskAggregationService`；M002 网关消费 `TaskGroupService`）
TaskGroupService = TaskAggregationService
