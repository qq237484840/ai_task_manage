"""会话认证与越权语义（两级主体 ACR-001；契约 Security / MODULE_DESIGN）。

- Bearer token → sha256 查 auth_sessions（库中仅存哈希）→ 过期/无效 = 401。
- 主体 = AuthContext.subject_type（family|student）+ family_id：
  family 主体可操作本家任意学生；student 主体强制本人（student_id 过滤底线之外的二级校验）。
  family_id 过滤保留为底线（student 会话同样携带其所属 family_id）。
- 登录防爆破：失败计数 + 渐进退避（单进程内存实现，V1 本地单机场景），超限锁定返回 403；
  以命名空间隔离键（family:/student:），两类账号 login_name 可同名不互扰。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import audit_event
from app.core.times import iso_plus, now_iso
from app.shared.exceptions import PermissionDeniedError, UnauthorizedError
from app.shared.security import hash_token

# 登录防爆破（进程内）。单进程部署（ASM-010）下语义充分；多进程需外移。
_LOCKED: dict[str, dict] = {}  # "ns:login" -> {count, locked_until}


@dataclass(frozen=True)
class AuthContext:
    """当前主体上下文：family_id 恒有（数据隔离底线）；student_id 仅 student 主体非空。"""

    family_id: str
    session_id: str
    subject_type: str = "family"  # family | student
    student_id: str | None = None
    login_name: str | None = None
    display_name: str | None = None

    @property
    def is_student(self) -> bool:
        return self.subject_type == "student"


def _lock_key(namespace: str, login_name: str) -> str:
    return f"{namespace}:{login_name}"


def resolve_auth(session_factory, credentials: str | None, *, lock_minutes: int = 5) -> AuthContext:
    """从 Bearer 原文解析当前会话主体（无效 → 401）。"""
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
            subject_type=row.subject_type,
            student_id=row.student_id,
            login_name=row.login_name,
            display_name=row.display_name,
        )


def consume_login_failure(
    login_name: str, *, namespace: str = "family", max_failures: int = 5, lock_minutes: int = 5
) -> None:
    """记录一次失败；达到阈值后锁定，调用方对锁定账号返回 403。"""
    key = _lock_key(namespace, login_name)
    rec = _LOCKED.setdefault(key, {"count": 0, "locked_until": None})
    rec["count"] = rec.get("count", 0) + 1
    if rec["count"] >= max_failures:
        rec["locked_until"] = iso_plus(minutes=lock_minutes)
        audit_event("login_locked", detail=f"login locked after failures; ns={namespace}; login={login_name!r}")
        raise PermissionDeniedError("失败次数过多，账号已临时锁定，请稍后再试")


def check_login_blocked(login_name: str, *, namespace: str = "family") -> None:
    rec = _LOCKED.get(_lock_key(namespace, login_name))
    if rec and rec.get("locked_until") and now_iso() < rec["locked_until"]:
        raise PermissionDeniedError("账号已临时锁定，请稍后再试")


def clear_login_failures(login_name: str, *, namespace: str = "family") -> None:
    _LOCKED.pop(_lock_key(namespace, login_name), None)
