"""M002 → 横切 AI 接入层（`app/core/ai/`，ADR-011 / Task-006）边界收敛点。

规则：
- M002 **不直连三方**；一切 LLM 能力经本 port 调用，默认实现委托 `app/core/ai/`。
- 真实 Provider 默认、Mock 降级（ADR-011）；本模块提供 MockAiClient 供测试与离线降级。
- 失败语义统一抛 AiUnavailableError（超时/不合规/未就绪/不可用），调用方必须降级：
  * 挂接建议失败 → 照片保持 unassigned，不产生脏数据；
  * 完成分析失败 → 结论 = 无法判断，evidence 保留。
- 对接 `app/core/ai` 的 `suggest_photo_links` / `analyze_completion`（含 available/ok 信封语义）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy.orm import Session

from app.modules.m002.clients.task_client import GroupSubjectRef
from app.modules.m002.domain.enums import Conclusion
from app.modules.m002.domain.errors import AiUnavailableError


@dataclass(frozen=True)
class AiPhotoInput:
    """送入 AI 的照片最小上下文（本地受控路径仅用于读取字节，不外发路径本身）。"""

    photo_id: str
    student_id: str
    kind: str
    normalized_path: str | None = None
    mime: str = "image/jpeg"


@dataclass(frozen=True)
class LinkSuggestion:
    """AI 挂接建议（目标 = 聚合学科子任务）。"""

    group_subject_id: str
    confidence: float
    model: str = "provider"
    prompt_version: str = "v1"


@dataclass(frozen=True)
class AnalysisDraft:
    """AI 完成分析草稿（判定单元 = 聚合子任务(学科)）。"""

    conclusion: str
    evidence_photo_ids: list[str] = field(default_factory=list)
    confidence: float | None = None
    model: str = "provider"
    prompt_version: str = "v1"


class AiClient(Protocol):
    def suggest_links(
        self,
        session: Session,
        family_id: str,
        photo: AiPhotoInput,
        candidates: list[GroupSubjectRef],
    ) -> list[LinkSuggestion]: ...

    def analyze_completion(
        self,
        session: Session,
        family_id: str,
        *,
        student_id: str,
        subject: str,
        group_subject_id: str,
        evidence: list[AiPhotoInput],
    ) -> AnalysisDraft: ...


class DefaultAiClient:
    """默认实现：委托 `app/core/ai/`（Task-006）；不可用 → AiUnavailableError（降级）。"""

    def suggest_links(
        self,
        session: Session,
        family_id: str,
        photo: AiPhotoInput,
        candidates: list[GroupSubjectRef],
    ) -> list[LinkSuggestion]:
        try:
            from app.core.ai import (  # noqa: PLC0415
                ImageInput,
                PhotoInput,
                SubjectCandidate,
                suggest_photo_links,
            )
        except ImportError as exc:  # pragma: no cover
            raise AiUnavailableError("AI 接入层 app/core/ai 尚未就绪，已降级") from exc
        try:
            outcome = suggest_photo_links(
                session,
                family_id=family_id,
                photo=PhotoInput(
                    photo_id=photo.photo_id,
                    image=ImageInput(mime=photo.mime, path=photo.normalized_path, image_id=photo.photo_id),
                ),
                candidates=[
                    SubjectCandidate(group_subject_id=c.group_subject_id, subject=c.subject)
                    for c in candidates
                ],
            )
        except Exception as exc:  # noqa: BLE001 - 统一降级语义
            raise AiUnavailableError(str(exc)) from exc
        if not (outcome.ok and outcome.available):
            raise AiUnavailableError(outcome.error_message or "AI 挂接建议不可用")
        return [
            LinkSuggestion(
                group_subject_id=link.group_subject_id,
                confidence=link.confidence,
                model=outcome.model_name or "provider",
                prompt_version=outcome.prompt_version,
            )
            for link in outcome.links
        ]

    def analyze_completion(
        self,
        session: Session,
        family_id: str,
        *,
        student_id: str,
        subject: str,
        group_subject_id: str,
        evidence: list[AiPhotoInput],
    ) -> AnalysisDraft:
        try:
            from app.core.ai import (  # noqa: PLC0415
                ImageInput,
                PhotoInput,
                analyze_completion,
            )
        except ImportError as exc:  # pragma: no cover
            raise AiUnavailableError("AI 接入层 app/core/ai 尚未就绪，已降级") from exc
        try:
            outcome = analyze_completion(
                session,
                family_id=family_id,
                subject=subject,
                contents=[],
                photos=[
                    PhotoInput(
                        photo_id=e.photo_id,
                        image=ImageInput(mime=e.mime, path=e.normalized_path, image_id=e.photo_id),
                    )
                    for e in evidence
                ],
            )
        except Exception as exc:  # noqa: BLE001
            raise AiUnavailableError(str(exc)) from exc
        if not (outcome.ok and outcome.available):
            raise AiUnavailableError(outcome.error_message or "AI 完成分析不可用")
        return AnalysisDraft(
            conclusion=outcome.conclusion,
            evidence_photo_ids=list(outcome.evidence_photo_ids),
            confidence=outcome.confidence,
            model=outcome.model_name or "provider",
            prompt_version=outcome.prompt_version,
        )


class MockAiClient:
    """确定性 Mock（最低验收线）；可配置失败以验证降级兜底。"""

    def __init__(
        self,
        *,
        suggest_enabled: bool = False,
        suggest_confidence: float = 0.9,
        suggest_all: bool = False,
        fail_suggest: bool = False,
        analysis_conclusion: str = Conclusion.COMPLETED,
        analysis_confidence: float | None = 0.8,
        fail_analysis: bool = False,
    ):
        self.suggest_enabled = suggest_enabled
        self.suggest_confidence = suggest_confidence
        self.suggest_all = suggest_all
        self.fail_suggest = fail_suggest
        self.analysis_conclusion = analysis_conclusion
        self.analysis_confidence = analysis_confidence
        self.fail_analysis = fail_analysis
        self.suggest_calls: list[tuple[str, tuple[str, ...]]] = []
        self.analyze_calls: list[str] = []

    def suggest_links(
        self,
        session: Session,
        family_id: str,
        photo: AiPhotoInput,
        candidates: list[GroupSubjectRef],
    ) -> list[LinkSuggestion]:
        self.suggest_calls.append((photo.photo_id, tuple(c.group_subject_id for c in candidates)))
        if self.fail_suggest:
            raise AiUnavailableError("mock suggest timeout")
        if not self.suggest_enabled or not candidates:
            return []
        targets = candidates if self.suggest_all else candidates[:1]
        return [
            LinkSuggestion(group_subject_id=c.group_subject_id, confidence=self.suggest_confidence)
            for c in targets
        ]

    def analyze_completion(
        self,
        session: Session,
        family_id: str,
        *,
        student_id: str,
        subject: str,
        group_subject_id: str,
        evidence: list[AiPhotoInput],
    ) -> AnalysisDraft:
        self.analyze_calls.append(group_subject_id)
        if self.fail_analysis:
            raise AiUnavailableError("mock analyze timeout")
        return AnalysisDraft(
            conclusion=self.analysis_conclusion,
            evidence_photo_ids=[e.photo_id for e in evidence],
            confidence=self.analysis_confidence,
        )


_ai_client: AiClient = DefaultAiClient()


def get_ai_client() -> AiClient:
    return _ai_client


def set_ai_client(client: AiClient | None) -> None:
    """测试注入 Mock/桩；传 None 恢复默认（真实 Provider → app/core/ai）。"""
    global _ai_client
    _ai_client = client or DefaultAiClient()
