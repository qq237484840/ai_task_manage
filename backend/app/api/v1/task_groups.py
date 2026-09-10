"""M001 聚合任务端点（契约 v0.2.0）：
- API-M001-019 `GET /api/v1/task-groups`（聚合任务列表）
- API-M001-020 `GET /api/v1/task-groups/{group_id}`（聚合任务详情）

薄端点：业务下沉 `TaskQueryService`（事实层 + 聚合层读接口）。
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session, get_window_resolver
from app.modules.m001.schemas.task_group import (
    TaskGroupDTO,
    TaskGroupListResponse,
)
from app.modules.m001.services.task_service import TaskQueryService
from app.modules.m001.services.window_resolver import DefaultWindowResolver
from app.shared.auth import AuthContext

router = APIRouter(prefix="/task-groups", tags=["task-groups"])


def _scope(ctx: AuthContext) -> str | None:
    return ctx.student_id if ctx.is_student else None


@router.get("", response_model=TaskGroupListResponse)
def list_task_groups(
    student_id: str | None = Query(default=None, max_length=36),
    week_index: int | None = Query(default=None, ge=1),
    window_type: Literal["day", "weekend", "holiday"] | None = None,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
    resolver: DefaultWindowResolver = Depends(get_window_resolver),
):
    scoped = _scope(ctx)
    if scoped is not None:
        student_id = scoped  # student 主体仅本人
    items = TaskQueryService.list_groups(
        session,
        ctx.family_id,
        student_id=student_id,
        week_index=week_index,
        window_type=window_type,
        resolver=resolver,
    )
    total = len(items)
    return TaskGroupListResponse(items=items, page=1, page_size=max(total, 1), total=total)


@router.get("/{group_id}", response_model=TaskGroupDTO)
def task_group_detail(
    group_id: str,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    return TaskQueryService.get_group(session, ctx.family_id, group_id)
