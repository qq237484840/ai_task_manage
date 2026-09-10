"""API-M002-001 创建上传批次。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session
from app.modules.m002.config import M002Settings, get_m002_settings
from app.modules.m002.schemas import BatchCreateIn, BatchOut
from app.modules.m002.services.dto_builders import build_batch_out
from app.modules.m002.services.upload_service import UploadService
from app.shared.auth import AuthContext

router = APIRouter(prefix="/upload-batches", tags=["M002 上传批次"])


@router.post("", response_model=BatchOut, status_code=201)
def create_batch(
    payload: BatchCreateIn,
    db: Session = Depends(get_session),
    ctx: AuthContext = Depends(current_context),
    settings: M002Settings = Depends(get_m002_settings),
):
    svc = UploadService(settings)
    subject_type, subject_id = ("student", ctx.student_id) if ctx.is_student else ("family", ctx.family_id)
    row = svc.create_batch(
        db,
        ctx.family_id,
        scope_student_id=ctx.student_id,
        student_id=str(payload.student_id) if payload.student_id else None,
        subject_type=subject_type,
        subject_id=subject_id,
        kind=payload.kind,
    )
    return build_batch_out(row)
