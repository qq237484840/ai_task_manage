"""家庭会话认证与越权语义（契约 Security / MODULE_DESIGN）。

- Bearer token → sha256 查 auth_sessions（库中仅存哈希）→ 过期/无效 = 401。
- 家庭数据隔离：AuthContext.family_id 注入后，Repository/Service 强制按其过滤（schools 公共只读例外）。
- 登录防爆破：失败计数 + 渐进退避（单进程内存实现，V1 本地单机场景），超限锁定返回 403。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import audit_event
from app.core.times import iso_plus, now_iso
from app.shared.exceptions import ConflictError, PermissionDeniedError, UnauthorizedError
from app.shared.security import hash_token

# 登录防爆破（进程内）。单进程部署（ASM-010）下语义充分；多进程需外移。
_LOCKED: dict[str, dict] = {}  # login_name -> {count, locked_until}


@dataclass(frozen=True)
class AuthContext:
    family_id: str
    session_id: str
    login_name: str | None = None
    display_name: str | None = None


def resolve_auth(session_factory, credentials: str | None, *, lock_minutes: int = 5) -> AuthContext:
    """从 Bearer 原文解析当前家庭会话（无效 → 401）。"""
    from app.modules.m001.repositories.account_repo import AccountRepo

    if not credentials:
        raise UnauthorizedError("未登录或会话已失效，请重新登录")
    token_hash = hash_token(credentials)
    with session_factory() as session:
        row = AccountRepo.get_session_by_token_hash(session, token_hash)
        if row is None:
            raise UnauthorizedError("未登录或会话已失效，请重新登录")
        if now_iso() > row.expires_at:
            AccountRepo.delete_session(session, row.session_id)
            session.commit()
            raise UnauthorizedError("会话已过期，请重新登录")
        return AuthContext(
            family_id=row.family_id,
            session_id=row.session_id,
            login_name=row.family_login_name,
            display_name=row.family_display_name,
        )


def consume_login_failure(login_name: str, *, max_failures: int = 5, lock_minutes: int = 5) -> None:
    """记录一次失败；达到阈值后按秒退避（渐进），调用方对锁定账号返回 403。"""
    rec = _LOCKED.setdefault(login_name, {"count": 0, "locked_until": None})
    rec["count"] = rec.get("count", 0) + 1
    if rec["count"] >= max_failures:
        rec["locked_until"] = iso_plus(minutes=lock_minutes)
        audit_event("login_locked", detail=f"login locked after failures; login={login_name!r}")
        raise PermissionDeniedError("失败次数过多，账号已临时锁定，请稍后再试")


def check_login_blocked(login_name: str) -> None:
    rec = _LOCKED.get(login_name)
    if rec and rec.get("locked_until") and now_iso() < rec["locked_until"]:
        raise PermissionDeniedError("账号已临时锁定，请稍后再试")


def clear_login_failures(login_name: str) -> None:
    _LOCKED.pop(login_name, None)


def register_session(
    session_factory, family_id: str, *, session_ttl_days: int = 30, login_name: str | None = None
) -> tuple[str, str]:
    """签发会话：token 原文仅此一次返回；库中只存哈希。返回 (token, expires_at)。"""
    from app.modules.m001.repositories.account_repo import AccountRepo
    from app.shared.security import new_session_token

    token = new_session_token()
    expires_at = iso_plus(days=session_ttl_days)
    with session_factory() as session:
        AccountRepo.create_session(session, family_id=family_id, token_hash=hash_token(token), expires_at=expires_at)
        session.commit()
    return token, expires_at
