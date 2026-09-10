"""API-M002-005 挂接复核（/links）/ API-M002-006 撤销清理。

- POST /photos/{photo_id}/links：accept | reject | relink（逐张复核；手工兜底保留）。
- DELETE /photos/{photo_id}：未消费可删，已消费 409 photo_consumed。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session
from app.modules.m002.clients.task_client import TaskClient
from app.modules.m002.config import M002Settings, get_m002_settings
from app.modules.m002.domain.enums import LinkAction
from app.modules.m002.schemas import LinkReviewIn, LinkReviewOut
from app.modules.m002.services.dto_builders import build_link_dto
from app.modules.m002.services.gate_service import GateService
from app.modules.m002.services.image_store import ImageStore
from app.modules.m002.services.link_service import LinkService
from app.modules.m002.services.undo_service import UndoService
from app.shared.auth import AuthContext

router = APIRouter(prefix="/photos", tags=["M002 照片挂接"])


@router.post("/{photo_id}/links", response_model=LinkReviewOut)
def review_photo_links(
    photo_id: str,
    payload: LinkReviewIn,
    db: Session = Depends(get_session),
    ctx: AuthContext = Depends(current_context),
    settings: M002Settings = Depends(get_m002_settings),
):
    photo, links = LinkService.review(
        db,
        ctx.family_id,
        photo_id,
        action=payload.action,
        link_id=str(payload.link_id) if payload.link_id else None,
        group_subject_id=str(payload.group_subject_id) if payload.group_subject_id else None,
        scope_student_id=ctx.student_id,
        settings=settings,
    )
    subject_names: dict[str, str] = {}
    confirmed_group_key: str | None = None
    for link in links:
        if link.group_subject_id in subject_names:
            continue
        try:
            ref = TaskClient.get_group_subject(db, ctx.family_id, link.group_subject_id)
            subject_names[link.group_subject_id] = ref.subject
            if link.confirmed_at and confirmed_group_key is None:
                confirmed_group_key = ref.group_key
        except Exception:  # noqa: BLE001 - 展示字段解析失败不阻断复核响应
            continue
    gate = None
    if payload.action in (LinkAction.ACCEPT, LinkAction.RELINK) and confirmed_group_key:
        try:
            gate = GateService.get_gate(
                db, ctx.family_id, student_id=photo.student_id, group_key=confirmed_group_key
            )
        except Exception:  # noqa: BLE001
            gate = None
    return LinkReviewOut(
        photo_id=photo.photo_id,
        status=photo.status,
        task_id=photo.task_id,
        links=[build_link_dto(link, subject_names.get(link.group_subject_id)) for link in links],
        gate=gate,
    )


@router.delete("/{photo_id}", status_code=204)
def delete_photo(
    photo_id: str,
    db: Session = Depends(get_session),
    ctx: AuthContext = Depends(current_context),
    settings: M002Settings = Depends(get_m002_settings),
):
    UndoService.delete(
        db,
        ImageStore(settings.image_root),
        ctx.family_id,
        photo_id,
        scope_student_id=ctx.student_id,
    )
