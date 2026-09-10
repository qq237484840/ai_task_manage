"""M002 挂接建议与门控端点（API-M002-007 / API-M002-008，契约 v0.4.0）。

- API-M002-007 `GET /api/v1/photos/{photo_id}/link-suggestions`（挂接建议查询 / 重试）
- API-M002-008 `GET /api/v1/photo-gates`（窗口级门控状态查询）
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session
from app.modules.m002.clients.task_client import TaskClient
from app.modules.m002.config import M002Settings, get_m002_settings
from app.modules.m002.domain.errors import NotFoundError
from app.modules.m002.repository.link_repository import LinkRepository
from app.modules.m002.repository.photo_repository import PhotoRepository
from app.modules.m002.schemas import (
    GateStatusDTO,
    LinkSuggestionItemOut,
    LinkSuggestionOut,
)
from app.modules.m002.services.gate_service import GateService
from app.modules.m002.services.link_service import LinkService
from app.shared.auth import AuthContext

router = APIRouter(tags=["M002 挂接建议/门控"])


@router.get("/photos/{photo_id}/link-suggestions", response_model=LinkSuggestionOut)
def get_link_suggestions(
    photo_id: str,
    retry: bool = Query(default=False, description="true = 对未挂接照片重试 AI 建议"),
    db: Session = Depends(get_session),
    ctx: AuthContext = Depends(current_context),
    settings: M002Settings = Depends(get_m002_settings),
):
    photo = PhotoRepository.get_by_id(db, ctx.family_id, photo_id)
    if photo is None or (ctx.is_student and ctx.student_id and photo.student_id != ctx.student_id):
        raise NotFoundError("照片不存在或无权访问")
    if retry:
        LinkService.suggest_for_photo(db, ctx.family_id, photo_id, settings=settings)
        db.commit()
        photo = PhotoRepository.get_by_id(db, ctx.family_id, photo_id)

    links = [link for link in LinkRepository.list_for_photo(db, photo.photo_id) if link.rejected_at is None]
    items: list[LinkSuggestionItemOut] = []
    for link in links:
        subject = None
        try:
            subject = TaskClient.get_group_subject(db, ctx.family_id, link.group_subject_id).subject
        except Exception:  # noqa: BLE001
            subject = None
        items.append(
            LinkSuggestionItemOut(
                link_id=link.link_id,
                group_subject_id=link.group_subject_id,
                subject=subject,
                confidence=link.confidence,
                source=link.source,
                suggested_at=link.created_at,
            )
        )
    return LinkSuggestionOut(photo_id=photo.photo_id, status=photo.status, suggestions=items)


@router.get("/photo-gates", response_model=list[GateStatusDTO])
def list_photo_gates(
    student_id: UUID | None = Query(default=None),
    group_key: str | None = Query(default=None),
    db: Session = Depends(get_session),
    ctx: AuthContext = Depends(current_context),
):
    return GateService.list_gates(
        db,
        ctx.family_id,
        scope_student_id=ctx.student_id,
        student_id=str(student_id) if student_id else None,
        group_key=group_key,
    )
