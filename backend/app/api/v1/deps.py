"""Router 公共依赖：请求级 DB 会话（统一提交/回滚）+ 家庭认证上下文注入。"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.shared.auth import AuthContext, resolve_auth

_bearer = HTTPBearer(auto_error=False)


def get_session(request: Request) -> Iterator[Session]:
    """请求级会话：成功统一提交，异常统一回滚（任务+题目集同事务的保障点）。"""
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        else:
            session.commit()


def current_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthContext:
    settings = request.app.state.settings
    token = credentials.credentials if credentials else None
    return resolve_auth(
        request.app.state.session_factory,
        token,
        lock_minutes=settings.login_lock_minutes,
    )
