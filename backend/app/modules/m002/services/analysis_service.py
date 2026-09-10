"""完成分析服务（API-M002-009/010/011）。

判定单元 = 聚合子任务(学科)（ADR-013）；结论 = 完成/部分完成/未完成/无法判断 + 依据照片 + 置信度。
- 生成：窗口级门控通过后，对窗口内各学科子任务出草稿（draft）。
- 确认：draft → confirmed，同事务经 M001 commit_conclusion 回写（DATA-013 唯一写入口），
  并置相关照片 consumed_at（消费锁定）。
- 重跑：仅 draft 可重跑，run_no 递增（覆盖当前草稿语义）；已确认 → 409。
- AI 失败/不合规 → 结论=无法判断（降级兜底，不产生脏数据）。
"""
from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.core.logging import audit_event
from app.core.times import now_iso
from app.modules.m002.clients.ai_client import AiPhotoInput, get_ai_client
from app.modules.m002.clients.task_client import GroupSubjectRef, TaskClient
from app.modules.m002.config import M002Settings, get_m002_settings
from app.modules.m002.domain.enums import AnalysisStatus, Conclusion
from app.modules.m002.domain.errors import (
    AiUnavailableError,
    AnalysisConfirmedError,
    AnalysisStateError,
    GateNotSatisfiedError,
    InvalidConclusionError,
    NotFoundError,
    ValidationAppError,
)
from app.modules.m002.domain.models import CompletionAnalysis
from app.modules.m002.repository.analysis_repository import AnalysisRepository
from app.modules.m002.repository.link_repository import LinkRepository
from app.modules.m002.repository.photo_repository import PhotoRepository
from app.modules.m002.services.gate_service import GateService

logger = logging.getLogger("m002.analysis")


class AnalysisService:
    @staticmethod
    def _scoped_student(student_id: str | None, scope_student_id: str | None) -> str | None:
        if scope_student_id is not None:
            if student_id is not None and str(student_id) != str(scope_student_id):
                raise NotFoundError("学生档案不存在或无权访问")
            return str(scope_student_id)
        return str(student_id) if student_id else None

    # ---------------------------------------------------------------- 生成
    @staticmethod
    def generate(
        session: Session,
        family_id: str,
        *,
        student_id: str | None,
        group_key: str,
        scope_student_id: str | None = None,
        settings: M002Settings | None = None,
    ) -> list[CompletionAnalysis]:
        s = settings or get_m002_settings()
        sid = AnalysisService._scoped_student(student_id, scope_student_id)
        if sid is None:
            raise ValidationAppError("家庭主体须指定本家学生")
        AnalysisService._require_gate(session, family_id, sid, group_key, s)
        groups = TaskClient.list_groups(session, family_id, student_id=sid, group_key=group_key)
        subjects = [sub for grp in groups for sub in grp.subjects]
        results = [
            AnalysisService._draft_for_subject(session, family_id, sid, ref, s) for ref in subjects
        ]
        audit_event(
            "completion_analysis_generated",
            family_id=family_id,
            student_id=sid,
            detail=f"group_key={group_key} subjects={len(results)}",
        )
        return results

    # ---------------------------------------------------------------- 确认
    @staticmethod
    def confirm(
        session: Session,
        family_id: str,
        analysis_id: str,
        *,
        confirmed_by: str,
        conclusion: str | None = None,
        scope_student_id: str | None = None,
    ) -> CompletionAnalysis:
        row = AnalysisRepository.get_by_id(session, family_id, analysis_id)
        if row is None:
            raise NotFoundError("分析记录不存在或无权访问")
        if scope_student_id is not None and str(row.student_id) != str(scope_student_id):
            raise NotFoundError("分析记录不存在或无权访问")
        if row.status == AnalysisStatus.CONFIRMED:
            raise AnalysisConfirmedError("分析已确认，不可重复确认")
        if conclusion is not None:
            if conclusion not in Conclusion.ALL:
                raise InvalidConclusionError(f"未知结论: {conclusion}")
            row.conclusion = conclusion

        evidence = AnalysisService._evidence_ids(row)
        # 同事务回写 M001（DATA-013 唯一写入口）：失败则整体回滚
        TaskClient.commit_conclusion(
            session,
            family_id,
            group_subject_id=row.group_subject_id,
            conclusion=row.conclusion,
            evidence_photo_ids=evidence,
            confidence=row.confidence,
            status=AnalysisStatus.CONFIRMED,
        )
        ts = now_iso()
        AnalysisRepository.confirm(
            session, row, confirmed_by=confirmed_by, confirmed_at=ts, conclusion=row.conclusion
        )
        links = LinkRepository.list_confirmed_for_subject(session, family_id, row.group_subject_id)
        PhotoRepository.mark_consumed(session, family_id, [link.photo_id for link in links], ts)
        audit_event(
            "completion_analysis_confirmed",
            family_id=family_id,
            student_id=row.student_id,
            detail=f"analysis={analysis_id} conclusion={row.conclusion}",
        )
        return row

    # ---------------------------------------------------------------- 重跑
    @staticmethod
    def rerun(
        session: Session,
        family_id: str,
        analysis_id: str,
        *,
        scope_student_id: str | None = None,
        settings: M002Settings | None = None,
    ) -> CompletionAnalysis:
        s = settings or get_m002_settings()
        row = AnalysisRepository.get_by_id(session, family_id, analysis_id)
        if row is None:
            raise NotFoundError("分析记录不存在或无权访问")
        if scope_student_id is not None and str(row.student_id) != str(scope_student_id):
            raise NotFoundError("分析记录不存在或无权访问")
        if row.status == AnalysisStatus.CONFIRMED:
            raise AnalysisStateError("已确认分析不可重跑")
        ref = TaskClient.get_group_subject(session, family_id, row.group_subject_id)
        AnalysisService._require_gate(session, family_id, row.student_id, ref.group_key, s)
        new_row = AnalysisService._draft_for_subject(session, family_id, row.student_id, ref, s)
        audit_event(
            "completion_analysis_rerun",
            family_id=family_id,
            student_id=row.student_id,
            detail=f"from={analysis_id} run_no={new_row.run_no}",
        )
        return new_row

    # ---------------------------------------------------------------- 内部
    @staticmethod
    def _require_gate(
        session: Session,
        family_id: str,
        student_id: str,
        group_key: str,
        settings: M002Settings,
    ) -> None:
        if not settings.analysis_gate_enabled:
            return
        gate = GateService.get_gate(session, family_id, student_id=student_id, group_key=group_key)
        if not gate.satisfied:
            raise GateNotSatisfiedError(gate.pending_photos)

    @staticmethod
    def _abs_path(settings: M002Settings, photo) -> str | None:
        try:
            from app.modules.m002.services.image_store import ImageStore

            return str(ImageStore(settings.image_root).abs_path(photo.normalized_path))
        except Exception:  # noqa: BLE001 - 路径解析失败交由 AI 层降级
            return None

    @staticmethod
    def _evidence_ids(row: CompletionAnalysis) -> list[str]:
        if not row.evidence_photo_ids_json:
            return []
        try:
            return [str(x) for x in json.loads(row.evidence_photo_ids_json)]
        except (ValueError, TypeError):
            return []

    @staticmethod
    def _draft_for_subject(
        session: Session,
        family_id: str,
        student_id: str,
        ref: GroupSubjectRef,
        settings: M002Settings,
    ) -> CompletionAnalysis:
        links = LinkRepository.list_confirmed_for_subject(
            session, family_id, ref.group_subject_id
        )
        evidence_ids = [link.photo_id for link in links][: settings.analysis_evidence_max_photos]
        photos = PhotoRepository.list_by_ids(session, family_id, evidence_ids)
        evidence = [
            AiPhotoInput(
                photo_id=p.photo_id,
                student_id=p.student_id,
                kind=p.kind,
                normalized_path=AnalysisService._abs_path(settings, p),
                mime=p.original_mime,
            )
            for p in photos
        ]
        conclusion = Conclusion.UNKNOWN
        confidence: float | None = None
        model: str | None = None
        prompt_version: str | None = None
        try:
            draft = get_ai_client().analyze_completion(
                session,
                family_id,
                student_id=student_id,
                subject=ref.subject,
                group_subject_id=ref.group_subject_id,
                evidence=evidence,
            )
            conclusion = draft.conclusion if draft.conclusion in Conclusion.ALL else Conclusion.UNKNOWN
            confidence = draft.confidence
            model = draft.model
            prompt_version = draft.prompt_version
            allowed = set(evidence_ids)
            filtered = [pid for pid in draft.evidence_photo_ids if pid in allowed]
            evidence_ids = filtered or evidence_ids
        except AiUnavailableError as exc:
            logger.warning("analysis degraded (AI unavailable): %s", exc)
            conclusion = Conclusion.UNKNOWN
            confidence = None

        run_no = AnalysisRepository.next_run_no(session, ref.group_subject_id)
        return AnalysisRepository.create(
            session,
            group_subject_id=ref.group_subject_id,
            family_id=family_id,
            student_id=student_id,
            conclusion=conclusion,
            evidence_photo_ids_json=json.dumps(evidence_ids, ensure_ascii=False),
            confidence=confidence,
            run_no=run_no,
            model=model,
            prompt_version=prompt_version,
        )
