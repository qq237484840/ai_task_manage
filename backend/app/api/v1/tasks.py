"""作业任务路由（契约 v0.2.0）：
- API-M001-007 `POST /api/v1/tasks`（上传输入源；无需填内容）
- API-M001-008 `GET  /api/v1/tasks`（列表）
- API-M001-009 `GET  /api/v1/tasks/{task_id}`（详情）
- API-M001-010 `PATCH /api/v1/tasks/{task_id}`（更新 title/grade_level/deadline + 内容项）
- API-M001-011 `POST /api/v1/tasks/{task_id}/status`（状态推进）
- API-M001-018 `POST /api/v1/tasks/{task_id}/parse-confirmation`（解析结果确认，显式/隐式）
- API-M001-021 `POST /api/v1/tasks/{task_id}/belong-date`（手工改归属日）

薄端点：参数与 DTO 映射，业务全部下沉 Service（Router 不做业务逻辑）。
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session, get_window_resolver
from app.modules.m001.schemas.task import (
    BelongDateChange,
    ParseConfirmation,
    TaskDTO,
    TaskIngest,
    TaskListResponse,
    TaskStatusAction,
    TaskStatusResult,
    TaskUpdate,
)
from app.modules.m001.services.task_service import TaskService
from app.modules.m001.services.task_state import TaskStateService
from app.modules.m001.services.window_resolver import DefaultWindowResolver
from app.shared.auth import AuthContext

router = APIRouter(prefix="/tasks", tags=["tasks"])

_TASK_STATUS = Literal["draft", "published", "in_progress", "closed"]


def _scope(ctx: AuthContext) -> str | None:
    """student 主体限定本人（越权由 Service 层 404）；family 主体 None（本家任意）。"""
    return ctx.student_id if ctx.is_student else None


@router.post("", status_code=201, response_model=TaskDTO)
def ingest_task(
    payload: TaskIngest,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
    resolver: DefaultWindowResolver = Depends(get_window_resolver),
):
    return TaskService.ingest(
        session, ctx.family_id, payload, scope_student_id=_scope(ctx), resolver=resolver
    )


@router.get("", response_model=TaskListResponse)
def list_tasks(
    status: _TASK_STATUS | None = None,
    student_id: str | None = Query(default=None, max_length=36),
    belong_date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    week_index: int | None = Query(default=None, ge=1),
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
        belong_date=belong_date,
        week_index=week_index,
        page=page,
        page_size=page_size,
        scope_student_id=_scope(ctx),
    )
    return TaskListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{task_id}", response_model=TaskDTO)
def task_detail(
    task_id: str,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    return TaskService.detail(session, ctx.family_id, task_id, scope_student_id=_scope(ctx))


@router.patch("/{task_id}", response_model=TaskDTO)
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


@router.post("/{task_id}/parse-confirmation", response_model=TaskDTO)
def confirm_parse(
    task_id: str,
    payload: ParseConfirmation,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
    resolver: DefaultWindowResolver = Depends(get_window_resolver),
):
    return TaskService.confirm_parse(
        session, ctx.family_id, task_id, payload, scope_student_id=_scope(ctx), resolver=resolver
    )


@router.post("/{task_id}/belong-date", response_model=TaskDTO)
def change_belong_date(
    task_id: str,
    payload: BelongDateChange,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
    resolver: DefaultWindowResolver = Depends(get_window_resolver),
):
    return TaskService.change_belong_date(
        session,
        ctx.family_id,
        task_id,
        payload.belong_date,
        operator="student" if ctx.is_student else "family",
        scope_student_id=_scope(ctx),
        resolver=resolver,
    )
