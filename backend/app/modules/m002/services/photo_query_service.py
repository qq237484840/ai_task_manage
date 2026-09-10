"""照片读取服务（REST 列表/详情 + 内部消费锁定）。

边界规则（MODULE_CONTRACT）：
- 一律强制 family_id；student 会话携带 scope_student_id（"仅本人"）：
  显式参数指向他人 → 对外 404（防探测，与 M001 REST 语义一致）。
- 本地路径绝不流入对外 DTO。
- 挂接展示经 TaskClient 解析学科名（聚合层不可用时不阻断读链路，subject 置空）。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.times import now_iso
from app.modules.m002.clients.task_client import TaskClient
from app.modules.m002.domain.errors import NotFoundError
from app.modules.m002.domain.models import Photo, PhotoSubjectLink
from app.modules.m002.repository.link_repository import LinkRepository
from app.modules.m002.repository.photo_repository import PhotoRepository
from app.modules.m002.schemas import PhotoDTO
from app.modules.m002.services.dto_builders import build_photo_dto


class PhotoQueryService:
    @staticmethod
    def _scoped_student(student_id: str | None, scope_student_id: str | None) -> str | None:
        """学生会话强制本人；显式传他人 → 404（不泄露存在性）。"""
        if scope_student_id is not None:
            if student_id is not None and str(student_id) != str(scope_student_id):
                raise NotFoundError("学生档案不存在或无权访问")
            return str(scope_student_id)
        return str(student_id) if student_id else None

    @staticmethod
    def _subject_names(
        session: Session, family_id: str, links: list[PhotoSubjectLink]
    ) -> dict[str, str]:
        names: dict[str, str] = {}
        for link in links:
            gid = link.group_subject_id
            if gid in names:
                continue
            try:
                names[gid] = TaskClient.get_group_subject(session, family_id, gid).subject
            except Exception:  # noqa: BLE001 - 展示字段解析失败不阻断读链路
                continue
        return names

    @staticmethod
    def _build(session: Session, family_id: str, photo: Photo) -> PhotoDTO:
        links = LinkRepository.list_for_photo(session, photo.photo_id)
        names = PhotoQueryService._subject_names(session, family_id, links)
        return build_photo_dto(photo, links=links, subject_names=names)

    @staticmethod
    def list_photos(
        session: Session,
        family_id: str,
        *,
        scope_student_id: str | None = None,
        student_id: str | None = None,
        statuses: tuple[str, ...] | None = None,
        batch_id: str | None = None,
        task_id: str | None = None,
        kind: str | None = None,
        group_subject_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PhotoDTO], int]:
        sid = PhotoQueryService._scoped_student(student_id, scope_student_id)
        offset = (page - 1) * page_size
        rows, total = PhotoRepository.list_photos(
            session,
            family_id,
            student_id=sid,
            statuses=statuses,
            batch_id=batch_id,
            task_id=task_id,
            kind=kind,
            group_subject_id=group_subject_id,
            offset=offset,
            limit=page_size,
        )
        return [PhotoQueryService._build(session, family_id, r) for r in rows], total

    @staticmethod
    def get_photo(
        session: Session,
        family_id: str,
        photo_id: str,
        *,
        scope_student_id: str | None = None,
    ) -> PhotoDTO:
        row = PhotoRepository.get_by_id(session, family_id, photo_id)
        if row is None:
            raise NotFoundError("照片不存在或无权访问")
        if scope_student_id is not None and str(row.student_id) != str(scope_student_id):
            raise NotFoundError("照片不存在或无权访问")
        return PhotoQueryService._build(session, family_id, row)

    @staticmethod
    def count_by_task(session: Session, family_id: str, task_id: str) -> int:
        return PhotoRepository.count_by_task(session, family_id, task_id)

    @staticmethod
    def mark_consumed(
        session: Session,
        family_id: str,
        photo_ids: list[str],
        *,
        consumed_at: str | None = None,
    ) -> int:
        """分析确认消费锁定（内部接口）：置 consumed_at；返回实际置位数。"""
        ts = consumed_at or now_iso()
        return PhotoRepository.mark_consumed(session, family_id, photo_ids, ts)
