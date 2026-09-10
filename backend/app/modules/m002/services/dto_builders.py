"""ORM Photo/UploadBatch/PhotoSubjectLink/CompletionAnalysis → DTO 装配（纯映射，无业务逻辑）。

本地路径字段绝不进入对外 PhotoDTO（受控目录相对路径不出网）。
"""
from __future__ import annotations

import json
import logging

from app.modules.m002.domain.models import (
    CompletionAnalysis,
    Photo,
    PhotoSubjectLink,
    UploadBatch,
)
from app.modules.m002.schemas import (
    AnalysisItemOut,
    BatchBriefOut,
    BatchOut,
    ContentUrlsOut,
    LinkDTO,
    PhotoDTO,
    QualityReportOut,
    UploadPhotoOut,
)

logger = logging.getLogger("m002.dto")


def _content_urls(photo_id: str) -> ContentUrlsOut:
    base = f"/api/v1/photos/{photo_id}/content"
    return ContentUrlsOut(original=f"{base}?kind=original", normalized=f"{base}?kind=normalized")


def _quality_report(photo: Photo) -> QualityReportOut:
    try:
        payload = json.loads(photo.quality_report_json or "{}")
        return QualityReportOut.model_validate(payload)
    except (ValueError, KeyError) as exc:  # 数据兜底：质量快照异常不应击穿读链路
        logger.warning("photo %s quality_report_json 不可解析: %s", photo.photo_id, exc)
        return QualityReportOut(ruleset_version="unknown", passed=True, checks=[])


def build_link_dto(link: PhotoSubjectLink, subject_name: str | None = None) -> LinkDTO:
    return LinkDTO(
        link_id=link.link_id,
        group_subject_id=link.group_subject_id,
        subject=subject_name,
        source=link.source,
        confidence=link.confidence,
        confirmed_at=link.confirmed_at,
        rejected_at=link.rejected_at,
        created_at=link.created_at,
    )


def build_photo_dto(
    photo: Photo,
    *,
    links: list[PhotoSubjectLink] | None = None,
    subject_names: dict[str, str] | None = None,
) -> PhotoDTO:
    names = subject_names or {}
    link_dtos = [
        build_link_dto(link, names.get(link.group_subject_id)) for link in (links or [])
    ]
    return PhotoDTO(
        photo_id=photo.photo_id,
        batch_id=photo.batch_id,
        student_id=photo.student_id,
        seq_no=photo.seq_no,
        kind=photo.kind,
        status=photo.status,
        task_id=photo.task_id,
        links=link_dtos,
        quality=_quality_report(photo),
        content_urls=_content_urls(photo.photo_id),
        created_at=photo.created_at,
    )


def build_batch_out(row: UploadBatch) -> BatchOut:
    return BatchOut(
        batch_id=row.batch_id,
        family_id=row.family_id,
        student_id=row.student_id,
        kind=row.kind,
        created_by_type=row.created_by_type,
        created_by_id=row.created_by_id,
        created_at=row.created_at,
    )


def build_upload_out(photo: Photo) -> UploadPhotoOut:
    return UploadPhotoOut(
        photo_id=photo.photo_id,
        batch=BatchBriefOut(
            batch_id=photo.batch_id, student_id=photo.student_id, kind=photo.kind
        ),
        seq_no=photo.seq_no,
        kind=photo.kind,
        status=photo.status,
        quality=_quality_report(photo),
        content_urls=_content_urls(photo.photo_id),
    )


def build_analysis_out(row: CompletionAnalysis, subject_name: str | None = None) -> AnalysisItemOut:
    evidence: list[str] = []
    if row.evidence_photo_ids_json:
        try:
            evidence = [str(x) for x in json.loads(row.evidence_photo_ids_json)]
        except (ValueError, TypeError):
            evidence = []
    return AnalysisItemOut(
        analysis_id=row.analysis_id,
        group_subject_id=row.group_subject_id,
        subject=subject_name,
        conclusion=row.conclusion,
        evidence_photo_ids=evidence,
        confidence=row.confidence,
        status=row.status,
        model=row.model,
        prompt_version=row.prompt_version,
        run_no=row.run_no,
        confirmed_by=row.confirmed_by,
        confirmed_at=row.confirmed_at,
        created_at=row.created_at,
    )
