"""聚合层读写（task_groups / task_group_subjects）。强制 family_id 过滤。

写一致性：聚合与成员任务的合并必须在同一事务/会话内完成；Repository 不自行 commit
（由请求级会话依赖统一 commit/rollback）。
"""
from __future__ import annotations

import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.m001.models.orm import TaskGroup, TaskGroupSubject


class GroupRepo:
    # —— task_groups ——
    @staticmethod
    def get_by_key(
        session: Session, student_id: str, category: str, group_key: str
    ) -> TaskGroup | None:
        stmt = select(TaskGroup).where(
            TaskGroup.student_id == student_id,
            TaskGroup.category == category,
            TaskGroup.group_key == group_key,
        )
        return session.scalar(stmt)

    @staticmethod
    def get_by_id(session: Session, family_id: str, group_id: str) -> TaskGroup | None:
        stmt = select(TaskGroup).where(
            TaskGroup.group_id == group_id, TaskGroup.family_id == family_id
        )
        return session.scalar(stmt)

    @staticmethod
    def create(
        session: Session,
        *,
        family_id: str,
        student_id: str,
        category: str,
        group_key: str,
        display_name: str,
        window_type: str,
        policy_version: str,
    ) -> TaskGroup:
        row = TaskGroup(
            family_id=family_id,
            student_id=student_id,
            category=category,
            group_key=group_key,
            display_name=display_name,
            window_type=window_type,
            policy_version=policy_version,
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def list_groups(
        session: Session,
        family_id: str,
        *,
        student_id: str | None = None,
        window_type: str | None = None,
    ) -> list[TaskGroup]:
        conds = [TaskGroup.family_id == family_id]
        if student_id:
            conds.append(TaskGroup.student_id == student_id)
        if window_type:
            conds.append(TaskGroup.window_type == window_type)
        stmt = select(TaskGroup).where(*conds).order_by(
            TaskGroup.group_key.desc(), TaskGroup.student_id.asc()
        )
        return list(session.scalars(stmt))

    @staticmethod
    def delete(session: Session, group: TaskGroup) -> None:
        session.execute(delete(TaskGroupSubject).where(TaskGroupSubject.group_id == group.group_id))
        session.delete(group)
        session.flush()

    # —— task_group_subjects ——
    @staticmethod
    def list_subjects(session: Session, group_id: str) -> list[TaskGroupSubject]:
        stmt = (
            select(TaskGroupSubject)
            .where(TaskGroupSubject.group_id == group_id)
            .order_by(TaskGroupSubject.subject.asc())
        )
        return list(session.scalars(stmt))

    @staticmethod
    def get_subject(session: Session, group_id: str, subject: str) -> TaskGroupSubject | None:
        stmt = select(TaskGroupSubject).where(
            TaskGroupSubject.group_id == group_id, TaskGroupSubject.subject == subject
        )
        return session.scalar(stmt)

    @staticmethod
    def get_subject_by_id(
        session: Session, family_id: str, group_subject_id: str
    ) -> tuple[TaskGroupSubject, TaskGroup] | None:
        stmt = (
            select(TaskGroupSubject, TaskGroup)
            .join(TaskGroup, TaskGroupSubject.group_id == TaskGroup.group_id)
            .where(
                TaskGroupSubject.group_subject_id == group_subject_id,
                TaskGroup.family_id == family_id,
            )
        )
        row = session.execute(stmt).first()
        return (row[0], row[1]) if row else None

    @staticmethod
    def upsert_subject(
        session: Session, group_id: str, subject: str, content_refs: list[str]
    ) -> TaskGroupSubject:
        row = GroupRepo.get_subject(session, group_id, subject)
        payload = json.dumps(content_refs, ensure_ascii=False)
        if row is None:
            row = TaskGroupSubject(group_id=group_id, subject=subject, content_refs=payload)
            session.add(row)
        else:
            row.content_refs = payload
        session.flush()
        return row

    @staticmethod
    def count_confirmed_subjects(session: Session, group_id: str) -> int:
        stmt = select(TaskGroupSubject).where(
            TaskGroupSubject.group_id == group_id,
            TaskGroupSubject.conclusion_status == "confirmed",
        )
        return len(list(session.scalars(stmt)))
