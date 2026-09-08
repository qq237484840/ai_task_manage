"""学生档案路由（API-M001-004 创建 / 005 列表 / 006 更新）。

越权/不存在统一对外 404（不泄露存在性）；school_id 不存在 → 422。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session
from app.modules.m001.schemas.student import StudentCreate, StudentDTO, StudentUpdate
from app.modules.m001.services.family_space import StudentService
from app.shared.auth import AuthContext

router = APIRouter(prefix="/students", tags=["students"])


@router.post("", status_code=201, response_model=StudentDTO)
def create_student(
    payload: StudentCreate,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    return StudentService.create(session, ctx.family_id, payload)


@router.get("", response_model=list[StudentDTO])
def list_students(
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    return StudentService.list(session, ctx.family_id)


@router.patch("/{student_id}", response_model=StudentDTO)
def update_student(
    student_id: str,
    payload: StudentUpdate,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    return StudentService.update(session, ctx.family_id, student_id, payload)
