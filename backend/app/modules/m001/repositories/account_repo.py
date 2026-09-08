"""家庭账号与会话读写（family_accounts / auth_sessions）。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.m001.models.orm import AuthSession, FamilyAccount
from app.shared.exceptions import ConflictError


@dataclass(frozen=True)
class SessionView:
    """会话 + 家庭登录名/显示名联合视图（供认证注入）。"""

    session_id: str
    family_id: str
    expires_at: str
    family_login_name: str | None = None
    family_display_name: str | None = None


class AccountRepo:
    """家庭账号/会话存储。家庭账号即账号本身，不存在跨家庭读取问题（按 login_name 全局唯一）。"""

    @staticmethod
    def get_by_login_name(session: Session, login_name: str) -> FamilyAccount | None:
        return session.scalar(select(FamilyAccount).where(FamilyAccount.login_name == login_name))

    @staticmethod
    def get_by_id(session: Session, family_id: str) -> FamilyAccount | None:
        return session.get(FamilyAccount, family_id)

    @staticmethod
    def create_family(
        session: Session, *, login_name: str, password_hash: str, display_name: str
    ) -> FamilyAccount:
        if AccountRepo.get_by_login_name(session, login_name) is not None:
            raise ConflictError("该登录名已被注册")
        row = FamilyAccount(login_name=login_name, password_hash=password_hash, display_name=display_name)
        session.add(row)
        try:
            session.flush()
        except IntegrityError:
            raise ConflictError("该登录名已被注册") from None
        return row

    @staticmethod
    def create_session(session: Session, *, family_id: str, token_hash: str, expires_at: str) -> AuthSession:
        row = AuthSession(family_id=family_id, token_hash=token_hash, expires_at=expires_at)
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def get_session_by_token_hash(session: Session, token_hash: str) -> SessionView | None:
        stmt = (
            select(AuthSession, FamilyAccount.login_name, FamilyAccount.display_name)
            .join(FamilyAccount, AuthSession.family_id == FamilyAccount.family_id)
            .where(AuthSession.token_hash == token_hash)
        )
        row = session.execute(stmt).first()
        if row is None:
            return None
        s, login_name, display_name = row
        return SessionView(
            session_id=s.session_id,
            family_id=s.family_id,
            expires_at=s.expires_at,
            family_login_name=login_name,
            family_display_name=display_name,
        )

    @staticmethod
    def delete_session(session: Session, session_id: str) -> None:
        row = session.get(AuthSession, session_id)
        if row is not None:
            session.delete(row)
