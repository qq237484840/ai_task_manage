"""学生档案路由（API-M001-004 创建 / 005 列表 / 006 更新）+ 子账号管理（ACR-001）。

双主体（ACR-001）：family 主体=本家任意学生；student 主体=仅本人（越权/不存在统一 404）。
子账号开通/停用/改密为家长操作（student 主体一律 403）。school_id 不存在 → 422。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session
from app.modules.m001.schemas.student import StudentCreate, StudentDTO, StudentUpdate
from app.modules.m001.schemas.student_account import (
    StudentAccountCreate,
    StudentAccountCreateResponse,
    StudentAccountUpdate,
)
from app.modules.m001.services.family_space import StudentService
from app.modules.m001.services.student_account_service import StudentAccountService
from app.shared.auth import AuthContext
from app.shared.exceptions import PermissionDeniedError

router = APIRouter(prefix="/students", tags=["students"])


def _ensure_family(ctx: AuthContext) -> None:
    """家长专属操作（创建档案/开通子账号等）：student 主体一律 403。"""
    if ctx.is_student:
        raise PermissionDeniedError("该操作仅家长账号可用")


@router.post("", status_code=201, response_model=StudentDTO)
def create_student(
    payload: StudentCreate,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    _ensure_family(ctx)
    return StudentService.create(session, ctx.family_id, payload)


@router.get("", response_model=list[StudentDTO])
def list_students(
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    scope = ctx.student_id if ctx.is_student else None
    return StudentService.list(session, ctx.family_id, scope_student_id=scope)


@router.patch("/{student_id}", response_model=StudentDTO)
def update_student(
    student_id: str,
    payload: StudentUpdate,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    scope = ctx.student_id if ctx.is_student else None
    return StudentService.update(session, ctx.family_id, student_id, payload, scope_student_id=scope)


# —— 学生子账号管理（ACR-001：家长开通 / 停用·启用·改密；仅 family 主体） ——


@router.post("/{student_id}/account", status_code=201, response_model=StudentAccountCreateResponse)
def open_student_account(
    student_id: str,
    payload: StudentAccountCreate,
    request: Request,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    _ensure_family(ctx)
    settings = request.app.state.settings
    return StudentAccountService.open(
        session,
        ctx.family_id,
        student_id,
        payload,
        n=settings.scrypt_n,
        r=settings.scrypt_r,
        p=settings.scrypt_p,
    )


@router.patch("/{student_id}/account", response_model=StudentAccountCreateResponse)
def update_student_account(
    student_id: str,
    payload: StudentAccountUpdate,
    request: Request,
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    _ensure_family(ctx)
    settings = request.app.state.settings
    return StudentAccountService.update(
        session,
        ctx.family_id,
        student_id,
        payload,
        n=settings.scrypt_n,
        r=settings.scrypt_r,
        p=settings.scrypt_p,
    )
