"""完成分析仓储（completion_analyses，DATA-017）。

- 判定单元 = 聚合子任务(学科)；run_no 在同一 group_subject_id 内自增。
- 全部查询强制 family_id 过滤；Repository 不自行 commit。
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.m002.domain.enums import AnalysisStatus
from app.modules.m002.domain.models import CompletionAnalysis


class AnalysisRepository:
    @staticmethod
    def next_run_no(session: Session, group_subject_id: str) -> int:
        current = (
            session.scalar(
                select(func.max(CompletionAnalysis.run_no)).where(
                    CompletionAnalysis.group_subject_id == group_subject_id
                )
            )
            or 0
        )
        return int(current) + 1

    @staticmethod
    def create(
        session: Session,
        *,
        group_subject_id: str,
        family_id: str,
        student_id: str,
        conclusion: str,
        evidence_photo_ids_json: str | None,
        confidence: float | None,
        run_no: int,
        model: str | None = None,
        prompt_version: str | None = None,
    ) -> CompletionAnalysis:
        row = CompletionAnalysis(
            group_subject_id=group_subject_id,
            family_id=family_id,
            student_id=student_id,
            conclusion=conclusion,
            evidence_photo_ids_json=evidence_photo_ids_json,
            confidence=confidence,
            status=AnalysisStatus.DRAFT,
            run_no=run_no,
            model=model,
            prompt_version=prompt_version,
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def get_by_id(
        session: Session, family_id: str, analysis_id: str
    ) -> CompletionAnalysis | None:
        return session.scalar(
            select(CompletionAnalysis).where(
                CompletionAnalysis.analysis_id == analysis_id,
                CompletionAnalysis.family_id == family_id,
            )
        )

    @staticmethod
    def list_for_subject(
        session: Session, family_id: str, group_subject_id: str
    ) -> list[CompletionAnalysis]:
        return list(
            session.scalars(
                select(CompletionAnalysis)
                .where(
                    CompletionAnalysis.family_id == family_id,
                    CompletionAnalysis.group_subject_id == group_subject_id,
                )
                .order_by(CompletionAnalysis.run_no.asc())
            )
        )

    @staticmethod
    def list_current(
        session: Session, family_id: str, group_subject_ids: list[str]
    ) -> list[CompletionAnalysis]:
        """每个学科子任务的当前分析（最大 run_no）。"""
        if not group_subject_ids:
            return []
        rows = list(
            session.scalars(
                select(CompletionAnalysis).where(
                    CompletionAnalysis.family_id == family_id,
                    CompletionAnalysis.group_subject_id.in_(group_subject_ids),
                )
            )
        )
        latest: dict[str, CompletionAnalysis] = {}
        for row in rows:
            prev = latest.get(row.group_subject_id)
            if prev is None or row.run_no > prev.run_no:
                latest[row.group_subject_id] = row
        return list(latest.values())

    @staticmethod
    def confirm(
        session: Session,
        analysis: CompletionAnalysis,
        *,
        confirmed_by: str,
        confirmed_at: str,
        conclusion: str | None = None,
    ) -> None:
        if conclusion is not None:
            analysis.conclusion = conclusion
        analysis.status = AnalysisStatus.CONFIRMED
        analysis.confirmed_by = confirmed_by
        analysis.confirmed_at = confirmed_at
        session.flush()
