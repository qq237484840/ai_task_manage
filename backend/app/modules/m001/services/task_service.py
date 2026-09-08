"""作业任务服务（API-M001-007~010 + 内部 TaskQueryService）。

核心规则（契约 v0.1.1 / MODULE_DATA）：
- 任务+题目集在同一事务内写；Repository 不自行 commit，请求级统一提交/回滚。
- 归属校验：student_id / task 必须属于当前 family，否则 404/403（对外 404 防探测）。
- 冻结规则：仅 draft/published（且未开始上传）可改；in_progress/closed 一律 409。
- include_answers 仅在与任务同 family 的上下文返回客观题参考答案（敏感内容防外泄）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import audit_event
from app.core.times import iso_from
from app.modules.m001.models.orm import Task, TaskItem
from app.modules.m001.repositories.student_repo import StudentRepo
from app.modules.m001.repositories.task_repo import TaskRepo
from app.modules.m001.schemas.task import (
    TaskCreate,
    TaskDetailDTO,
    TaskGroupSegmentDTO,
    TaskItemOut,
    TaskItemIn,
    TaskSummaryDTO,
    TaskUpdate,
)
from app.shared.exceptions import ConflictError, NotFoundError, ValidationAppError

_EDITABLE_STATUSES = ("draft", "published")


def validate_items(items: list[TaskItemIn]) -> list[dict]:
    """题目集业务校验（CR-001 容器化）：非空、seq 从 1 连续唯一、主客观参考答案规则、
    学科作业段结构（group_no 收敛语义）。返回规范化 dict 列表（含 group_no）。"""
    if not items:
        raise ValidationAppError("任务至少需要包含 1 道题目")
    ordered = sorted(items, key=lambda i: i.seq)
    if ordered[0].seq != 1 or any(a.seq + 1 != b.seq for a, b in zip(ordered, ordered[1:])):
        raise ValidationAppError("题号 seq 必须为从 1 开始的连续整数")
    norm = [
        {
            "seq": it.seq,
            "item_type": it.item_type,
            "subject": it.subject,
            "group_no": it.group_no,
            "stem": it.stem,
            "reference_answer": it.reference_answer,  # subjective 已由 schema 置空
        }
        for it in ordered
    ]
    _validate_group_structure(norm)
    return norm


def _validate_group_structure(rows: list[dict]) -> None:
    """学科作业段结构约束（CR-001 收敛语义，按 seq 升序输入）：
    - 显式分组：存在 group_no>0 时，组号必须为从 1 起的连续整数（无空洞），禁止混入 0；
    - 全部 0 = 默认单段（旧数据兼容），允许跨科目同段（无 group 区分时不做强制分组）；
    - 同一组号内 subject 必须一致（段=subject+group_no）；
    - 同组题目必须连续录入（组内题号 seq 连续，不允许跨组交错）。"""
    groups: dict[int, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["group_no"], []).append(r)

    numbers = sorted(groups)
    explicit = [n for n in numbers if n > 0]
    if explicit:
        if 0 in numbers:
            raise ValidationAppError("group_no=0（未分组）不能与显式分组混用")
        if explicit != list(range(1, explicit[-1] + 1)):
            raise ValidationAppError("学科作业段号 group_no 必须为从 1 开始的连续整数")

    for gno, items_g in groups.items():
        # 段内科目一致仅约束显式分组；group 0 为默认单段（收敛语义），允许跨科目
        if gno > 0 and len({r["subject"] for r in items_g}) > 1:
            raise ValidationAppError(f"学科作业段 {gno} 内科目不一致，请拆分到不同 group_no")

    # 组块连续性：按 seq 升序扫描，同一组再次出现且中间隔了其它组 → 交错
    seen: set[int] = set()
    last: int | None = None
    for r in rows:
        if r["group_no"] != last:
            if r["group_no"] in seen:
                raise ValidationAppError("同一学科作业段必须连续录入（组内题号 seq 连续，不允许跨组交错）")
            seen.add(r["group_no"])
            last = r["group_no"]


def _deadline_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # 未标注时区视为 UTC（契约：时间一律 UTC）
    return iso_from(dt)


def build_item_out(item: TaskItem, include_answers: bool) -> TaskItemOut:
    answer = None
    if include_answers and item.item_type == "objective":
        answer = item.reference_answer  # 客观题参考答案受 include_answers 控制
    return TaskItemOut(
        seq=item.seq,
        item_type=item.item_type,  # type: ignore[arg-type]
        subject=item.subject,
        group_no=item.group_no,
        stem=item.stem,
        reference_answer=answer,
    )


def build_detail(session: Session, task: Task, *, include_answers: bool = False) -> TaskDetailDTO:
    items = TaskRepo.list_items(session, task.task_id)
    return TaskDetailDTO(
        task_id=UUID(task.task_id),
        student_id=UUID(task.student_id),
        title=task.title,
        subject=task.subject,
        grade_level=task.grade_level,
        content=task.content,
        status=task.status,  # type: ignore[arg-type]
        deadline=task.deadline,
        created_at=task.created_at,
        updated_at=task.updated_at,
        items=[build_item_out(i, include_answers) for i in items],
    )


class TaskService:
    """REST 任务业务：创建/列表/详情/更新。

    ACR-001 双主体：scope_student_id=None（family 主体，可操作本家任意学生）；
    student 主体必须传 scope_student_id=本人，越权/不存在统一 NotFoundError(404)。
    """

    @staticmethod
    def create(
        session: Session, family_id: str, data: TaskCreate, *, scope_student_id: str | None = None
    ) -> TaskDetailDTO:
        target_student_id = str(data.student_id)
        # 1) 学生档案归属校验 + 学生主体仅本人（404 防探测）
        if StudentRepo.get_with_school(session, family_id, target_student_id) is None:
            raise NotFoundError("学生档案不存在")
        if scope_student_id is not None and scope_student_id != target_student_id:
            raise NotFoundError("学生档案不存在")
        # 2) 题目集校验
        norm_items = validate_items(data.items)
        # 3) 单事务写入任务(draft) + 题目集
        task = TaskRepo.create(
            session,
            family_id=family_id,
            student_id=target_student_id,
            title=data.title,
            subject=data.subject,
            grade_level=data.grade_level,
            content=data.content,
            deadline=_deadline_iso(data.deadline),
        )
        TaskRepo.replace_items(session, task.task_id, norm_items)
        audit_event("task_created", family_id=family_id, task_id=task.task_id)  # 不含参考答案
        return build_detail(session, task)

    @staticmethod
    def list(
        session: Session,
        family_id: str,
        *,
        status: str | None = None,
        student_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
        scope_student_id: str | None = None,
    ) -> tuple[list[TaskSummaryDTO], int]:
        # 学生主体：显式查询他人 → 404；否则强制仅本人
        if scope_student_id is not None:
            if student_id is not None and student_id != scope_student_id:
                raise NotFoundError("任务不存在")
            student_id = scope_student_id
        rows, total = TaskRepo.list_tasks(
            session,
            family_id,
            status=status,
            student_id=student_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        names = StudentRepo.get_names(session, family_id, [r.student_id for r in rows])
        summaries = []
        for r in rows:
            items = TaskRepo.list_items(session, r.task_id)
            summaries.append(
                TaskSummaryDTO(
                    task_id=UUID(r.task_id),
                    student_id=UUID(r.student_id),
                    student_name=names.get(r.student_id, ""),
                    title=r.title,
                    subject=r.subject,
                    grade_level=r.grade_level,
                    status=r.status,  # type: ignore[arg-type]
                    deadline=r.deadline,
                    item_count=len(items),
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
        include_answers: bool = False,
        scope_student_id: str | None = None,
    ) -> TaskDetailDTO:
        task = TaskRepo.get_by_id(session, family_id, task_id)
        if task is None:
            raise NotFoundError("任务不存在")
        if scope_student_id is not None and task.student_id != scope_student_id:
            raise NotFoundError("任务不存在")
        return build_detail(session, task, include_answers=include_answers)

    @staticmethod
    def update(
        session: Session,
        family_id: str,
        task_id: str,
        data: TaskUpdate,
        *,
        scope_student_id: str | None = None,
    ) -> TaskDetailDTO:
        task = TaskRepo.get_by_id(session, family_id, task_id)
        if task is None:
            raise NotFoundError("任务不存在")
        if scope_student_id is not None and task.student_id != scope_student_id:
            raise NotFoundError("任务不存在")
        if task.status not in _EDITABLE_STATUSES:
            raise ConflictError("任务已开始，题目/内容已冻结，仅支持关闭或重新发布")
        fields: dict = {}
        for key in ("title", "content"):
            if key in data.model_fields_set:
                fields[key] = getattr(data, key)
        if "deadline" in data.model_fields_set:
            fields["deadline"] = _deadline_iso(data.deadline)
        if fields:
            TaskRepo.update_fields(session, task, **fields)
        if "items" in data.model_fields_set:
            TaskRepo.replace_items(session, task.task_id, validate_items(data.items or []))
        if fields or "items" in data.model_fields_set:
            audit_event("task_updated", family_id=family_id, task_id=task.task_id)
        return build_detail(session, task)


class TaskQueryService:
    """内部服务接口（进程内，供 M002/M004/M005/M007；契约见 MODULE_API）。

    内部越权语义统一 PermissionDenied（由调用方在 REST 层转换为对外状态码）。
    """

    @staticmethod
    def get_task(
        session: Session, family_id: str, task_id: str, *, include_answers: bool = False
    ) -> TaskDetailDTO:
        from app.shared.exceptions import PermissionDeniedError

        task = TaskRepo.get_by_id(session, family_id, task_id)
        if task is None:
            raise PermissionDeniedError("任务不存在或无权访问")
        return build_detail(session, task, include_answers=include_answers)

    @staticmethod
    def list_tasks(
        session: Session,
        family_id: str,
        *,
        student_id: str | None = None,
        status: str | None = None,
    ) -> list[TaskDetailDTO]:
        rows, _ = TaskRepo.list_tasks(session, family_id, status=status, student_id=student_id, limit=10000)
        return [build_detail(session, r) for r in rows]

    @staticmethod
    def can_accept_submission(session: Session, family_id: str, task_id: str, student_id: str) -> bool:
        """该任务对该学生当前可上传？published 可开始上传；in_progress 可继续上传。"""
        task = TaskRepo.get_by_id(session, family_id, task_id)
        if task is None or task.student_id != student_id:
            return False
        return task.status in ("published", "in_progress")

    # —— CR-001 容器化新增（M002 即用接口）——

    @staticmethod
    def get_task_groups(
        session: Session, family_id: str, task_id: str
    ) -> list[tuple[str, int]]:
        """任务内学科作业段清单 [(subject, group_no)]（按科目、组号排序）。"""
        from app.shared.exceptions import PermissionDeniedError

        task = TaskRepo.get_by_id(session, family_id, task_id)
        if task is None:
            raise PermissionDeniedError("任务不存在或无权访问")
        stats = TaskRepo.group_stats(session, task_id)
        return sorted(stats.keys())

    @staticmethod
    def get_task_group(
        session: Session,
        family_id: str,
        task_id: str,
        subject: str,
        group_no: int,
        *,
        include_answers: bool = False,
    ) -> TaskGroupSegmentDTO:
        """校验并读取任务内某学科作业段（subject+group_no）题目（CR-001 归属目标）。
        段不存在或越权 → PermissionDeniedError（不泄露存在性）。"""
        from app.shared.exceptions import PermissionDeniedError

        task = TaskRepo.get_by_id(session, family_id, task_id)
        if task is None:
            raise PermissionDeniedError("任务不存在或无权访问")
        rows = TaskRepo.list_items_in_group(session, task_id, subject, group_no)
        if not rows:
            raise PermissionDeniedError("该学科作业段不存在")
        return TaskGroupSegmentDTO(
            task_id=UUID(task.task_id),
            student_id=UUID(task.student_id),
            title=task.title,
            subject=subject,
            group_no=group_no,
            item_count=len(rows),
            items=[build_item_out(i, include_answers) for i in rows],
        )

    @staticmethod
    def can_accept_photo(session: Session, family_id: str, task_id: str, student_id: str) -> bool:
        """CR-001/M002 归属语义：任务对该学生当前可接受归属照片。
        与 can_accept_submission 等价（published 首采；in_progress 续采；draft/closed 不可）。"""
        return TaskQueryService.can_accept_submission(session, family_id, task_id, student_id)
