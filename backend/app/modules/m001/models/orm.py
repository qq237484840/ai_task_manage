"""M001 ORM 模型 —— 字段级权威源：MODULE_DATA.md（v0.1.1 Frozen）。

表：family_accounts / schools / students / auth_sessions / tasks / task_items。
- 所有 ID 为 UUID4 的文本存储（32 hex 无连字符风格? 统一带连字符 str(uuid4)，36 字符）。
- 时间统一 UTC ISO 字符串（core.times）。
- schools 为全局共享只读表：仅 seed 写入，运行期无写路径（ORM 层不暴露写方法）。
"""
import uuid

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.times import now_iso


def _uid() -> str:
    return str(uuid.uuid4())


class FamilyAccount(Base):
    """家庭账号（DATA-002）。"""

    __tablename__ = "family_accounts"

    family_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    login_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso, onupdate=now_iso)


class School(Base):
    """学校基础字典（DATA-011，全局共享只读，ADR-008）。"""

    __tablename__ = "schools"
    __table_args__ = (UniqueConstraint("name", "stage", name="uq_schools_name_stage"),)

    school_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    stage: Mapped[str] = mapped_column(String(16), nullable=False, default="primary")
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso, onupdate=now_iso)


class Student(Base):
    """学生档案（DATA-002）。school_id 必填关联 schools（REQ-009/ADR-008）。"""

    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_accounts.family_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    grade_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    school_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("schools.school_id"), nullable=False, index=True
    )
    relation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso, onupdate=now_iso)


class AuthSession(Base):
    """家庭登录会话（DATA-002 附属，库内仅存 token 哈希）。"""

    __tablename__ = "auth_sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_accounts.family_id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)


class Task(Base):
    """作业任务（DATA-001）。"""

    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_family_status_created", "family_id", "status", "created_at"),
    )

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_accounts.family_id"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.student_id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    grade_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    deadline: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso, onupdate=now_iso)


class TaskItem(Base):
    """题目集（DATA-001 附属，逐题建模 ADR-006）。"""

    __tablename__ = "task_items"
    __table_args__ = (UniqueConstraint("task_id", "seq", name="uq_task_items_task_seq"),)

    item_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.task_id"), nullable=False, index=True
    )
    seq: Mapped[int] = mapped_column(nullable=False)
    item_type: Mapped[str] = mapped_column(String(16), nullable=False)  # objective | subjective
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
