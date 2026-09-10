"""M001 ORM 模型 —— 字段级权威源：MODULE_DATA.md（v0.2.0，ADR-013 双层模型）。

表：family_accounts / schools / students / student_accounts / auth_sessions /
    tasks（事实层按天）/ task_contents / task_spec_sources /
    task_groups（聚合层）/ task_group_subjects（★判定单元）/ task_items（Deprecated）。
- 所有 ID 为 UUID4 的文本存储（统一带连字符 str(uuid4)，36 字符）。
- 时间统一 UTC ISO 字符串（core.times）；`belong_date` 为 DATE（`YYYY-MM-DD`）文本。
- schools 为全局共享只读表：仅 seed 写入，运行期无写路径（ORM 层不暴露写方法）。
- 两级主体（ADR-009/ACR-001）：family_accounts（家长，全家）+ student_accounts（学生子账号，仅本人）。
- **事实层按天（ADR-013）**：`tasks` 唯一键 = `(student_id, category, belong_date)`；
  `tasks.subject`/`content` 废弃（留列不写）；`task_items`（含 group_no/reference_answer）Deprecated 留表。
- **聚合层跨天**：`task_groups`（含 `policy_version` 锁定）+ `task_group_subjects`（按学科合并的判定单元）。
"""
import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
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
    """作业任务（DATA-001 —— **事实层按天**，ADR-013）。

    只承载"哪一天（归属窗口）通过什么输入源布置了什么"，不承载判定；
    判定落聚合层 `task_group_subjects`。唯一键 = `(student_id, category, belong_date)`。
    `belong_date`/`week_index`/`window_type` 由 `WindowResolver` 于写入时计算并**固化**。
    `subject`/`content` **Deprecated**（留列不写；内容项见 `task_contents`）。
    """

    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "category", "belong_date", name="uq_tasks_student_category_belong_date"
        ),
        Index("ix_tasks_family_status_created", "family_id", "status", "created_at"),
        Index("ix_tasks_family_student_belong", "family_id", "student_id", "belong_date"),
    )

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_accounts.family_id"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.student_id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(16), nullable=False, default="school")
    belong_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    week_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    window_type: Mapped[str] = mapped_column(String(16), nullable=False, default="day")
    spec_status: Mapped[str] = mapped_column(String(16), nullable=False, default="placeholder")
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    # Deprecated（不写；学科标签移至 task_contents.subject / 聚合层 task_group_subjects.subject）
    subject: Mapped[str | None] = mapped_column(String(32), nullable=True)
    grade_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Deprecated（不再由家长录入；内容项见 task_contents）
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    deadline: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso, onupdate=now_iso)


class TaskItem(Base):
    """题目集（DATA-001 附属 —— **Deprecated**，ADR-013）。

    V1 **不再写入**；表保留以兼容旧数据与回滚（`create_all` 不删表）。
    逐题建模不再作为判定载体；`reference_answer` 随表退役（端到端直判原则由 ADR-013 继承）。
    相关段级查询（`get_task_group(s)`/`can_accept_photo`）为 deprecated 兼容桩，新链路勿用。
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


class TaskContent(Base):
    """任务内容项（DATA-014；FK `task_id`）。

    由 AI 解析草稿 + 家长确认产生；V1 只读展示，不参与挂接与判定（聚合层合并原料）。
    """

    __tablename__ = "task_contents"
    __table_args__ = (
        UniqueConstraint("task_id", "seq", name="uq_task_contents_task_seq"),
        Index("ix_task_contents_task", "task_id"),
    )

    content_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.task_id"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)


class TaskSpecSource(Base):
    """任务输入源（DATA-015；多段，图片 / 粘贴文本可混排）。

    上传时**无需填写任何内容**；`photo_id` 仅存引用（照片实体 Owner = M002，不建跨模块 FK）。
    """

    __tablename__ = "task_spec_sources"
    __table_args__ = (
        UniqueConstraint("task_id", "seq", name="uq_task_spec_sources_task_seq"),
        Index("ix_task_spec_sources_task", "task_id"),
    )

    source_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.task_id"), nullable=False, index=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # text | image
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)


class TaskGroup(Base):
    """聚合任务（DATA-012 —— **聚合层**，ADR-013）。

    成员 = 若干天 `tasks`；展示/挂接/判定/（V2）报告走同一代码路径，仅成员集合不同。
    `policy_version` = 生成时生效配置版本（锁定；追加数据不改）。
    """

    __tablename__ = "task_groups"
    __table_args__ = (
        UniqueConstraint("student_id", "category", "group_key", name="uq_task_groups_student_category_key"),
        Index("ix_task_groups_family_student", "family_id", "student_id"),
    )

    group_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_accounts.family_id"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.student_id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(16), nullable=False, default="school")
    group_key: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(32), nullable=False)
    window_type: Mapped[str] = mapped_column(String(16), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso, onupdate=now_iso)


class TaskGroupSubject(Base):
    """聚合学科子任务（DATA-013 —— **★判定单元**）。

    按 `subject` 合并聚合内各天任务的内容项；结论由 M002 计算、**经 M001 内部接口回写**
    （`TaskAggregationService.commit_conclusion`，DATA-013 唯一写入口）。
    `conclusion_status=confirmed` 后禁改归属日（契约 §F5④）。
    """

    __tablename__ = "task_group_subjects"
    __table_args__ = (
        UniqueConstraint("group_id", "subject", name="uq_task_group_subjects_group_subject"),
        Index("ix_task_group_subjects_group", "group_id"),
    )

    group_subject_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    group_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("task_groups.group_id"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    content_refs: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list[str]
    conclusion: Mapped[str | None] = mapped_column(String(16), nullable=True)
    conclusion_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso, onupdate=now_iso)
