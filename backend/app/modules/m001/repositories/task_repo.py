"""事实层读写（tasks / task_contents / task_spec_sources）。强制 family_id 过滤。

事实层按天（ADR-013）：唯一键 `(student_id, category, belong_date)`。
写一致性：任务 + 输入源 + 内容项必须在同一事务/会话内完成；Repository 不自行 commit ——
由请求级会话依赖统一 commit/rollback（失败整体回滚，MODULE_DATA 约束）。

`task_items` 相关方法为 **Deprecated 兼容桩**（表保留；新链路不写入，不得新增调用）。
"""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.modules.m001.models.orm import Task, TaskContent, TaskItem, TaskSpecSource

_TASK_STATUSES = ("draft", "published", "in_progress", "closed")
_UNSET = object()  # 区分"未提供"与"显式置空(None)"（PATCH 语义）


class TaskRepo:
    # —— 事实层主表 ——
    @staticmethod
    def create(
        session: Session,
        *,
        family_id: str,
        student_id: str,
        category: str,
        belong_date: str,
        week_index: int,
        window_type: str,
        title: str,
        grade_level: str | None,
        deadline: str | None,
        spec_status: str = "placeholder",
    ) -> Task:
        row = Task(
            family_id=family_id,
            student_id=student_id,
            category=category,
            belong_date=belong_date,
            week_index=week_index,
            window_type=window_type,
            title=title,
            grade_level=grade_level,
            deadline=deadline,
            spec_status=spec_status,
            status="draft",
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def get_by_id(session: Session, family_id: str, task_id: str) -> Task | None:
        stmt = select(Task).where(Task.task_id == task_id, Task.family_id == family_id)
        return session.scalar(stmt)

    @staticmethod
    def get_by_day(
        session: Session, student_id: str, category: str, belong_date: str
    ) -> Task | None:
        """事实层按天唯一键命中（同一学生/同日/同分类）。"""
        stmt = select(Task).where(
            Task.student_id == student_id,
            Task.category == category,
            Task.belong_date == belong_date,
        )
        return session.scalar(stmt)

    @staticmethod
    def list_tasks(
        session: Session,
        family_id: str,
        *,
        status: str | None = None,
        student_id: str | None = None,
        belong_date: str | None = None,
        week_index: int | None = None,
        category: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Task], int]:
        conds = [Task.family_id == family_id]
        if status:
            conds.append(Task.status == status)
        if student_id:
            conds.append(Task.student_id == student_id)
        if belong_date:
            conds.append(Task.belong_date == belong_date)
        if week_index is not None:
            conds.append(Task.week_index == week_index)
        if category:
            conds.append(Task.category == category)
        base = select(Task).where(*conds)
        total = session.scalar(select(func.count()).select_from(Task).where(*conds)) or 0
        rows = list(
            session.scalars(
                base.order_by(Task.belong_date.desc(), Task.task_id.desc()).offset(offset).limit(limit)
            )
        )
        return rows, total

    @staticmethod
    def list_by_belong_dates(
        session: Session,
        family_id: str,
        student_id: str,
        category: str,
        dates: list[str],
    ) -> list[Task]:
        """聚合窗口成员任务（按归属日升序）。"""
        if not dates:
            return []
        stmt = (
            select(Task)
            .where(
                Task.family_id == family_id,
                Task.student_id == student_id,
                Task.category == category,
                Task.belong_date.in_(dates),
            )
            .order_by(Task.belong_date.asc(), Task.task_id.asc())
        )
        return list(session.scalars(stmt))

    @staticmethod
    def set_status(session: Session, task: Task, status: str) -> None:
        if status not in _TASK_STATUSES:  # 防御：非法值不应落入数据库
            raise ValueError(f"invalid task status: {status}")
        task.status = status
        session.flush()

    @staticmethod
    def set_spec_status(session: Session, task: Task, spec_status: str) -> None:
        if spec_status not in ("placeholder", "parsed", "confirmed"):
            raise ValueError(f"invalid spec_status: {spec_status}")
        task.spec_status = spec_status
        session.flush()

    @staticmethod
    def set_belong_window(
        session: Session, task: Task, *, belong_date: str, week_index: int, window_type: str
    ) -> None:
        task.belong_date = belong_date
        task.week_index = week_index
        task.window_type = window_type
        session.flush()

    @staticmethod
    def update_fields(
        session: Session,
        task: Task,
        *,
        title: str | object = _UNSET,
        grade_level: str | None | object = _UNSET,
        deadline: str | None | object = _UNSET,
    ) -> None:
        """更新可编辑字段（归属字段不可经此修改，须走改归属日端点）。"""
        if title is not _UNSET:
            task.title = title
        if grade_level is not _UNSET:
            task.grade_level = grade_level
        if deadline is not _UNSET:
            task.deadline = deadline
        session.flush()

    # —— task_contents（DATA-014） ——
    @staticmethod
    def list_contents(session: Session, task_id: str) -> list[TaskContent]:
        stmt = (
            select(TaskContent)
            .where(TaskContent.task_id == task_id)
            .order_by(TaskContent.seq.asc())
        )
        return list(session.scalars(stmt))

    @staticmethod
    def replace_contents(session: Session, task_id: str, items: list[dict]) -> None:
        """整体替换内容项（seq 从 1 重排）。items 元素已通过业务校验。"""
        session.execute(delete(TaskContent).where(TaskContent.task_id == task_id))
        session.flush()
        TaskRepo.append_contents(session, task_id, items)

    @staticmethod
    def append_contents(session: Session, task_id: str, items: list[dict]) -> None:
        """追加内容项（seq 接着现有最大值继续，不去重 —— 同学科追加 A3 语义）。"""
        current = session.scalar(
            select(func.count()).select_from(TaskContent).where(TaskContent.task_id == task_id)
        ) or 0
        seq = current + 1
        for it in items:
            session.add(
                TaskContent(
                    task_id=task_id,
                    subject=it["subject"],
                    seq=seq,
                    text=it["text"],
                )
            )
            seq += 1
        session.flush()

    # —— task_spec_sources（DATA-015） ——
    @staticmethod
    def list_sources(session: Session, task_id: str) -> list[TaskSpecSource]:
        stmt = (
            select(TaskSpecSource)
            .where(TaskSpecSource.task_id == task_id)
            .order_by(TaskSpecSource.seq.asc())
        )
        return list(session.scalars(stmt))

    @staticmethod
    def max_source_seq(session: Session, task_id: str) -> int:
        return (
            session.scalar(
                select(func.max(TaskSpecSource.seq)).where(TaskSpecSource.task_id == task_id)
            )
            or 0
        )

    @staticmethod
    def add_sources(session: Session, task_id: str, items: list[dict]) -> None:
        """追加输入源（多段；seq 接续现有最大值）。"""
        seq = TaskRepo.max_source_seq(session, task_id)
        for it in items:
            seq += 1
            session.add(
                TaskSpecSource(
                    task_id=task_id,
                    seq=seq,
                    kind=it["kind"],
                    text_content=it.get("text_content"),
                    photo_id=it.get("photo_id"),
                )
            )
        session.flush()

    # —— task_items（Deprecated 兼容桩；新链路不写入） ——
    @staticmethod
    def replace_items(session: Session, task_id: str, items: list[dict]) -> None:
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
        rows = session.execute(
            select(TaskItem.subject, TaskItem.group_no, func.count())
            .where(TaskItem.task_id == task_id)
            .group_by(TaskItem.subject, TaskItem.group_no)
        ).all()
        return {(subj, grp): cnt for subj, grp, cnt in rows}
