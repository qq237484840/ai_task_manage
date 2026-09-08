"""账号与会话读写（family_accounts / student_accounts / auth_sessions；两级主体 ACR-001）。

主体类型：family（家长，操作全家）/ student（学生子账号，仅本人）。
login_name 命名空间：family 与 student 各自全局唯一（登录入口已按类型区分，如 /family/login 与 /student/login）。
"""  # noqa: E501

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.m001.models.orm import AuthSession, FamilyAccount, Student, StudentAccount
from app.shared.exceptions import ConflictError


@dataclass(frozen=True)
class SessionView:
    """会话 + 主体信息联合视图（供认证注入；subject 即当前登录主体）。"""

    session_id: str
    family_id: str
    expires_at: str
    subject_type: str = "family"  # family | student
    student_id: str | None = None
    login_name: str | None = None
    display_name: str | None = None


class AccountRepo:
    """家庭/学生账号与会话存储。login_name 在各自命名空间内全局唯一。"""

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
    def create_session(
        session: Session,
        *,
        family_id: str,
        token_hash: str,
        expires_at: str,
        subject_type: str = "family",
        student_id: str | None = None,
    ) -> AuthSession:
        row = AuthSession(
            family_id=family_id,
            token_hash=token_hash,
            expires_at=expires_at,
            subject_type=subject_type,
            student_id=student_id,
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def get_session_by_token_hash(session: Session, token_hash: str) -> SessionView | None:
        s = session.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
        if s is None:
            return None
        if s.subject_type == "student":
            # 学生会话：经 student_accounts 取登录名、students 取展示名（姓名）
            stu = session.get(Student, s.student_id) if s.student_id else None
            acc = (
                session.scalar(
                    select(StudentAccount).where(StudentAccount.student_id == s.student_id)
                )
                if s.student_id
                else None
            )
            return SessionView(
                session_id=s.session_id,
                family_id=s.family_id,
                expires_at=s.expires_at,
                subject_type="student",
                student_id=s.student_id,
                login_name=acc.login_name if acc else None,
                display_name=stu.name if stu else None,
            )
        # family 主体：login/display 即家庭账号信息
        fa = session.get(FamilyAccount, s.family_id)
        return SessionView(
            session_id=s.session_id,
            family_id=s.family_id,
            expires_at=s.expires_at,
            subject_type="family",
            login_name=fa.login_name if fa else None,
            display_name=fa.display_name if fa else None,
        )

    @staticmethod
    def delete_session(session: Session, session_id: str) -> None:
        row = session.get(AuthSession, session_id)
        if row is not None:
            session.delete(row)

    # —— 学生子账号（ACR-001，由家长管理） ——

    @staticmethod
    def get_student_account_by_login_name(session: Session, login_name: str) -> StudentAccount | None:
        return session.scalar(select(StudentAccount).where(StudentAccount.login_name == login_name))

    @staticmethod
    def get_student_account(session: Session, student_id: str) -> StudentAccount | None:
        """查某学生档案的子账号（跨家庭可查；权限由调用方按 family 校验）。"""
        return session.scalar(
            select(StudentAccount).where(StudentAccount.student_id == student_id)
        )

    @staticmethod
    def get_student_account_in_family(
        session: Session, family_id: str, student_id: str
    ) -> StudentAccount | None:
        """按所属家庭 + 学生档案查子账号（对外资源归属校验）。"""
        return session.scalar(
            select(StudentAccount).where(
                StudentAccount.family_id == family_id, StudentAccount.student_id == student_id
            )
        )

    @staticmethod
    def create_student_account(
        session: Session, *, family_id: str, student_id: str, login_name: str, password_hash: str
    ) -> StudentAccount:
        if AccountRepo.get_student_account_by_login_name(session, login_name) is not None:
            raise ConflictError("该学生账号登录名已被使用")
        if AccountRepo.get_student_account(session, student_id) is not None:
            raise ConflictError("该学生已有子账号")
        row = StudentAccount(
            family_id=family_id,
            student_id=student_id,
            login_name=login_name,
            password_hash=password_hash,
            status="active",
        )
        session.add(row)
        try:
            session.flush()
        except IntegrityError:
            raise ConflictError("学生子账号已存在或登录名被占用") from None
        return row

    @staticmethod
    def update_student_account(
        session: Session,
        account: StudentAccount,
        *,
        status: str | None = None,
        password_hash: str | None = None,
    ) -> None:
        if status is not None:
            account.status = status  # active | disabled
        if password_hash is not None:
            account.password_hash = password_hash
        session.flush()

    @staticmethod
    def get_student_credentials(
        session: Session, login_name: str
    ) -> tuple[StudentAccount | None, Student | None]:
        """登录时按 login_name 取子账号与其所属学生档案（含 family 归属）。"""
        acc = AccountRepo.get_student_account_by_login_name(session, login_name)
        if acc is None:
            return None, None
        return acc, session.get(Student, acc.student_id)
