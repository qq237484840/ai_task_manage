"""挂接服务（API-M002-005 复核 / 007 建议 / 异步建议 / migrate_links）。

归属目标 = 聚合学科子任务（task_group_subjects，ADR-013）；N:N，UNIQUE(photo_id, group_subject_id)。
流程：
- 上传后异步建议（幂等，只处理未挂接照片；AI 失败 → 保持 unassigned，不产生脏数据）。
- 逐张复核 accept/reject/relink（手工兜底必须保留；目标不存在/越权 → 404）。
- 首条确认挂接 → 同事务调 M001 mark_in_progress（幂等）。
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.logging import audit_event
from app.core.times import now_iso
from app.modules.m002.clients.ai_client import AiPhotoInput, get_ai_client
from app.modules.m002.clients.task_client import GroupSubjectRef, TaskClient
from app.modules.m002.config import M002Settings, get_m002_settings
from app.modules.m002.domain.enums import LinkAction, LinkSource, PhotoStatus
from app.modules.m002.domain.errors import (
    AiUnavailableError,
    LinkMissingError,
    LinkStateError,
    LinkTargetMissingError,
    M001UnavailableError,
    NotFoundError,
    PhotoConsumedError,
    SubjectPhotoLimitError,
    TaskNotAcceptableError,
    ValidationAppError,
)
from app.modules.m002.domain.models import Photo, PhotoSubjectLink
from app.modules.m002.repository.link_repository import LinkRepository
from app.modules.m002.repository.photo_repository import PhotoRepository

logger = logging.getLogger("m002.link")

_ACCEPTABLE_TASK_STATUS = ("published", "in_progress")


class LinkService:
    # ---------------------------------------------------------------- 异步建议
    @staticmethod
    def suggest_for_photo(
        session: Session,
        family_id: str,
        photo_id: str,
        *,
        settings: M002Settings | None = None,
    ) -> int:
        """为单张未挂接照片生成 AI 挂接建议（幂等）。返回新建链接数。

        AI/聚合层不可用 → 0（照片保持 unassigned）；已存在有效挂接 → 跳过（重复触发不重复建链）。
        """
        s = settings or get_m002_settings()
        if not s.association_suggestion_enabled:
            return 0
        photo = PhotoRepository.get_by_id(session, family_id, photo_id)
        if photo is None or photo.consumed_at is not None:
            return 0
        if LinkRepository.has_active_link(session, photo_id):
            return 0
        try:
            subjects = TaskClient.list_group_subjects(
                session, family_id, student_id=photo.student_id
            )
        except M001UnavailableError as exc:
            logger.warning("link suggestion degraded (M001 unavailable): %s", exc)
            return 0
        scoped = [ref for ref in subjects if ref.student_id == photo.student_id]
        if not scoped:
            return 0
        photo_input = AiPhotoInput(
            photo_id=photo.photo_id,
            student_id=photo.student_id,
            kind=photo.kind,
            normalized_path=LinkService._abs_path(s, photo),
            mime=photo.original_mime,
        )
        try:
            suggestions = get_ai_client().suggest_links(session, family_id, photo_input, scoped)
        except AiUnavailableError as exc:
            logger.warning("link suggestion degraded (AI unavailable): %s", exc)
            return 0
        by_id = {ref.group_subject_id: ref for ref in scoped}
        created = 0
        for sug in suggestions[: s.association_suggestion_top_k]:
            ref = by_id.get(sug.group_subject_id)
            if ref is None or ref.student_id != photo.student_id:
                continue
            _, is_new = LinkRepository.get_or_create(
                session,
                photo_id=photo.photo_id,
                family_id=family_id,
                group_subject_id=sug.group_subject_id,
                source=LinkSource.AI,
                confidence=sug.confidence,
            )
            created += 1 if is_new else 0
        if created:
            LinkService._recompute_photo_status(session, photo)
            session.flush()
            audit_event(
                "photo_link_suggested",
                family_id=family_id,
                student_id=photo.student_id,
                detail=f"photo={photo.photo_id} suggestions={created}",
            )
        return created

    # ---------------------------------------------------------------- 复核
    @staticmethod
    def review(
        session: Session,
        family_id: str,
        photo_id: str,
        *,
        action: str,
        link_id: str | None = None,
        group_subject_id: str | None = None,
        scope_student_id: str | None = None,
        settings: M002Settings | None = None,
    ) -> tuple[Photo, list[PhotoSubjectLink]]:
        s = settings or get_m002_settings()
        if action not in LinkAction.ALL:
            raise ValidationAppError(f"未知复核动作: {action}")
        photo = PhotoRepository.get_by_id(session, family_id, photo_id)
        if photo is None:
            raise NotFoundError("照片不存在或无权访问")
        if scope_student_id is not None and str(photo.student_id) != str(scope_student_id):
            raise NotFoundError("照片不存在或无权访问")
        if photo.consumed_at is not None:
            raise PhotoConsumedError("照片已被分析消费，不可改派")

        links_before = LinkRepository.list_for_photo(session, photo_id)
        had_confirmed = any(link.confirmed_at for link in links_before)

        if action == LinkAction.ACCEPT:
            LinkService._do_accept(session, family_id, photo, link_id, group_subject_id, s)
        elif action == LinkAction.REJECT:
            LinkService._do_reject(session, family_id, photo, link_id, group_subject_id)
        else:  # RELINK
            LinkService._do_relink(session, family_id, photo, link_id, group_subject_id, s)

        LinkService._recompute_photo_status(session, photo)
        links_after = LinkRepository.list_for_photo(session, photo_id)
        now_confirmed = any(link.confirmed_at for link in links_after)
        if now_confirmed and not had_confirmed:
            LinkService._on_first_confirm(session, family_id, photo, links_after)
        session.flush()
        audit_event(
            "photo_link_reviewed",
            family_id=family_id,
            student_id=photo.student_id,
            detail=f"photo={photo_id} action={action} status={photo.status}",
        )
        return photo, LinkRepository.list_for_photo(session, photo_id)

    # ---------------------------------------------------------------- migrate_links
    @staticmethod
    def migrate_links(
        session: Session,
        family_id: str,
        *,
        student_id: str,
        old_group_key: str,
        new_group_key: str,
    ) -> int:
        """M001 反向调用的迁移钩子：窗口 key 变更时重挂已确认链接（同事务，失败整体回滚）。

        按学科 subject 对齐到新窗口对应子任务；新窗口缺该学科 → ConflictError（回滚，不丢数据）。
        """
        from app.shared.exceptions import ConflictError

        old_groups = TaskClient.list_groups(
            session, family_id, student_id=student_id, group_key=old_group_key
        )
        old_subject_by_id = {
            sub.group_subject_id: sub.subject for grp in old_groups for sub in grp.subjects
        }
        if not old_subject_by_id:
            return 0
        new_groups = TaskClient.list_groups(
            session, family_id, student_id=student_id, group_key=new_group_key
        )
        new_by_subject = {
            sub.subject: sub.group_subject_id for grp in new_groups for sub in grp.subjects
        }
        links = LinkRepository.list_confirmed_for_subjects(
            session, family_id, list(old_subject_by_id)
        )
        migrated = 0
        for link in links:
            subject = old_subject_by_id[link.group_subject_id]
            target = new_by_subject.get(subject)
            if target is None:
                raise ConflictError(f"新窗口缺少学科 {subject}，迁移中止")
            if target == link.group_subject_id:
                continue
            LinkRepository.reject(session, link, now_iso())
            new_link, _ = LinkRepository.get_or_create(
                session,
                photo_id=link.photo_id,
                family_id=family_id,
                group_subject_id=target,
                source=link.source,
                confidence=link.confidence,
            )
            LinkRepository.confirm(session, new_link, now_iso())
            migrated += 1
        return migrated

    # ---------------------------------------------------------------- 内部
    @staticmethod
    def _abs_path(settings: M002Settings, photo: Photo) -> str | None:
        try:
            from app.modules.m002.services.image_store import ImageStore

            return str(ImageStore(settings.image_root).abs_path(photo.normalized_path))
        except Exception:  # noqa: BLE001 - 路径解析失败交由 AI 层降级
            return None

    @staticmethod
    def _resolve_link(
        session: Session,
        family_id: str,
        photo: Photo,
        link_id: str | None,
        group_subject_id: str | None,
    ) -> PhotoSubjectLink:
        if link_id:
            link = LinkRepository.get_by_id(session, family_id, link_id)
            if link is None or link.photo_id != photo.photo_id:
                raise NotFoundError("挂接记录不存在")
            return link
        if group_subject_id:
            link = LinkRepository.get_by_photo_subject(session, photo.photo_id, group_subject_id)
            if link is None:
                raise NotFoundError("挂接记录不存在")
            return link
        raise LinkMissingError("缺少 link_id 或 group_subject_id")

    @staticmethod
    def _validate_target(
        session: Session,
        family_id: str,
        photo: Photo,
        group_subject_id: str,
        settings: M002Settings,
        *,
        check_limit: bool,
    ) -> GroupSubjectRef:
        try:
            ref = TaskClient.get_group_subject(session, family_id, group_subject_id)
        except (M001UnavailableError, LinkTargetMissingError, NotFoundError) as exc:
            raise LinkTargetMissingError("挂接目标不存在或无权访问") from exc
        if ref.student_id and str(ref.student_id) != str(photo.student_id):
            raise LinkTargetMissingError("挂接目标不属于该学生")
        if ref.task_status and ref.task_status not in _ACCEPTABLE_TASK_STATUS:
            raise TaskNotAcceptableError(ref.task_status)
        if check_limit:
            confirmed = LinkRepository.count_confirmed_for_subject(
                session, family_id, group_subject_id
            )
            if confirmed >= settings.association_max_photos_per_subject:
                raise SubjectPhotoLimitError(
                    f"该学科已挂接 {confirmed} 张，达上限 {settings.association_max_photos_per_subject}"
                )
        return ref

    @staticmethod
    def _do_accept(
        session: Session,
        family_id: str,
        photo: Photo,
        link_id: str | None,
        group_subject_id: str | None,
        settings: M002Settings,
    ) -> None:
        ts = now_iso()
        existing: PhotoSubjectLink | None = None
        if link_id:
            existing = LinkService._resolve_link(session, family_id, photo, link_id, None)
        elif group_subject_id:
            existing = LinkRepository.get_by_photo_subject(
                session, photo.photo_id, group_subject_id
            )
        else:
            raise LinkMissingError("accept 需要 link_id 或 group_subject_id")

        if existing is not None:
            if existing.rejected_at is not None:
                raise LinkStateError("该挂接已判无效，不可再确认")
            if existing.confirmed_at is not None:
                return  # 幂等
            LinkService._validate_target(
                session, family_id, photo, existing.group_subject_id, settings, check_limit=True
            )
            LinkRepository.confirm(session, existing, ts)
            return

        # 手工兜底：直接新建并确认（不依赖 AI 建议）
        assert group_subject_id is not None
        LinkService._validate_target(
            session, family_id, photo, group_subject_id, settings, check_limit=True
        )
        link, _ = LinkRepository.get_or_create(
            session,
            photo_id=photo.photo_id,
            family_id=family_id,
            group_subject_id=group_subject_id,
            source=LinkSource.MANUAL,
        )
        LinkRepository.confirm(session, link, ts)

    @staticmethod
    def _do_reject(
        session: Session,
        family_id: str,
        photo: Photo,
        link_id: str | None,
        group_subject_id: str | None,
    ) -> None:
        link = LinkService._resolve_link(session, family_id, photo, link_id, group_subject_id)
        if link.confirmed_at is not None:
            raise LinkStateError("已确认挂接不可直接判无效，请使用改挂")
        LinkRepository.reject(session, link, now_iso())

    @staticmethod
    def _do_relink(
        session: Session,
        family_id: str,
        photo: Photo,
        link_id: str | None,
        group_subject_id: str | None,
        settings: M002Settings,
    ) -> None:
        if not group_subject_id:
            raise LinkMissingError("relink 需要 group_subject_id")
        old = LinkService._resolve_link(session, family_id, photo, link_id, None)
        if old.group_subject_id == group_subject_id and old.confirmed_at is not None:
            return  # 幂等
        LinkService._validate_target(
            session, family_id, photo, group_subject_id, settings, check_limit=True
        )
        ts = now_iso()
        LinkRepository.reject(session, old, ts)
        new_link, _ = LinkRepository.get_or_create(
            session,
            photo_id=photo.photo_id,
            family_id=family_id,
            group_subject_id=group_subject_id,
            source=LinkSource.MANUAL,
        )
        LinkRepository.confirm(session, new_link, ts)

    @staticmethod
    def _recompute_photo_status(session: Session, photo: Photo) -> None:
        links = LinkRepository.list_for_photo(session, photo.photo_id)
        if any(link.confirmed_at for link in links):
            photo.status = PhotoStatus.ASSIGNED
            photo.assigned_at = photo.assigned_at or now_iso()
        elif any(link.rejected_at is None for link in links):
            photo.status = PhotoStatus.SUGGESTED
        elif links:
            photo.status = PhotoStatus.REJECTED
        else:
            photo.status = PhotoStatus.UNASSIGNED
        session.flush()

    @staticmethod
    def _on_first_confirm(
        session: Session, family_id: str, photo: Photo, links: list[PhotoSubjectLink]
    ) -> None:
        """首条确认挂接 → 窗口任务 0→1 → mark_in_progress（幂等）；窗口任务未知则仅跳过联动。"""
        for link in links:
            if link.confirmed_at is None:
                continue
            try:
                ref = TaskClient.get_group_subject(session, family_id, link.group_subject_id)
            except Exception:  # noqa: BLE001 - 目标解析失败不阻断复核
                continue
            if not ref.window_task_id:
                continue
            PhotoRepository.set_window_task(session, photo, ref.window_task_id)
            TaskClient.mark_in_progress(session, family_id, ref.window_task_id)
            return
