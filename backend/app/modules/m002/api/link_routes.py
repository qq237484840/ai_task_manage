"""M002 挂接建议与门控端点（API-M002-007 / API-M002-008，契约 v0.4.3）。

- API-M002-007 `GET /api/v1/photos/{photo_id}/link-suggestions`（挂接建议查询 / 重试）
- API-M002-008 `GET /api/v1/photo-gates`（窗口级门控状态查询）
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session
from app.core.ai.service import get_ai_service
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

_logger = logging.getLogger("uvicorn.error")

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
    # `CR-006` 子项 B：读取 DATA-009 暴露 AI 失败原因（按 photo.upload_request_id 过滤最近记录）
    last_attempt: dict[str, Any] | None = None
    try:
        ai_svc = get_ai_service()
        # 按 capability=photo_link_suggest 过滤，取最新一条
        from app.core.ai.records import AICallRecord
        recent = (
            db.query(AICallRecord)
            .filter(
                AICallRecord.request_id == photo.upload_request_id,
                AICallRecord.capability == "photo_link_suggest",
            )
            .order_by(AICallRecord.created_at.desc())
            .first()
        )
        if recent and (recent.status == "error" or recent.error):
            last_attempt = {"code": recent.error.code.value, "message": recent.error.message}
            _logger.info("M002 link-suggestions: last_attempt=%s", last_attempt)
    except Exception as exc:  # noqa: BLE001 - 读取 DATA-009 失败不影响主流程
        _logger.warning("读取 DATA-009 失败（%s）→ last_attempt=null", exc)
    return LinkSuggestionOut(photo_id=photo.photo_id, status=photo.status, last_attempt=last_attempt, suggestions=items)


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
