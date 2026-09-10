"""API-M002-002 上传作业照片 / API-M002-003 列表 / API-M002-004 受控取图。"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session
from app.core.logging import audit_event
from app.modules.m002.api.content import photo_content_response
from app.modules.m002.config import M002Settings, get_m002_settings
from app.modules.m002.domain.errors import NotFoundError
from app.modules.m002.repository.photo_repository import PhotoRepository
from app.modules.m002.schemas import (
    BatchKindValue,
    PhotoDTO,
    PhotoListResponse,
    PhotoStatusValue,
    UploadPhotoOut,
)
from app.modules.m002.services.dto_builders import build_upload_out
from app.modules.m002.services.image_store import ImageStore
from app.modules.m002.services.photo_query_service import PhotoQueryService
from app.modules.m002.services.upload_service import UploadService
from app.shared.auth import AuthContext

router = APIRouter(prefix="/photos", tags=["M002 照片"])


@router.post("", response_model=UploadPhotoOut, status_code=201)
def upload_photo(
    request: Request,
    file: UploadFile = File(...),
    batch_id: str = Form(...),
    db: Session = Depends(get_session),
    ctx: AuthContext = Depends(current_context),
    settings: M002Settings = Depends(get_m002_settings),
):
    data = file.file.read(settings.image_max_size_bytes + 1)  # 413 边界由服务判定
    subject_type, subject_id = ("student", ctx.student_id) if ctx.is_student else ("family", ctx.family_id)
    svc = UploadService(settings)
    row = svc.upload(
        db,
        ctx.family_id,
        batch_id.strip(),
        data,
        scope_student_id=ctx.student_id,
        subject_type=subject_type,
        subject_id=subject_id,
        session_factory=getattr(request.app.state, "session_factory", None),
    )
    return build_upload_out(row)


@router.get("", response_model=PhotoListResponse)
def list_photos(
    student_id: UUID | None = Query(default=None),
    status: list[PhotoStatusValue] | None = Query(default=None),
    batch_id: UUID | None = Query(default=None),
    task_id: UUID | None = Query(default=None),
    kind: BatchKindValue | None = Query(default=None),
    group_subject_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_session),
    ctx: AuthContext = Depends(current_context),
):
    items, total = PhotoQueryService.list_photos(
        db,
        ctx.family_id,
        scope_student_id=ctx.student_id,
        student_id=str(student_id) if student_id else None,
        statuses=tuple(status) if status else None,
        batch_id=str(batch_id) if batch_id else None,
        task_id=str(task_id) if task_id else None,
        kind=kind,
        group_subject_id=str(group_subject_id) if group_subject_id else None,
        page=page,
        page_size=page_size,
    )
    return PhotoListResponse(page=page, page_size=page_size, total=total, items=items)


@router.get("/{photo_id}/content")
def get_photo_content(
    request: Request,
    photo_id: str,
    kind: Literal["original", "normalized"] = Query(default="normalized"),
    db: Session = Depends(get_session),
    ctx: AuthContext = Depends(current_context),
    settings: M002Settings = Depends(get_m002_settings),
):
    row = PhotoRepository.get_by_id(db, ctx.family_id, photo_id)
    if row is None or (ctx.is_student and ctx.student_id and row.student_id != ctx.student_id):
        raise NotFoundError("照片不存在或无权访问")
    store = ImageStore(settings.image_root)
    rel = row.original_path if kind == "original" else row.normalized_path
    media_type = row.original_mime if kind == "original" else "image/jpeg"
    try:
        data = store.read(rel)
    except OSError as exc:
        raise NotFoundError("图片文件缺失") from exc
    audit_event(
        "photo_content_served",
        family_id=ctx.family_id,
        student_id=row.student_id,
        detail=f"photo={row.photo_id} kind={kind}",
    )
    return photo_content_response(request, data, media_type)
