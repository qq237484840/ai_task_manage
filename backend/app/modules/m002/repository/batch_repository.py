"""上传批次仓储（upload_batches）。

写一致性：批次行随请求级会话统一提交/回滚（Repository 不自行 commit，M001 同约定）。
所有查询强制 family_id 过滤（家庭级底线）。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.m002.domain.models import Photo, UploadBatch


class BatchRepository:
    @staticmethod
    def create(
        session: Session,
        *,
        family_id: str,
        student_id: str,
        created_by_type: str,
        created_by_id: str,
        kind: str = "homework",
    ) -> UploadBatch:
        row = UploadBatch(
            family_id=family_id,
            student_id=student_id,
            kind=kind,
            created_by_type=created_by_type,
            created_by_id=created_by_id,
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def get_by_id(session: Session, family_id: str, batch_id: str) -> UploadBatch | None:
        """按归属家庭取批次（跨家庭 → None，调用方按 404 处理，防探测）。"""
        stmt = select(UploadBatch).where(
            UploadBatch.batch_id == batch_id, UploadBatch.family_id == family_id
        )
        return session.scalar(stmt)

    @staticmethod
    def count_photos(session: Session, batch_id: str) -> int:
        from sqlalchemy import func

        return (
            session.scalar(
                select(func.count()).select_from(Photo).where(Photo.batch_id == batch_id)
            )
            or 0
        )
