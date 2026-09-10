"""照片↔聚合学科子任务挂接仓储（photo_subject_links，DATA-016）。

- 幂等：UNIQUE(photo_id, group_subject_id)；get_or_create 先查后建（同会话内）。
- 全部查询强制 family_id 过滤；Repository 不自行 commit。
"""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.modules.m002.domain.enums import LinkSource
from app.modules.m002.domain.models import PhotoSubjectLink


class LinkRepository:
    @staticmethod
    def get_by_id(session: Session, family_id: str, link_id: str) -> PhotoSubjectLink | None:
        return session.scalar(
            select(PhotoSubjectLink).where(
                PhotoSubjectLink.link_id == link_id,
                PhotoSubjectLink.family_id == family_id,
            )
        )

    @staticmethod
    def get_by_photo_subject(
        session: Session, photo_id: str, group_subject_id: str
    ) -> PhotoSubjectLink | None:
        return session.scalar(
            select(PhotoSubjectLink).where(
                PhotoSubjectLink.photo_id == photo_id,
                PhotoSubjectLink.group_subject_id == group_subject_id,
            )
        )

    @staticmethod
    def get_or_create(
        session: Session,
        *,
        photo_id: str,
        family_id: str,
        group_subject_id: str,
        source: str = LinkSource.AI,
        confidence: float | None = None,
    ) -> tuple[PhotoSubjectLink, bool]:
        """幂等建链：已存在则复用（不覆盖 confirmed/rejected 状态），返回 (row, created)。"""
        existing = LinkRepository.get_by_photo_subject(session, photo_id, group_subject_id)
        if existing is not None:
            return existing, False
        row = PhotoSubjectLink(
            photo_id=photo_id,
            family_id=family_id,
            group_subject_id=group_subject_id,
            source=source,
            confidence=confidence,
        )
        session.add(row)
        session.flush()
        return row, True

    @staticmethod
    def list_for_photo(session: Session, photo_id: str) -> list[PhotoSubjectLink]:
        return list(
            session.scalars(
                select(PhotoSubjectLink)
                .where(PhotoSubjectLink.photo_id == photo_id)
                .order_by(PhotoSubjectLink.created_at.asc(), PhotoSubjectLink.link_id.asc())
            )
        )

    @staticmethod
    def list_for_photos(session: Session, photo_ids: list[str]) -> list[PhotoSubjectLink]:
        if not photo_ids:
            return []
        return list(
            session.scalars(
                select(PhotoSubjectLink)
                .where(PhotoSubjectLink.photo_id.in_(photo_ids))
                .order_by(PhotoSubjectLink.photo_id.asc(), PhotoSubjectLink.created_at.asc())
            )
        )

    @staticmethod
    def has_active_link(session: Session, photo_id: str) -> bool:
        """是否存在有效挂接（未判无效）；用于异步建议幂等（rejected-only 允许重试）。"""
        count = session.scalar(
            select(func.count())
            .select_from(PhotoSubjectLink)
            .where(
                PhotoSubjectLink.photo_id == photo_id,
                PhotoSubjectLink.rejected_at.is_(None),
            )
        )
        return bool(count)

    @staticmethod
    def list_active_for_photos(
        session: Session, photo_ids: list[str]
    ) -> list[PhotoSubjectLink]:
        if not photo_ids:
            return []
        return list(
            session.scalars(
                select(PhotoSubjectLink).where(
                    PhotoSubjectLink.photo_id.in_(photo_ids),
                    PhotoSubjectLink.rejected_at.is_(None),
                )
            )
        )

    @staticmethod
    def list_confirmed_for_subject(
        session: Session, family_id: str, group_subject_id: str
    ) -> list[PhotoSubjectLink]:
        return list(
            session.scalars(
                select(PhotoSubjectLink).where(
                    PhotoSubjectLink.family_id == family_id,
                    PhotoSubjectLink.group_subject_id == group_subject_id,
                    PhotoSubjectLink.confirmed_at.is_not(None),
                )
            )
        )

    @staticmethod
    def count_confirmed_for_subject(
        session: Session, family_id: str, group_subject_id: str
    ) -> int:
        return (
            session.scalar(
                select(func.count())
                .select_from(PhotoSubjectLink)
                .where(
                    PhotoSubjectLink.family_id == family_id,
                    PhotoSubjectLink.group_subject_id == group_subject_id,
                    PhotoSubjectLink.confirmed_at.is_not(None),
                )
            )
            or 0
        )

    @staticmethod
    def list_confirmed_for_subjects(
        session: Session, family_id: str, group_subject_ids: list[str]
    ) -> list[PhotoSubjectLink]:
        if not group_subject_ids:
            return []
        return list(
            session.scalars(
                select(PhotoSubjectLink).where(
                    PhotoSubjectLink.family_id == family_id,
                    PhotoSubjectLink.group_subject_id.in_(group_subject_ids),
                    PhotoSubjectLink.confirmed_at.is_not(None),
                )
            )
        )

    @staticmethod
    def confirm(session: Session, link: PhotoSubjectLink, confirmed_at: str) -> None:
        link.confirmed_at = confirmed_at
        link.rejected_at = None
        session.flush()

    @staticmethod
    def reject(session: Session, link: PhotoSubjectLink, rejected_at: str) -> None:
        link.rejected_at = rejected_at
        link.confirmed_at = None
        session.flush()

    @staticmethod
    def delete_for_photos(session: Session, family_id: str, photo_ids: list[str]) -> int:
        """随照片删除级联清理挂接行（先删子表避免 FK 约束失败）。"""
        if not photo_ids:
            return 0
        result = session.execute(
            delete(PhotoSubjectLink).where(
                PhotoSubjectLink.family_id == family_id,
                PhotoSubjectLink.photo_id.in_(photo_ids),
            )
        )
        session.flush()
        return result.rowcount or 0
