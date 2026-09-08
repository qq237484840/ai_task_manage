"""作业任务路由（API-M001-007 创建 / 008 列表 / 009 详情 / 010 更新 / 011 状态推进）。

薄端点：参数与 DTO 映射，业务全部下沉 Service（Router 不做业务逻辑）。
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session
from app.modules.m001.schemas.task import (
    TaskCreate,
    TaskDetailDTO,
    TaskListResponse,
    TaskStatusAction,
    TaskStatusResult,
    TaskSummaryDTO,
    TaskUpdate,
)
from app.modules.m001.services.task_service import TaskService
from app.modules.m001.services.task_state import TaskStateService
from app.shared.auth import AuthContext

router = APIRouter(prefix="/tasks", tags=["tasks"])

_TASK_STATUS = Literal["draft", "published", "in_progress", "closed"]


def _scope(ctx: AuthContext) -> str | None:
    """student 主体限定本人（越权由 Service 层 404）；family 主体 None（本家任意）。"""
    return ctx.student_id if ctx.is_student else None


@router.post("", status_code=201, response_model=TaskDetailDTO)
def create_task(
    payload: TaskCreate,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    return TaskService.create(session, ctx.family_id, payload, scope_student_id=_scope(ctx))


@router.get("", response_model=TaskListResponse)
def list_tasks(
    status: _TASK_STATUS | None = None,
    student_id: str | None = Query(default=None, max_length=36),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    items, total = TaskService.list(
        session,
        ctx.family_id,
        status=status,
        student_id=student_id,
        page=page,
        page_size=page_size,
        scope_student_id=_scope(ctx),
    )
    return TaskListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{task_id}", response_model=TaskDetailDTO)
def task_detail(
    task_id: str,
    include_answers: bool = False,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    return TaskService.detail(
        session,
        ctx.family_id,
        task_id,
        include_answers=include_answers,
        scope_student_id=_scope(ctx),
    )


@router.patch("/{task_id}", response_model=TaskDetailDTO)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    return TaskService.update(session, ctx.family_id, task_id, payload, scope_student_id=_scope(ctx))


@router.post("/{task_id}/status", response_model=TaskStatusResult)
def advance_task_status(
    task_id: str,
    payload: TaskStatusAction,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    _, status = TaskStateService.transition(
        session, ctx.family_id, task_id, payload.action, scope_student_id=_scope(ctx)
    )
    return TaskStatusResult(task_id=UUID(task_id), status=status)  # type: ignore[arg-type]
