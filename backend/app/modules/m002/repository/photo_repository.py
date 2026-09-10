"""照片仓储（photos）—— M002 数据面唯一写入口（DATA-003 修订）。

约定（MODULE_DATA v0.4.0）：
- 全部查询强制 family_id 过滤；student 主体的"仅本人"过滤由调用方（服务层）给出 student_id。
- Repository 不自行 commit；行删除/状态变更与文件操作的生命周期一致由服务层编排。
- seq_no 为批次内服务端自增页序，(batch_id, seq_no) UNIQUE 约束兜底并发。
- 挂接/判定落聚合层：subject/group_no/suggestion_json 停写；按 group_subject_id 过滤经
  photo_subject_links 子查询。
"""
from __future__ import annotations

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.modules.m002.domain.enums import PhotoStatus
from app.modules.m002.domain.models import Photo, PhotoSubjectLink


class PhotoRepository:
    @staticmethod
    def create(
        session: Session,
        *,
        photo_id: str,
        batch_id: str,
        family_id: str,
        student_id: str,
        seq_no: int,
        kind: str,
        created_by_type: str,
        created_by_id: str,
        original_mime: str,
        original_path: str,
        normalized_path: str,
        file_size_bytes: int,
        width: int,
        height: int,
        sha256: str,
        quality_report_json: str,
    ) -> Photo:
        row = Photo(
            photo_id=photo_id,
            batch_id=batch_id,
            family_id=family_id,
            student_id=student_id,
            seq_no=seq_no,
            kind=kind,
            status=PhotoStatus.UNASSIGNED,
            created_by_type=created_by_type,
            created_by_id=created_by_id,
            original_mime=original_mime,
            original_path=original_path,
            normalized_path=normalized_path,
            file_size_bytes=file_size_bytes,
            width=width,
            height=height,
            sha256=sha256,
            quality_report_json=quality_report_json,
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def next_seq(session: Session, batch_id: str) -> int:
        """批次内下一页序（服务端自增：当前最大 + 1；D6 不接受前端页码）。"""
        current = (
            session.scalar(select(func.max(Photo.seq_no)).where(Photo.batch_id == batch_id)) or 0
        )
        return int(current) + 1

    @staticmethod
    def get_by_id(session: Session, family_id: str, photo_id: str) -> Photo | None:
        stmt = select(Photo).where(Photo.photo_id == photo_id, Photo.family_id == family_id)
        return session.scalar(stmt)

    @staticmethod
    def list_by_ids(session: Session, family_id: str, photo_ids: list[str]) -> list[Photo]:
        if not photo_ids:
            return []
        return list(
            session.scalars(
                select(Photo).where(Photo.family_id == family_id, Photo.photo_id.in_(photo_ids))
            )
        )

    @staticmethod
    def list_photos(
        session: Session,
        family_id: str,
        *,
        student_id: str | None = None,
        statuses: tuple[str, ...] | None = None,
        batch_id: str | None = None,
        task_id: str | None = None,
        kind: str | None = None,
        group_subject_id: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Photo], int]:
        conds = [Photo.family_id == family_id]
        if student_id:
            conds.append(Photo.student_id == student_id)
        if statuses:
            conds.append(Photo.status.in_(statuses))
        if batch_id:
            conds.append(Photo.batch_id == batch_id)
        if task_id:
            conds.append(Photo.task_id == task_id)
        if kind:
            conds.append(Photo.kind == kind)
        if group_subject_id:
            # 仅按“当前有效挂接”过滤（已判无效的链接不计入）
            sub = select(PhotoSubjectLink.photo_id).where(
                PhotoSubjectLink.family_id == family_id,
                PhotoSubjectLink.group_subject_id == group_subject_id,
                PhotoSubjectLink.rejected_at.is_(None),
            )
            conds.append(Photo.photo_id.in_(sub))
        total = session.scalar(select(func.count()).select_from(Photo).where(*conds)) or 0
        rows = list(
            session.scalars(
                select(Photo)
                .where(*conds)
                .order_by(Photo.created_at.desc(), Photo.seq_no.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return rows, total

    @staticmethod
    def count_by_task(
        session: Session, family_id: str, task_id: str, *, status: str | None = None
    ) -> int:
        conds = [Photo.family_id == family_id, Photo.task_id == task_id]
        if status:
            conds.append(Photo.status == status)
        return session.scalar(select(func.count()).select_from(Photo).where(*conds)) or 0

    @staticmethod
    def set_status(
        session: Session, photo: Photo, *, status: str, assigned_at: str | None = None
    ) -> None:
        photo.status = status
        if assigned_at is not None:
            photo.assigned_at = assigned_at
        session.flush()

    @staticmethod
    def set_window_task(session: Session, photo: Photo, task_id: str | None) -> None:
        """窗口级归属（仅冗余便于过滤/计数；挂接目标仍为聚合学科子任务）。"""
        if task_id and not photo.task_id:
            photo.task_id = task_id
            session.flush()

    @staticmethod
    def mark_consumed(
        session: Session, family_id: str, photo_ids: list[str], consumed_at: str
    ) -> int:
        """置 consumed_at（分析确认消费锁定，内部接口）；已消费照片不动，返回实际置位数量。"""
        if not photo_ids:
            return 0
        result = session.execute(
            update(Photo)
            .where(
                Photo.family_id == family_id,
                Photo.photo_id.in_(photo_ids),
                Photo.consumed_at.is_(None),
            )
            .values(consumed_at=consumed_at)
        )
        session.flush()
        return result.rowcount or 0

    @staticmethod
    def delete_rows(session: Session, family_id: str, photo_ids: list[str]) -> int:
        result = session.execute(
            delete(Photo).where(Photo.family_id == family_id, Photo.photo_id.in_(photo_ids))
        )
        session.flush()
        return result.rowcount or 0
