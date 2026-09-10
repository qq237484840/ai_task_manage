"""M002 完成分析端点（API-M002-009 ~ 011，契约 v0.4.0）。

- API-M002-009 `POST /api/v1/completion-analyses`（生成，窗口级门控前置）
- API-M002-010 `POST /api/v1/completion-analyses/{analysis_id}/confirmation`（家长确认）
- API-M002-011 `POST /api/v1/completion-analyses/{analysis_id}/rerun`（重跑，run_no 递增）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session
from app.modules.m002.clients.task_client import TaskClient
from app.modules.m002.config import M002Settings, get_m002_settings
from app.modules.m002.schemas import (
    AnalysisConfirmIn,
    AnalysisCreateIn,
    AnalysisGenerateOut,
    AnalysisItemOut,
)
from app.modules.m002.services.analysis_service import AnalysisService
from app.modules.m002.services.dto_builders import build_analysis_out
from app.shared.auth import AuthContext

router = APIRouter(tags=["M002 完成分析"])


def _subject_name(db: Session, family_id: str, group_subject_id: str) -> str | None:
    try:
        return TaskClient.get_group_subject(db, family_id, group_subject_id).subject
    except Exception:  # noqa: BLE001 - 展示字段解析失败不阻断
        return None


@router.post("/completion-analyses", response_model=AnalysisGenerateOut, status_code=201)
def generate_analyses(
    payload: AnalysisCreateIn,
    db: Session = Depends(get_session),
    ctx: AuthContext = Depends(current_context),
    settings: M002Settings = Depends(get_m002_settings),
):
    rows = AnalysisService.generate(
        db,
        ctx.family_id,
        student_id=str(payload.student_id) if payload.student_id else None,
        group_key=payload.group_key,
        scope_student_id=ctx.student_id,
        settings=settings,
    )
    return AnalysisGenerateOut(
        group_key=payload.group_key,
        items=[
            build_analysis_out(row, _subject_name(db, ctx.family_id, row.group_subject_id))
            for row in rows
        ],
    )


@router.post(
    "/completion-analyses/{analysis_id}/confirmation", response_model=AnalysisItemOut
)
def confirm_analysis(
    analysis_id: str,
    payload: AnalysisConfirmIn,
    db: Session = Depends(get_session),
    ctx: AuthContext = Depends(current_context),
):
    row = AnalysisService.confirm(
        db,
        ctx.family_id,
        analysis_id,
        confirmed_by=ctx.family_id,
        conclusion=payload.conclusion,
        scope_student_id=ctx.student_id,
    )
    return build_analysis_out(row, _subject_name(db, ctx.family_id, row.group_subject_id))


@router.post(
    "/completion-analyses/{analysis_id}/rerun", response_model=AnalysisItemOut, status_code=201
)
def rerun_analysis(
    analysis_id: str,
    db: Session = Depends(get_session),
    ctx: AuthContext = Depends(current_context),
    settings: M002Settings = Depends(get_m002_settings),
):
    row = AnalysisService.rerun(
        db,
        ctx.family_id,
        analysis_id,
        scope_student_id=ctx.student_id,
        settings=settings,
    )
    return build_analysis_out(row, _subject_name(db, ctx.family_id, row.group_subject_id))
