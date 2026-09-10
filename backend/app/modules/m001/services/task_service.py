"""作业任务服务（事实层 + 聚合层 + 链路 T；契约 v0.2.0 / ADR-013）。

核心规则：
- **事实层按天**：`tasks` 唯一键 `(student_id, category, belong_date)`；同日同类型幂等归集（不新建）。
- **归属引擎**：`WindowResolver` 于写入时解析 `belong_date`/`week_index`/`window_type` 并固化。
- **链路 T**：输入源（图片/文本多段）→ AI 解析草稿（Mock 可解阻）→ `task_contents` + `spec_status`。
- **聚合层**：`ensure_group` 惰性幂等；`task_group_subjects` = ★判定单元（M002 结论经内部接口回写）。
- 写一致性：任务 + 输入源 + 内容项（+ 聚合生成）在同一请求事务内完成；Repository 不自行 commit。
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import audit_event
from app.core.times import iso_from
from app.modules.m001.models.orm import Task, TaskContent, TaskItem, TaskSpecSource
from app.modules.m001.repositories.group_repo import GroupRepo
from app.modules.m001.repositories.student_repo import StudentRepo
from app.modules.m001.repositories.task_repo import TaskRepo
from app.modules.m001.schemas.task import (
    ContentItemDTO,
    ContentItemIn,
    ParseConfirmation,
    SourceDTO,
    TaskDTO,
    TaskGroupSegmentDTO,
    TaskIngest,
    TaskItemIn,
    TaskItemOut,
    TaskSummaryDTO,
    TaskUpdate,
)
from app.modules.m001.schemas.task_group import WindowInfo
from app.modules.m001.services.aggregation_service import (
    TaskAggregationService,
    build_group_dto,
)
from app.modules.m001.services.task_group_service import TaskGroupService
from app.modules.m001.services.task_parser import ContentDraft, Parser, default_parser
from app.modules.m001.services.window_resolver import (
    DefaultWindowResolver,
    day_title,
    get_default_resolver,
)
from app.shared.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationAppError

_EDITABLE_STATUSES = ("draft", "published")
_DEPRECATED_GROUP_NO_HINT = "group_no 已废弃（ADR-013：学科作业段语义取消）"


def _deadline_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # 未标注时区视为 UTC（契约：时间一律 UTC）
    return iso_from(dt)


def validate_sources(sources) -> list[dict]:
    """输入源校验：至少 1 段、seq 从 1 连续唯一（Pydantic 已做段落内容校验）。"""
    if not sources:
        raise ValidationAppError("任务至少需要 1 段输入源")
    ordered = sorted(sources, key=lambda s: s.seq)
    if ordered[0].seq != 1 or any(a.seq + 1 != b.seq for a, b in zip(ordered, ordered[1:])):
        raise ValidationAppError("输入源 seq 必须为从 1 开始的连续整数")
    return [
        {
            "seq": s.seq,
            "kind": s.kind,
            "text_content": s.text_content,
            "photo_id": str(s.photo_id) if s.photo_id else None,
        }
        for s in ordered
    ]


def build_content_dto(row: TaskContent) -> ContentItemDTO:
    return ContentItemDTO(
        content_id=UUID(row.content_id), subject=row.subject, seq=row.seq, text=row.text
    )


def build_source_dto(row: TaskSpecSource) -> SourceDTO:
    return SourceDTO(
        source_id=UUID(row.source_id),
        seq=row.seq,
        kind=row.kind,  # type: ignore[arg-type]
        text_content=row.text_content,
        photo_id=UUID(row.photo_id) if row.photo_id else None,
    )


def build_detail(session: Session, task: Task) -> TaskDTO:
    contents = TaskRepo.list_contents(session, task.task_id)
    sources = TaskRepo.list_sources(session, task.task_id)
    return TaskDTO(
        task_id=UUID(task.task_id),
        student_id=UUID(task.student_id),
        category=task.category,
        belong_date=task.belong_date,
        week_index=task.week_index,
        window_type=task.window_type,  # type: ignore[arg-type]
        spec_status=task.spec_status,  # type: ignore[arg-type]
        title=task.title,
        grade_level=task.grade_level,
        status=task.status,  # type: ignore[arg-type]
        deadline=task.deadline,
        contents=[build_content_dto(c) for c in contents],
        sources=[build_source_dto(s) for s in sources],
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _group_by_subject(drafts: list[ContentDraft]) -> list[dict]:
    return [{"subject": d.subject, "text": d.text} for d in drafts]


def _resolve_scope_task(
    session: Session, family_id: str, task_id: str, scope_student_id: str | None
) -> Task:
    task = TaskRepo.get_by_id(session, family_id, task_id)
    if task is None:
        raise NotFoundError("任务不存在")
    if scope_student_id is not None and task.student_id != scope_student_id:
        raise NotFoundError("任务不存在")
    return task


class TaskService:
    """REST 任务业务：上传输入源 / 详情 / 列表 / 更新 / 解析确认 / 改归属日。"""

    @staticmethod
    def ingest(
        session: Session,
        family_id: str,
        data: TaskIngest,
        *,
        scope_student_id: str | None = None,
        resolver: DefaultWindowResolver | None = None,
        parser: Parser | None = None,
    ) -> TaskDTO:
        target_student_id = str(data.student_id)
        # 1) 学生档案归属校验 + student 主体仅本人（404 防探测）
        if StudentRepo.get_with_school(session, family_id, target_student_id) is None:
            raise NotFoundError("学生档案不存在")
        if scope_student_id is not None and scope_student_id != target_student_id:
            raise NotFoundError("学生档案不存在")
        # 2) 输入源校验
        norm_sources = validate_sources(data.sources)
        # 3) 归属窗口（按上传时刻解析；同日同类型幂等归集）
        resolver = resolver or get_default_resolver()
        window = resolver.resolve(datetime.now(timezone.utc))
        task = TaskRepo.get_by_day(session, target_student_id, data.category, window.belong_date)
        if task is None:
            task = TaskRepo.create(
                session,
                family_id=family_id,
                student_id=target_student_id,
                category=data.category,
                belong_date=window.belong_date,
                week_index=window.week_index,
                window_type=window.window_type,
                title=day_title(window.belong_date),
                grade_level=data.grade_level,
                deadline=None,
                spec_status="placeholder",
            )
        elif data.grade_level is not None:
            TaskRepo.update_fields(session, task, grade_level=data.grade_level)
        # 4) 输入源多段落库
        TaskRepo.add_sources(session, task.task_id, norm_sources)
        # 5) 链路 T 解析（失败/不可用 → 保持 placeholder，不阻断事实层）
        parser_fn = parser or default_parser
        drafts = parser_fn(norm_sources, session=session)
        if drafts:
            TaskRepo.append_contents(session, task.task_id, _group_by_subject(drafts))
            if task.spec_status == "placeholder":
                TaskRepo.set_spec_status(session, task, "parsed")
        # 6) 幂等聚合生成（惰性；不改已存在聚合的 policy_version）
        TaskAggregationService.ensure_group(
            session, family_id, target_student_id, data.category, window.belong_date, resolver=resolver
        )
        audit_event(
            "task_ingested",
            family_id=family_id,
            student_id=target_student_id,
            task_id=task.task_id,
            detail=f"belong_date={window.belong_date} sources={len(norm_sources)} parsed={bool(drafts)}",
        )
        return build_detail(session, task)

    @staticmethod
    def list(
        session: Session,
        family_id: str,
        *,
        status: str | None = None,
        student_id: str | None = None,
        belong_date: str | None = None,
        week_index: int | None = None,
        page: int = 1,
        page_size: int = 20,
        scope_student_id: str | None = None,
    ) -> tuple[list[TaskSummaryDTO], int]:
        if scope_student_id is not None:
            if student_id is not None and student_id != scope_student_id:
                raise NotFoundError("任务不存在")
            student_id = scope_student_id
        rows, total = TaskRepo.list_tasks(
            session,
            family_id,
            status=status,
            student_id=student_id,
            belong_date=belong_date,
            week_index=week_index,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        names = StudentRepo.get_names(session, family_id, [r.student_id for r in rows])
        summaries = []
        for r in rows:
            summaries.append(
                TaskSummaryDTO(
                    task_id=UUID(r.task_id),
                    student_id=UUID(r.student_id),
                    student_name=names.get(r.student_id, ""),
                    category=r.category,
                    belong_date=r.belong_date,
                    week_index=r.week_index,
                    window_type=r.window_type,  # type: ignore[arg-type]
                    spec_status=r.spec_status,  # type: ignore[arg-type]
                    title=r.title,
                    grade_level=r.grade_level,
                    status=r.status,  # type: ignore[arg-type]
                    deadline=r.deadline,
                    content_count=len(TaskRepo.list_contents(session, r.task_id)),
                    source_count=len(TaskRepo.list_sources(session, r.task_id)),
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
            )
        return summaries, total

    @staticmethod
    def detail(
        session: Session,
        family_id: str,
        task_id: str,
        *,
        scope_student_id: str | None = None,
    ) -> TaskDTO:
        task = _resolve_scope_task(session, family_id, task_id, scope_student_id)
        return build_detail(session, task)

    @staticmethod
    def update(
        session: Session,
        family_id: str,
        task_id: str,
        data: TaskUpdate,
        *,
        scope_student_id: str | None = None,
    ) -> TaskDTO:
        task = _resolve_scope_task(session, family_id, task_id, scope_student_id)
        if task.status not in _EDITABLE_STATUSES:
            raise ConflictError("任务已开始，内容已冻结，仅支持关闭或重新发布")
        fields: dict = {}
        if "title" in data.model_fields_set:
            fields["title"] = data.title
        if "grade_level" in data.model_fields_set:
            fields["grade_level"] = data.grade_level
        if "deadline" in data.model_fields_set:
            fields["deadline"] = _deadline_iso(data.deadline)
        if fields:
            TaskRepo.update_fields(session, task, **fields)
        if "contents" in data.model_fields_set:
            TaskRepo.replace_contents(
                session, task.task_id, _norm_content_items(data.contents or [])
            )
        if fields or "contents" in data.model_fields_set:
            audit_event("task_updated", family_id=family_id, task_id=task.task_id)
        return build_detail(session, task)

    @staticmethod
    def confirm_parse(
        session: Session,
        family_id: str,
        task_id: str,
        data: ParseConfirmation,
        *,
        scope_student_id: str | None = None,
        resolver: DefaultWindowResolver | None = None,
    ) -> TaskDTO:
        task = _resolve_scope_task(session, family_id, task_id, scope_student_id)
        new_items = None if data.contents is None else _norm_content_items(data.contents)
        if task.spec_status == "confirmed":
            if new_items is not None and new_items != _existing_items(session, task.task_id):
                raise ConflictError("任务解析已确认，内容项冲突")
            return build_detail(session, task)  # 幂等
        if new_items is not None:
            TaskRepo.replace_contents(session, task.task_id, new_items)
        TaskRepo.set_spec_status(session, task, "confirmed")
        resolver = resolver or get_default_resolver()
        TaskAggregationService.ensure_group(
            session, family_id, task.student_id, task.category, task.belong_date, resolver=resolver
        )
        source = "m002_implicit" if data.implicit else "family"
        audit_event(
            "parse_confirmed",
            family_id=family_id,
            student_id=task.student_id,
            task_id=task.task_id,
            detail=f"source={source}",
        )
        return build_detail(session, task)

    @staticmethod
    def change_belong_date(
        session: Session,
        family_id: str,
        task_id: str,
        new_belong_date: str,
        *,
        operator: str = "family",
        scope_student_id: str | None = None,
        resolver: DefaultWindowResolver | None = None,
    ) -> TaskDTO:
        """§F5 六条连锁（单事务）：重算快照 → 迁移 FK → 源聚合空则删 → 已消费拒绝 → 审计 → 回调 M002。"""
        task = _resolve_scope_task(session, family_id, task_id, scope_student_id)
        if new_belong_date == task.belong_date:
            return build_detail(session, task)  # 幂等
        resolver = resolver or get_default_resolver()
        old_window = resolver.window_for_date(date.fromisoformat(task.belong_date))
        old_group = GroupRepo.get_by_key(session, task.student_id, task.category, old_window.group_key)
        # ④ 已被完成分析消费 → 直接拒绝
        if old_group is not None and GroupRepo.count_confirmed_subjects(session, old_group.group_id) > 0:
            raise ConflictError("该作业已被完成分析消费，禁止修改归属日")
        # ① 重算快照 ② 迁移主表 FK
        new_window = resolver.window_for_date(date.fromisoformat(new_belong_date))
        TaskRepo.set_belong_window(
            session,
            task,
            belong_date=new_window.belong_date,
            week_index=new_window.week_index,
            window_type=new_window.window_type,
        )
        TaskAggregationService.ensure_group(
            session, family_id, task.student_id, task.category, new_window.belong_date, resolver=resolver
        )
        # ③ 源聚合刷新；变空则删
        if old_group is not None:
            TaskAggregationService.refresh_group(session, old_group, resolver=resolver)
            if not TaskAggregationService.member_tasks(session, old_group, resolver=resolver):
                GroupRepo.delete(session, old_group)
        # ⑥ 跨聚合迁移：回调 M002 迁移 photo_subject_links
        if old_window.group_key != new_window.group_key:
            TaskAggregationService.migrate_links_hook(
                session, family_id, task.task_id, old_window.group_key, new_window.group_key
            )
        # ⑤ 审计
        audit_event(
            "task_belong_date_changed",
            family_id=family_id,
            student_id=task.student_id,
            task_id=task.task_id,
            detail=f"{old_window.belong_date}->{new_window.belong_date} by={operator}",
        )
        return build_detail(session, task)


def _norm_content_items(items: list[ContentItemIn]) -> list[dict]:
    return [{"subject": it.subject, "text": it.text} for it in items]


def _existing_items(session: Session, task_id: str) -> list[dict]:
    return [
        {"subject": c.subject, "text": c.text} for c in TaskRepo.list_contents(session, task_id)
    ]


class TaskQueryService:
    """内部服务接口（进程内，供 M002；契约见 MODULE_API）。

    内部越权统一 `PermissionDeniedError`（REST 层转对外 404/403）。
    `TaskQueryService` 提供事实层 + 聚合层读接口；写路径聚合经 `TaskAggregationService`。
    """

    @staticmethod
    def get_task(session: Session, family_id: str, task_id: str) -> TaskDTO:
        task = TaskRepo.get_by_id(session, family_id, task_id)
        if task is None:
            raise PermissionDeniedError("任务不存在或无权访问")
        return build_detail(session, task)

    @staticmethod
    def list_tasks(
        session: Session,
        family_id: str,
        *,
        student_id: str | None = None,
        belong_date: str | None = None,
        status: str | None = None,
    ) -> list[TaskDTO]:
        rows, _ = TaskRepo.list_tasks(
            session,
            family_id,
            status=status,
            student_id=student_id,
            belong_date=belong_date,
            limit=10000,
        )
        return [build_detail(session, r) for r in rows]

    @staticmethod
    def resolve_window(
        ts: datetime, *, resolver: DefaultWindowResolver | None = None
    ) -> WindowInfo:
        """归属窗口解析（预览；纯计算，不锁配置）。"""
        return (resolver or get_default_resolver()).resolve(ts)

    @staticmethod
    def list_groups(
        session: Session,
        family_id: str,
        *,
        student_id: str | None = None,
        week_index: int | None = None,
        window_type: str | None = None,
        resolver: DefaultWindowResolver | None = None,
    ):
        return TaskGroupService.list_groups(
            session,
            family_id,
            student_id=student_id,
            week_index=week_index,
            window_type=window_type,
            resolver=resolver,
        )

    @staticmethod
    def get_group(session: Session, family_id: str, group_id: str):
        return TaskGroupService.get_group(session, family_id, group_id)

    @staticmethod
    def ensure_group(
        session: Session,
        family_id: str,
        student_id: str,
        category: str,
        belong_date: str,
        *,
        resolver: DefaultWindowResolver | None = None,
    ):
        return TaskGroupService.ensure_group(
            session,
            family_id,
            student_id=student_id,
            category=category,
            belong_date=belong_date,
            resolver=resolver,
        )

    @staticmethod
    def can_accept_submission(session: Session, family_id: str, task_id: str, student_id: str) -> bool:
        """Deprecated：任务对该学生当前可上传（published 首采 / in_progress 续采）。"""
        task = TaskRepo.get_by_id(session, family_id, task_id)
        if task is None or task.student_id != student_id:
            return False
        return task.status in ("published", "in_progress")

    # —— Deprecated 段级兼容桩（MODULE_API v0.2.0 已作废；勿在新链路使用） ——
    @staticmethod
    def get_task_groups(session: Session, family_id: str, task_id: str) -> list[tuple[str, int]]:
        task = TaskRepo.get_by_id(session, family_id, task_id)
        if task is None:
            raise PermissionDeniedError("任务不存在或无权访问")
        return sorted(TaskRepo.group_stats(session, task_id).keys())

    @staticmethod
    def get_task_group(
        session: Session, family_id: str, task_id: str, subject: str, group_no: int
    ) -> TaskGroupSegmentDTO:
        task = TaskRepo.get_by_id(session, family_id, task_id)
        if task is None:
            raise PermissionDeniedError("任务不存在或无权访问")
        rows: list[TaskItem] = TaskRepo.list_items_in_group(session, task_id, subject, group_no)
        if not rows:
            raise PermissionDeniedError("该学科作业段不存在")
        return TaskGroupSegmentDTO(
            task_id=UUID(task.task_id),
            student_id=UUID(task.student_id),
            title=task.title,
            subject=subject,
            group_no=group_no,
            item_count=len(rows),
            items=[
                TaskItemOut(
                    seq=i.seq,
                    item_type=i.item_type,  # type: ignore[arg-type]
                    subject=i.subject,
                    group_no=i.group_no,
                    stem=i.stem,
                )
                for i in rows
            ],
        )

    @staticmethod
    def can_accept_photo(session: Session, family_id: str, task_id: str, student_id: str) -> bool:
        """Deprecated：等价 `can_accept_submission`（ADR-013 起以窗口级聚合为准）。"""
        return TaskQueryService.can_accept_submission(session, family_id, task_id, student_id)


# —— Deprecated 逐题校验（task_items 退役；仅旧签名保留） ——
def validate_items(items: list[TaskItemIn]) -> list[dict]:
    return [
        {
            "seq": it.seq,
            "item_type": it.item_type,
            "subject": it.subject,
            "group_no": it.group_no,
            "stem": it.stem,
            "reference_answer": it.reference_answer,
        }
        for it in sorted(items, key=lambda i: i.seq)
    ]


def build_group_detail(session: Session, group) -> object:  # 兼容旧引用（内部）
    return build_group_dto(session, group)


__all__ = [
    "TaskService",
    "TaskQueryService",
    "validate_sources",
    "build_detail",
    "build_group_detail",
    "validate_items",
]
