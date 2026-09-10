"""M002 ORM 模型 —— 字段级权威源：MODULE_DATA.md（v0.4.0 冻结基线）。

表：upload_batches / photos / photo_subject_links / completion_analyses。
- ID 一律 UUID4 文本存储（str(uuid4)，36 字符）；时间一律 UTC ISO 字符串（core.times）。
- photos.family_id 冗余（防御纵深：读取一律按此过滤；写入须与其批次一致，服务层单点保证）。
- 入口 `kind`：upload_batches.kind 权威，photos.kind 冗余（随批次一致）。
- 归属 = photo_subject_links（N:N → task_group_subjects，ADR-013 双层模型）：
  photos.task_id 仅作窗口级归属；photos.subject/group_no/suggestion_json 废弃停写（保留列）。
- 分析 = completion_analyses（聚合子任务(学科)级；draft → confirmed，run_no 递增）。
- 数据库 FK + 应用层校验双保险（同 M001 约定）。
"""
from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.times import now_iso


def _uid() -> str:
    return str(uuid.uuid4())


class UploadBatch(Base):
    """上传批次（DATA-003 修订；一次"拍照/选图上传会话"，无状态机）。

    kind 由菜单入口决定（task_spec | homework），为权威入口标记；photos.kind 冗余一致。
    created_by_type ∈ family|student；created_by_id 为发起主体 id。
    """

    __tablename__ = "upload_batches"
    __table_args__ = (
        Index("ix_batches_family_kind_created", "family_id", "kind", "created_at"),
        Index("ix_batches_family_student_created", "family_id", "student_id", "created_at"),
        Index("ix_batches_student_created", "student_id", "created_at"),
    )

    batch_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_accounts.family_id"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.student_id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="homework")
    created_by_type: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)


class Photo(Base):
    """照片记录（DATA-003 修订；一行 = 一张通过质检的图：原始图 + 归一图）。

    状态机见 domain/enums.PhotoStatus（由 photo_subject_links 派生）。
    kind 冗余自批次；task_id 仅作窗口级归属（挂接与判定落聚合层）。
    subject/group_no/suggestion_json 为 v0.3.0 遗留列，v0.4.0 起停写（保留以兼容存量）。
    original_path/normalized_path 为受控目录内相对路径（绝不序列化到对外响应）。
    """

    __tablename__ = "photos"
    __table_args__ = (
        UniqueConstraint("batch_id", "seq_no", name="uq_photos_batch_seq"),
        Index("ix_photos_family_status_created", "family_id", "status", "created_at"),
        Index("ix_photos_family_kind_created", "family_id", "kind", "created_at"),
        Index("ix_photos_family_task", "family_id", "task_id"),
        Index("ix_photos_student_created", "student_id", "created_at"),
    )

    photo_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    batch_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("upload_batches.batch_id"), nullable=False, index=True
    )
    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_accounts.family_id"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.student_id"), nullable=False, index=True
    )
    seq_no: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="homework")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="unassigned")
    # —— 归属（先采后认）——
    task_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tasks.task_id"), nullable=True, index=True
    )
    subject: Mapped[str | None] = mapped_column(String(32), nullable=True)  # v0.3.0 遗留，停写
    group_no: Mapped[int | None] = mapped_column(Integer, nullable=True)  # v0.3.0 遗留，停写
    suggestion_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # v0.3.0 遗留，停写
    assigned_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    consumed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # —— 上传主体（同批次规则）——
    created_by_type: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # —— 文件与元数据 ——
    original_mime: Mapped[str] = mapped_column(String(32), nullable=False)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_report_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)
    updated_at: Mapped[str] = mapped_column(
        String(32), nullable=False, default=now_iso, onupdate=now_iso
    )


class PhotoSubjectLink(Base):
    """照片↔聚合学科子任务挂接（DATA-016；N:N，ADR-013 双层模型）。

    UNIQUE(photo_id, group_subject_id) 保证幂等；source ∈ ai|manual；
    confirmed_at 落位 = 该挂接被家长确认；rejected_at 落位 = 判无效（保留审计）。
    """

    __tablename__ = "photo_subject_links"
    __table_args__ = (
        UniqueConstraint("photo_id", "group_subject_id", name="uq_links_photo_subject"),
        Index("ix_links_family_photo", "family_id", "photo_id"),
        Index("ix_links_photo_confirmed", "photo_id", "confirmed_at"),
        Index("ix_links_subject_confirmed", "group_subject_id", "confirmed_at"),
    )

    link_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    photo_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("photos.photo_id"), nullable=False, index=True
    )
    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_accounts.family_id"), nullable=False, index=True
    )
    group_subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(8), nullable=False, default="ai")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    confirmed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rejected_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)
    updated_at: Mapped[str] = mapped_column(
        String(32), nullable=False, default=now_iso, onupdate=now_iso
    )


class CompletionAnalysis(Base):
    """完成分析（DATA-017；判定单元 = 聚合子任务(学科)，ADR-013）。

    draft →（家长确认）→ confirmed；重跑生成 run_no+1 新草稿（覆盖当前草稿语义）。
    conclusion ∈ 完成|部分完成|未完成|无法判断；evidence_photo_ids 为 JSON 文本。
    """

    __tablename__ = "completion_analyses"
    __table_args__ = (
        UniqueConstraint("group_subject_id", "run_no", name="uq_analysis_subject_run"),
        Index("ix_analysis_family_subject", "family_id", "group_subject_id"),
        Index("ix_analysis_family_status", "family_id", "status"),
        Index("ix_analysis_student_created", "student_id", "created_at"),
    )

    analysis_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    group_subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("family_accounts.family_id"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.student_id"), nullable=False, index=True
    )
    conclusion: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_photo_ids_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    run_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    confirmed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    confirmed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)
    updated_at: Mapped[str] = mapped_column(
        String(32), nullable=False, default=now_iso, onupdate=now_iso
    )
