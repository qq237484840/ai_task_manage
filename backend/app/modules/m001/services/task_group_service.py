"""聚合层对外门面 `TaskGroupService`（M002 `DefaultM001Gateway` 消费面）。

与 `TaskAggregationService`（契约文档命名）等价；本模块提供 M002 网关已采用的**全关键字**
调用形态（`ensure_group`/`commit_conclusion` 全 kw、`list_groups` 支持 `group_key`），
作为跨模块调用的稳定落地点，避免签名漂移。
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.modules.m001.repositories.group_repo import GroupRepo
from app.modules.m001.schemas.task_group import TaskGroupDTO, TaskGroupSubjectDTO
from app.modules.m001.services.aggregation_service import (
    TaskAggregationService,
    build_group_dto,
    register_links_migration_hook,
)
from app.modules.m001.services.window_resolver import DefaultWindowResolver, get_default_resolver
from app.shared.exceptions import NotFoundError

__all__ = ["TaskGroupService", "register_links_migration_hook"]


class TaskGroupService:
    """聚合层门面（供 M002 内部网关；全部方法携带 `family_id` 上下文）。"""

    @staticmethod
    def ensure_group(
        session: Session,
        family_id: str,
        *,
        student_id: str,
        category: str,
        belong_date: str,
        resolver: DefaultWindowResolver | None = None,
    ) -> TaskGroupDTO:
        return TaskAggregationService.ensure_group(
            session, family_id, student_id, category, belong_date, resolver=resolver
        )

    @staticmethod
    def get_group(session: Session, family_id: str, group_id: str) -> TaskGroupDTO:
        group = GroupRepo.get_by_id(session, family_id, group_id)
        if group is None:
            raise NotFoundError("聚合对象不存在")
        return build_group_dto(session, group)

    @staticmethod
    def list_groups(
        session: Session,
        family_id: str,
        *,
        student_id: str | None = None,
        group_key: str | None = None,
        week_index: int | None = None,
        window_type: str | None = None,
        resolver: DefaultWindowResolver | None = None,
    ) -> list[TaskGroupDTO]:
        rows = GroupRepo.list_groups(
            session, family_id, student_id=student_id, window_type=window_type
        )
        if group_key:
            rows = [g for g in rows if g.group_key == group_key]
        if week_index is not None:
            resolver = resolver or get_default_resolver()
            rows = [
                g
                for g in rows
                if _week_index_of(resolver, g.group_key, g.window_type) == week_index
            ]
        return [build_group_dto(session, g) for g in rows]

    @staticmethod
    def get_group_subject(
        session: Session, family_id: str, group_subject_id: str
    ) -> TaskGroupSubjectDTO:
        return TaskAggregationService.get_group_subject(session, family_id, group_subject_id)

    @staticmethod
    def commit_conclusion(
        session: Session,
        family_id: str,
        *,
        group_subject_id: str,
        conclusion: str | None,
        evidence_photo_ids: list[str] | None = None,
        confidence: float | None = None,
        status: str = "confirmed",
    ) -> TaskGroupSubjectDTO:
        return TaskAggregationService.commit_conclusion(
            session,
            family_id,
            group_subject_id,
            conclusion,
            confidence=confidence,
            status=status,
            evidence_photo_ids=evidence_photo_ids,
        )

    @staticmethod
    def migrate_links_hook(
        session: Session,
        family_id: str,
        task_id: str,
        old_group_key: str,
        new_group_key: str,
    ) -> None:
        TaskAggregationService.migrate_links_hook(
            session, family_id, task_id, old_group_key, new_group_key
        )


def _week_index_of(
    resolver: DefaultWindowResolver, group_key: str, window_type: str
) -> int:
    if window_type == "weekend":
        belong = date.fromisoformat(group_key.removeprefix("W:"))
    elif window_type == "holiday":
        belong = date.fromisoformat(group_key.split(":")[1].split(".")[0])
    else:
        belong = date.fromisoformat(group_key)
    return resolver.week_index_for_date(belong)
