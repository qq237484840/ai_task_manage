"""M001 ORM 模型 —— 字段级权威源：MODULE_DATA.md（随 CHANGE-001 修订后基线）。

表：family_accounts / schools / students / student_accounts / auth_sessions / tasks / task_items。
- 所有 ID 为 UUID4 的文本存储（统一带连字符 str(uuid4)，36 字符）。
- 时间统一 UTC ISO 字符串（core.times）。
- schools 为全局共享只读表：仅 seed 写入，运行期无写路径（ORM 层不暴露写方法）。
- 两级主体（ADR-009/ACR-001）：family_accounts（家长，全家）+ student_accounts（学生子账号，仅本人）。
- 任务为多学科作业登记单容器（CR-001）：tasks.subject 可为 NULL/'mixed'（多学科登记单）；
  学科作业段 = task_items 内 (subject, group_no)，group_no 为段内序号（0=默认单段收敛语义）。
- task_items.reference_answer 保留为**非判定基准**辅助字段（ADR-010/ACR-002：判定链端到端直判）。
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


class StudentAccount(Base):
    """学生子账号（DATA-002，两级主体 ADR-009/ACR-001）。

    由家长（family 主体）为某学生档案开通；login_name 全局唯一（登录时不携带家庭上下文）；
    口令 scrypt 存储同 FamilyAccount；status: active|disabled（disabled 不可登录）。
    """

    __tablename__ = "student_accounts"

    student_account_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_accounts.family_id"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.student_id"), nullable=False, unique=True, index=True
    )
    login_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso, onupdate=now_iso)


class AuthSession(Base):
    """登录会话（DATA-002 附属，库内仅存 token 哈希；两级主体 ACR-001）。

    subject_type: family（家长，family_id 即账号）/ student（学生子账号，family_id=所属家庭，
    额外绑定 student_id）。family_id 列对两类会话均非空（家庭过滤底线 + join 父账号）。
    """

    __tablename__ = "auth_sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_accounts.family_id"), nullable=False, index=True
    )
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False, default="family")
    student_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("students.student_id"), nullable=True, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)


class Task(Base):
    """作业登记单（DATA-001，任务=多学科容器 CR-001）。

    subject 语义放宽：可空（NULL=未标注/不适用）或 'mixed'（多学科混合登记单）；
    学科作业段见 task_items.subject + group_no。
    """

    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_family_status_created", "family_id", "status", "created_at"),
        Index("ix_tasks_family_student_created", "family_id", "student_id", "created_at"),
    )

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_accounts.family_id"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.student_id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(32), nullable=True)
    grade_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    deadline: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso, onupdate=now_iso)


class TaskItem(Base):
    """题目（DATA-001 附属；多学科登记单容器 CR-001，逐题建模）。

    group_no：学科作业段序号。收敛语义：未显式分组时全为 0（单段/旧数据兼容）；
    显式多段时组号从 1 起连续（每段 (subject, group_no) 内 subject 一致）。
    reference_answer：**非判定基准**辅助字段（ADR-010：判定链端到端直判，不依赖参考答案）。
    """

    __tablename__ = "task_items"
    __table_args__ = (
        UniqueConstraint("task_id", "seq", name="uq_task_items_task_seq"),
        Index("ix_task_items_group", "task_id", "subject", "group_no"),
    )

    item_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.task_id"), nullable=False, index=True
    )
    seq: Mapped[int] = mapped_column(nullable=False)
    item_type: Mapped[str] = mapped_column(String(16), nullable=False)  # objective | subjective
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    group_no: Mapped[int] = mapped_column(nullable=False, default=0)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
