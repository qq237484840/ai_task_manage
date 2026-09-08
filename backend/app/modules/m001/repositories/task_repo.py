"""任务与题目集读写（tasks / task_items）。强制 family_id 过滤。

写一致性：任务+题目集必须在同一事务/会话内完成；Repository 不自行 commit ——
由请求级会话依赖统一 commit/rollback（失败整体回滚，MODULE_DATA 约束）。
"""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.modules.m001.models.orm import Task, TaskItem

_TASK_STATUSES = ("draft", "published", "in_progress", "closed")
_UNSET = object()  # 区分"未提供"与"显式置空(None)"（PATCH 语义）


class TaskRepo:
    @staticmethod
    def create(
        session: Session,
        *,
        family_id: str,
        student_id: str,
        title: str,
        subject: str | None,
        grade_level: str | None,
        content: str | None,
        deadline: str | None,
    ) -> Task:
        row = Task(
            family_id=family_id,
            student_id=student_id,
            title=title,
            subject=subject,
            grade_level=grade_level,
            content=content,
            status="draft",
            deadline=deadline,
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def replace_items(session: Session, task_id: str, items: list[dict]) -> None:
        """整体替换题目集（同事务 delete+insert）。items 元素已通过业务校验（含 group_no）。"""
        session.execute(delete(TaskItem).where(TaskItem.task_id == task_id))
        for it in items:
            session.add(
                TaskItem(
                    task_id=task_id,
                    seq=it["seq"],
                    item_type=it["item_type"],
                    subject=it["subject"],
                    group_no=it.get("group_no", 0),
                    stem=it["stem"],
                    reference_answer=it.get("reference_answer"),
                )
            )
        session.flush()

    @staticmethod
    def list_items(session: Session, task_id: str) -> list[TaskItem]:
        stmt = select(TaskItem).where(TaskItem.task_id == task_id).order_by(TaskItem.seq.asc())
        return list(session.scalars(stmt))

    @staticmethod
    def list_items_in_group(
        session: Session, task_id: str, subject: str, group_no: int
    ) -> list[TaskItem]:
        """某学科作业段（subject+group_no）内题目（CR-001 段归属目标）。"""
        stmt = (
            select(TaskItem)
            .where(
                TaskItem.task_id == task_id,
                TaskItem.subject == subject,
                TaskItem.group_no == group_no,
            )
            .order_by(TaskItem.seq.asc())
        )
        return list(session.scalars(stmt))

    @staticmethod
    def group_stats(session: Session, task_id: str) -> dict[tuple[str, int], int]:
        """任务内 (subject, group_no) → 题数（CR-001 段结构）。"""
        rows = session.execute(
            select(TaskItem.subject, TaskItem.group_no, func.count())
            .where(TaskItem.task_id == task_id)
            .group_by(TaskItem.subject, TaskItem.group_no)
        ).all()
        return {(subj, grp): cnt for subj, grp, cnt in rows}

    @staticmethod
    def get_by_id(session: Session, family_id: str, task_id: str) -> Task | None:
        stmt = select(Task).where(Task.task_id == task_id, Task.family_id == family_id)
        return session.scalar(stmt)

    @staticmethod
    def list_tasks(
        session: Session,
        family_id: str,
        *,
        status: str | None = None,
        student_id: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Task], int]:
        conds = [Task.family_id == family_id]
        if status:
            conds.append(Task.status == status)
        if student_id:
            conds.append(Task.student_id == student_id)
        base = select(Task).where(*conds)
        total = session.scalar(select(func.count()).select_from(Task).where(*conds)) or 0
        rows = list(
            session.scalars(base.order_by(Task.created_at.desc(), Task.task_id.desc()).offset(offset).limit(limit))
        )
        return rows, total

    @staticmethod
    def set_status(session: Session, task: Task, status: str) -> None:
        if status not in _TASK_STATUSES:  # 防御：非法值不应落入数据库
            raise ValueError(f"invalid task status: {status}")
        task.status = status
        session.flush()

    @staticmethod
    def update_fields(
        session: Session,
        task: Task,
        *,
        title: str | object = _UNSET,
        content: str | None | object = _UNSET,
        deadline: str | None | object = _UNSET,
    ) -> None:
        """更新可编辑字段；显式 None（content/deadline）= 清除；updated_at 由 onupdate 维护。"""
        if title is not _UNSET:
            task.title = title
        if content is not _UNSET:
            task.content = content
        if deadline is not _UNSET:
            task.deadline = deadline
        session.flush()
