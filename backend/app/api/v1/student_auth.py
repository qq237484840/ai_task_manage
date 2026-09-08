"""学生子账号认证路由（ACR-001 新增：学生登录 / 登出 / 主体信息）。

两级主体 ACR-001：`/student/login` 与 `/family/login` 各自独立命名空间
（login_name 可同名不互扰；登录防爆破按 namespace 隔离，见 shared/auth.py）。
学生会话 subject_type=student 并绑定 student_id（本人数据底线，family_id 仍为
过滤底线）；登出与 family 共用 delete_session；GET /student/me 仅学生会话可用。
审计：登录成功/失败/停用/登出（不含密码与 token，学生姓名不入审计）。
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session
from app.core.logging import audit_event
from app.core.times import iso_plus
from app.modules.m001.repositories.account_repo import AccountRepo
from app.modules.m001.schemas.student import StudentDTO
from app.modules.m001.schemas.student_account import StudentLogin, StudentLoginResponse
from app.modules.m001.services.family_space import FamilySpaceService
from app.shared.auth import (
    AuthContext,
    check_login_blocked,
    clear_login_failures,
    consume_login_failure,
)
from app.shared.exceptions import PermissionDeniedError, UnauthorizedError
from app.shared.security import hash_token, new_session_token, verify_password

router = APIRouter(prefix="/student", tags=["student-auth"])


@router.post("/login", response_model=StudentLoginResponse)
def student_login(
    payload: StudentLogin,
    request: Request,
    session: Session = Depends(get_session),
):
    settings = request.app.state.settings
    check_login_blocked(payload.login_name, namespace="student")
    account, student = AccountRepo.get_student_credentials(session, payload.login_name)
    if account is None or student is None or not verify_password(payload.password, account.password_hash):
        consume_login_failure(
            payload.login_name,
            namespace="student",
            max_failures=settings.login_max_failures,
            lock_minutes=settings.login_lock_minutes,
        )
        audit_event("student_login_failed", detail=f"login={payload.login_name!r}")
        raise UnauthorizedError("登录名或密码错误")
    if account.status != "active":
        audit_event("student_login_disabled", family_id=account.family_id, student_id=account.student_id)
        raise UnauthorizedError("账号已停用，请联系家长恢复")
    clear_login_failures(payload.login_name, namespace="student")
    token = new_session_token()
    expires_at = iso_plus(days=settings.auth_session_ttl_days)
    AccountRepo.create_session(
        session,
        family_id=account.family_id,
        token_hash=hash_token(token),
        expires_at=expires_at,
        subject_type="student",
        student_id=account.student_id,
    )
    audit_event("student_login", family_id=account.family_id, student_id=account.student_id)
    return StudentLoginResponse(
        token=token,
        expires_at=expires_at,
        subject_type="student",
        student_id=UUID(account.student_id),
        student_name=student.name,
    )


@router.post("/logout", status_code=204)
def student_logout(
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    AccountRepo.delete_session(session, ctx.session_id)
    audit_event(
        "student_logout",
        family_id=ctx.family_id,
        session_id=ctx.session_id,
        student_id=ctx.student_id,
    )


@router.get("/me", response_model=StudentDTO)
def student_me(
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    """主体信息：当前学生档案。仅 student 主体可用（family 主体无"当前学生"语义）。"""
    if not ctx.is_student or not ctx.student_id:
        raise PermissionDeniedError("该接口仅学生账号可访问")
    return FamilySpaceService.get_student(session, ctx.family_id, ctx.student_id)
