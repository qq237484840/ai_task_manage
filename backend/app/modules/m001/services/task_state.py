"""任务状态机唯一实现（契约 task.status_flow：draft→published→in_progress→closed）。

合法迁移（MODULE_DESIGN）：
    draft      --publish----------------------------------> published
    published  --(首传, mark_in_progress, M002 调用)-----> in_progress
    published  --close-----------------------------------> closed
    in_progress--close-----------------------------------> closed
    closed     --reopen----------------------------------> published
非法边一律 InvalidTransitionError(409)。状态变更写审计（who=family / from / to / when），
不含任务内容（DEVELOPMENT_GUIDE §7）。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import audit_event
from app.modules.m001.repositories.task_repo import TaskRepo
from app.shared.exceptions import ConflictError, InvalidTransitionError, NotFoundError, PermissionDeniedError

# action -> {from_status: to_status}
_TRANSITIONS: dict[str, dict[str, str]] = {
    "publish": {"draft": "published"},
    "close": {"published": "closed", "in_progress": "closed"},
    "reopen": {"closed": "published"},
}


class TaskStateService:
    """任务状态机（REST 推进 + M002 首传 mark_in_progress 的唯一出口）。"""

    @staticmethod
    def transition(
        session: Session,
        family_id: str,
        task_id: str,
        action: str,
        *,
        scope_student_id: str | None = None,
    ) -> tuple[str, str]:
        task = TaskRepo.get_by_id(session, family_id, task_id)
        if task is None:
            raise NotFoundError("任务不存在")
        if scope_student_id is not None and task.student_id != scope_student_id:
            raise NotFoundError("任务不存在")
        allowed = _TRANSITIONS.get(action)
        if allowed is None:
            raise InvalidTransitionError(f"未知状态动作: {action}")
        if task.status not in allowed:
            raise InvalidTransitionError(f"当前状态 {task.status} 不允许执行 {action}")
        new_status = allowed[task.status]
        TaskRepo.set_status(session, task, new_status)
        audit_event(
            "task_status_changed",
            family_id=family_id,
            task_id=task_id,
            detail=f"status {task.status}->{new_status} action={action}",
        )
        return task_id, new_status

    @staticmethod
    def mark_in_progress(session: Session, family_id: str, task_id: str) -> tuple[str, str]:
        """首次有效上传后由 M002 调用推进 published→in_progress；重复调用幂等。"""
        task = TaskRepo.get_by_id(session, family_id, task_id)
        if task is None:
            raise PermissionDeniedError("任务不存在或无权访问")
        if task.status == "in_progress":
            return task_id, task.status  # 幂等
        if task.status != "published":
            raise ConflictError(f"任务状态 {task.status} 无法开始上传（需先发布）")
        TaskRepo.set_status(session, task, "in_progress")
        audit_event("task_marked_in_progress", family_id=family_id, task_id=task_id)
        return task_id, task.status
