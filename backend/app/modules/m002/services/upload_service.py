"""上传（API-M002-001/002：建批次 + 单张上传 + 自增页序）。

流程（契约 D1~D6）：
  scope/批次校验 → 单批上限 → 硬校验(size→413/pixels→422/format→415) → 质检 v1.0(422) →
  归一 → 原图落盘 + 归一 JPEG 落盘 → 行写入 → commit。
文件与行同生命周期：任何 DB 失败 → 回滚并清理已落盘文件（无残留）；两阶段写入因此
在本服务显式 commit（打破"Repository 不 commit"惯例的必要例外，详见类 docstring）。
并发：同批次以 (family_id, batch_id) 进程级键互斥串行；DB UNIQUE/锁冲突 → 409 concurrent_conflict。
"""
from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.logging import audit_event
from app.modules.m002.clients.task_client import TaskClient
from app.modules.m002.config import M002Settings
from app.modules.m002.domain.errors import (
    BatchPhotoLimitError,
    ConcurrentConflictError,
    ImageQualityRejectedError,
    ImageTooLargeError,
    InternalAppError,
    NotFoundError,
    PixelLimitError,
    UnsupportedMediaError,
    ValidationAppError,
)
from app.modules.m002.domain.models import Photo, UploadBatch
from app.modules.m002.repository.batch_repository import BatchRepository
from app.modules.m002.repository.photo_repository import PhotoRepository
from app.modules.m002.services.image_store import ImageStore
from app.modules.m002.services.locks import keyed_lock
from app.modules.m002.services.normalizer import Normalizer
from app.modules.m002.services.quality import LocalQualityChecker
from app.modules.m002.services.suggestion_scheduler import schedule

logger = logging.getLogger("m002.upload")

# PIL format 名 → MIME（解码来源可信；不做文件名/Content-Type 信任）
_MIME_BY_FORMAT = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class UploadService:
    """上传编排。每个方法 = 一次请求级服务（含自管 commit 的两阶段上传）。"""

    def __init__(self, settings: M002Settings):
        self.settings = settings
        self.store = ImageStore(settings.image_root)

    # —— 建批次 ——
    def create_batch(
        self,
        session: Session,
        family_id: str,
        *,
        scope_student_id: str | None = None,
        student_id: str | None = None,
        subject_type: str,
        subject_id: str,
        kind: str | None = None,
    ) -> UploadBatch:
        """建批次。student 会话强制本人（student_id 传他人 → 404）；family 会话须显式给本家学生。

        kind 由菜单入口决定（task_spec | homework）；缺省 = homework。
        """
        batch_kind = kind or self.settings.batch_default_kind
        if batch_kind not in self.settings.batch_kinds:
            raise ValidationAppError(f"未知入口 kind: {batch_kind}")
        if scope_student_id is not None:
            target = str(scope_student_id)
            if student_id is not None and str(student_id) != target:
                raise NotFoundError("学生档案不存在或无权访问")
        else:
            if student_id is None:
                raise ValidationAppError("家庭主体须指定本家学生")
            target = str(student_id)

        if not TaskClient.student_exists(session, family_id, target):
            raise NotFoundError("学生档案不存在或无权访问")

        row = BatchRepository.create(
            session,
            family_id=family_id,
            student_id=target,
            kind=batch_kind,
            created_by_type=subject_type,
            created_by_id=subject_id,
        )
        audit_event(
            "photo_batch_created",
            family_id=family_id,
            student_id=target,
            detail=f"batch={row.batch_id} kind={batch_kind} by={subject_type}:{subject_id}",
        )
        return row

    # —— 单张上传 ——
    def upload(
        self,
        session: Session,
        family_id: str,
        batch_id: str,
        file_bytes: bytes,
        *,
        scope_student_id: str | None = None,
        subject_type: str,
        subject_id: str,
        session_factory: Callable[[], Session] | None = None,
    ) -> Photo:
        """上传一张：通过后入库返回行；失败不留文件/行残留。

        commit 成功后异步触发挂接建议（进程内异步任务，幂等；失败不影响上传结果）。
        """
        s = self.settings
        with keyed_lock(f"upload:{family_id}:{batch_id}"):
            batch = BatchRepository.get_by_id(session, family_id, batch_id)
            if batch is None:
                raise NotFoundError("上传批次不存在或无权访问")
            if scope_student_id is not None and str(batch.student_id) != str(scope_student_id):
                raise NotFoundError("上传批次不存在或无权访问")

            if (
                BatchRepository.count_photos(session, batch_id)
                >= s.upload_max_photos_per_batch
            ):
                raise BatchPhotoLimitError(
                    f"本批次照片已达上限 {s.upload_max_photos_per_batch} 张，请新建批次继续上传"
                )

            # —— 阶段一：硬校验 + 质检 + 归一（不触碰文件/DB）——
            if len(file_bytes) > s.image_max_size_bytes:
                mb = s.image_max_size_bytes // (1024 * 1024)
                raise ImageTooLargeError(f"单张图片不能超过 {mb}MB")
            try:
                im = Image.open(BytesIO(file_bytes))
                mime = _MIME_BY_FORMAT.get(im.format or "")
                if mime is None:
                    raise UnsupportedMediaError("仅支持 JPEG/PNG/WEBP 图片")
                width, height = im.size
            except UnidentifiedImageError as exc:
                raise UnsupportedMediaError("文件不是有效图片（仅支持 JPEG/PNG/WEBP）") from exc

            if width * height > s.image_max_pixels:
                raise PixelLimitError("图片像素超过上限（60MP），请压缩后重试")

            report = LocalQualityChecker(s).run(im)
            if not report.passed:
                reasons = "、".join(
                    f"{c.id}(value={c.value})" for c in report.checks
                    if c.severity == "reject" and not c.passed
                )
                raise ImageQualityRejectedError(f"图片质量不合格：{reasons}")
            normalized_bytes, _ = Normalizer(s).normalize(im)

            # —— 阶段二：文件 + 行 两阶段写入（同生命周期，失败整体回滚清理）——
            photo_id = str(uuid.uuid4())
            seq_no = PhotoRepository.next_seq(session, batch_id)
            rel_dir = self.store.batch_rel_dir(family_id, batch_id)
            original_rel: str | None = None
            normalized_rel: str | None = None
            try:
                original_rel, sha256 = self.store.save_original(
                    rel_dir, seq_no=seq_no, photo_id=photo_id, data=file_bytes, mime=mime
                )
                normalized_rel = self.store.save_normalized(
                    rel_dir, seq_no=seq_no, photo_id=photo_id, data=normalized_bytes
                )
                row = PhotoRepository.create(
                    session,
                    photo_id=photo_id,
                    batch_id=batch_id,
                    family_id=family_id,
                    student_id=batch.student_id,
                    seq_no=seq_no,
                    kind=batch.kind,
                    created_by_type=subject_type,
                    created_by_id=subject_id,
                    original_mime=mime,
                    original_path=original_rel,
                    normalized_path=normalized_rel,
                    file_size_bytes=len(file_bytes),
                    width=width,
                    height=height,
                    sha256=sha256,
                    quality_report_json=json.dumps(report.to_dict(), ensure_ascii=False),
                )
                session.commit()
            except (IntegrityError, OperationalError) as exc:
                session.rollback()
                self._cleanup(original_rel, normalized_rel)
                raise ConcurrentConflictError("并发写入冲突或数据库繁忙，请重试") from exc
            except Exception as exc:
                session.rollback()
                self._cleanup(original_rel, normalized_rel)
                logger.exception("photo upload storage failure")
                raise InternalAppError("图片存储失败，请重试") from exc

            audit_event(
                "photo_uploaded",
                family_id=family_id,
                student_id=row.student_id,
                detail=f"photo={photo_id} batch={batch_id} seq={seq_no} dims={width}x{height}",
            )
            self._schedule_suggestion(session_factory, family_id, photo_id)
            return row

    def _schedule_suggestion(
        self,
        session_factory: Callable[[], Session] | None,
        family_id: str,
        photo_id: str,
    ) -> None:
        """commit 后异步触发挂接建议（幂等；无 session_factory 则跳过，测试用内联调度）。"""
        if session_factory is None:
            return

        def runner() -> None:
            from app.modules.m002.services.link_service import LinkService

            with session_factory() as worker:
                try:
                    LinkService.suggest_for_photo(worker, family_id, photo_id, settings=self.settings)
                    worker.commit()
                except Exception:  # noqa: BLE001 - 异步任务失败不得影响上传
                    worker.rollback()
                    logger.exception("async link suggestion failed for photo %s", photo_id)

        schedule(runner)

    def _cleanup(self, *rel_paths: str | None) -> None:
        """DB 失败时清理已落盘文件（幂等；残留文件绝不可达）。"""
        for rel in rel_paths:
            if rel:
                try:
                    self.store.delete(rel)
                except OSError:
                    logger.warning("upload cleanup failed for %s", rel)
