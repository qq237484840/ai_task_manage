"""照片撤销/删除（API-M002-006；未消费可删，已消费 409 photo_consumed）。

删除语义（MODULE_CONTRACT）：物理删 + 行删 + 审计 单操作；文件删除幂等，
失败仅记录告警（行已删则视为达成业务删除，遗留孤儿文件不入库引用，不可达）。
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.logging import audit_event
from app.modules.m002.domain.errors import NotFoundError, PhotoConsumedError
from app.modules.m002.repository.link_repository import LinkRepository
from app.modules.m002.repository.photo_repository import PhotoRepository
from app.modules.m002.services.image_store import ImageStore

logger = logging.getLogger("m002.undo")


class UndoService:
    @staticmethod
    def delete(
        session: Session,
        store: ImageStore,
        family_id: str,
        photo_id: str,
        *,
        scope_student_id: str | None = None,
        reason: str = "user_undo",
    ) -> None:
        photo = PhotoRepository.get_by_id(session, family_id, photo_id)
        if photo is None:
            raise NotFoundError("照片不存在或无权访问")
        if scope_student_id is not None and str(photo.student_id) != str(scope_student_id):
            raise NotFoundError("照片不存在或无权访问")
        if photo.consumed_at is not None:
            raise PhotoConsumedError("照片已被识别消费，不可删除")

        paths = [photo.original_path, photo.normalized_path]
        LinkRepository.delete_for_photos(session, family_id, [photo_id])
        PhotoRepository.delete_rows(session, family_id, [photo_id])
        for rel in paths:
            try:
                store.delete(rel)
            except OSError as exc:
                logger.warning(
                    "photo %s 物理文件删除失败（已删行，不可达孤儿）: %s", photo_id, exc
                )
        audit_event(
            "photo_deleted",
            family_id=family_id,
            student_id=photo.student_id,
            detail=f"photo={photo_id} reason={reason}",
        )
