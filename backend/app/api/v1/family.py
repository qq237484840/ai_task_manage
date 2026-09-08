"""家庭认证路由（API-M001-001 注册 / 002 登录 / 003 登出）。

登录防爆破：失败计数 + 渐进退避（进程内，见 shared/auth.py）；锁定期间登录返回 403。
审计：注册/登录成功/登录失败/锁定/登出（不含密码与 token）。
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.deps import current_context, get_session
from app.core.logging import audit_event
from app.core.times import iso_plus
from app.modules.m001.repositories.account_repo import AccountRepo
from app.modules.m001.schemas.family import (
    FamilyLogin,
    FamilyRegister,
    FamilyRegisterResponse,
    LoginResponse,
)
from app.shared.auth import (
    AuthContext,
    check_login_blocked,
    clear_login_failures,
    consume_login_failure,
)
from app.shared.exceptions import UnauthorizedError
from app.shared.security import hash_password, hash_token, new_session_token, verify_password

router = APIRouter(prefix="/family", tags=["family"])


@router.post("/register", status_code=201, response_model=FamilyRegisterResponse)
def register_family(payload: FamilyRegister, request: Request, session: Session = Depends(get_session)):
    settings = request.app.state.settings
    row = AccountRepo.create_family(
        session,
        login_name=payload.login_name,
        password_hash=hash_password(
            payload.password, n=settings.scrypt_n, r=settings.scrypt_r, p=settings.scrypt_p
        ),
        display_name=payload.display_name,
    )
    audit_event("family_registered", family_id=row.family_id)
    return FamilyRegisterResponse(family_id=UUID(row.family_id), display_name=row.display_name)


@router.post("/login", response_model=LoginResponse)
def family_login(payload: FamilyLogin, request: Request, session: Session = Depends(get_session)):
    settings = request.app.state.settings
    check_login_blocked(payload.login_name)
    account = AccountRepo.get_by_login_name(session, payload.login_name)
    if account is None or not verify_password(payload.password, account.password_hash):
        consume_login_failure(payload.login_name, max_failures=settings.login_max_failures, lock_minutes=settings.login_lock_minutes)
        audit_event("family_login_failed", detail=f"login={payload.login_name!r}")
        raise UnauthorizedError("登录名或密码错误")
    clear_login_failures(payload.login_name)
    token = new_session_token()
    expires_at = iso_plus(days=settings.auth_session_ttl_days)
    AccountRepo.create_session(
        session, family_id=account.family_id, token_hash=hash_token(token), expires_at=expires_at
    )
    audit_event("family_login", family_id=account.family_id)
    return LoginResponse(token=token, expires_at=expires_at)


@router.post("/logout", status_code=204)
def family_logout(
    ctx: AuthContext = Depends(current_context),
    session: Session = Depends(get_session),
):
    AccountRepo.delete_session(session, ctx.session_id)
    audit_event("family_logout", family_id=ctx.family_id, session_id=ctx.session_id)
