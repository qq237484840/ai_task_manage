"""学生子账号业务（ACR-001：开通/停用/改密；家长操作，学生档案必须属本家庭）。

口令：scrypt 与家庭一致（复用 app.shared.security）；学生口令允许弱口令，
但开通/改密响应带 password_warning 提示（ACR：学生弱口令提示）。
审计只记 student_id（学生姓名等未成年人信息不入日志）。
"""
from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import audit_event
from app.modules.m001.models.orm import StudentAccount
from app.modules.m001.repositories.account_repo import AccountRepo
from app.modules.m001.repositories.student_repo import StudentRepo
from app.modules.m001.schemas.student_account import (
    StudentAccountCreate,
    StudentAccountCreateResponse,
    StudentAccountDTO,
    StudentAccountUpdate,
)
from app.shared.exceptions import NotFoundError
from app.shared.security import hash_password


def _weak_password_hint(password: str) -> str | None:
    if len(password) < 8 or not (re.search(r"[A-Za-z]", password) and re.search(r"[0-9]", password)):
        return "口令强度较弱，建议至少 8 位且同时包含字母与数字"
    return None


def _dto(acc: StudentAccount) -> StudentAccountDTO:
    return StudentAccountDTO(
        student_id=UUID(acc.student_id),
        login_name=acc.login_name,
        status=acc.status,
        created_at=acc.created_at,
        updated_at=acc.updated_at,
    )


class StudentAccountService:
    """学生子账号 REST 业务（ACR-001 新增端点）。全部要求 family 主体（router 层已拦 student）。"""

    @staticmethod
    def open(
        session: Session, family_id: str, student_id: str, data: StudentAccountCreate, *, n: int, r: int, p: int
    ) -> StudentAccountCreateResponse:
        # 学生档案归属校验（404 防探测）
        if StudentRepo.get_with_school(session, family_id, student_id) is None:
            raise NotFoundError("学生档案不存在")
        acc = AccountRepo.create_student_account(
            session,
            family_id=family_id,
            student_id=student_id,
            login_name=data.login_name,
            password_hash=hash_password(data.password, n=n, r=r, p=p),
        )
        audit_event("student_account_opened", family_id=family_id, student_id=student_id)
        warning = _weak_password_hint(data.password)
        return StudentAccountCreateResponse(**_dto(acc).model_dump(), password_warning=warning)

    @staticmethod
    def update(
        session: Session,
        family_id: str,
        student_id: str,
        data: StudentAccountUpdate,
        *,
        n: int,
        r: int,
        p: int,
    ) -> StudentAccountCreateResponse:
        # 学生档案归属 + 子账号存在性（404 防探测，二者缺一即 404）
        if StudentRepo.get_with_school(session, family_id, student_id) is None:
            raise NotFoundError("学生账号不存在")
        acc = AccountRepo.get_student_account_in_family(session, family_id, student_id)
        if acc is None:
            raise NotFoundError("学生账号不存在")
        password_hash = None
        warning = None
        if data.password is not None:
            password_hash = hash_password(data.password, n=n, r=r, p=p)
            warning = _weak_password_hint(data.password)
        AccountRepo.update_student_account(session, acc, status=data.status, password_hash=password_hash)
        audit_event(
            "student_account_updated",
            family_id=family_id,
            student_id=student_id,
            detail=f"status={data.status or 'unchanged'}",
        )
        return StudentAccountCreateResponse(**_dto(acc).model_dump(), password_warning=warning)
