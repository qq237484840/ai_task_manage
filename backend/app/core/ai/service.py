"""AI 能力服务 —— 三个能力接口（供 M001 / M002 调用）+ 统一可靠性封装。

能力接口（签名即对接契约，供上游按名调用）：
- `AIService.parse_task_spec(session, *, family_id, sources, grade_level=None, request_id=None)`
  → `TaskParseOutcome`（学科子任务 + 内容项草稿 + 置信度）；
- `AIService.suggest_photo_links(session, *, family_id, photo, candidates, request_id=None)`
  → `PhotoLinkOutcome`（照片 → 聚合子任务 N:N + 置信度）；
- `AIService.analyze_completion(session, *, family_id, subject, contents, photos, request_id=None)`
  → `CompletionOutcome`（完成/部分完成/未完成/无法判断 + 依据照片 + 置信度）。

可靠性：超时/重试/错误映射/降级 + 每次 Provider 尝试写 DATA-009；失败时 `available=False`
作为明确「不可用」信号，供上游走手工兜底（CLARIFICATION §2.C6）。
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.ai.config import AISettings, get_ai_settings
from app.core.ai.errors import AIError, AIErrorCode
from app.core.ai.prompts import (
    PROMPT_COMPLETION_ANALYSIS,
    PROMPT_OCR_EXTRACT,
    PROMPT_PHOTO_LINK_SUGGEST,
    PROMPT_TASK_SPEC_PARSE,
    PromptTemplate,
    get_prompt,
)
from app.core.ai.providers.base import (
    LLMRequest,
    OCRRequest,
    ProviderResponse,
    VisionRequest,
    validate_structured,
)
from app.core.ai.providers.registry import (
    PROVIDER_KIND_LLM,
    PROVIDER_KIND_OCR,
    PROVIDER_KIND_VISION,
    ProviderBundle,
    ResolvedProvider,
    build_providers,
)
from app.core.ai.records import record_call
from app.core.ai.schemas import (
    CompletionAnalysisResult,
    PhotoLinkSuggestionResult,
    TaskSpecParseResult,
)
from app.core.ai.types import (
    CompletionOutcome,
    ImageInput,
    OCRTextOutcome,
    PhotoInput,
    PhotoLinkOutcome,
    SourceInput,
    SubjectCandidate,
    TaskParseOutcome,
)
from app.core.logging import get_request_id

_logger = logging.getLogger("uvicorn.error")

CAPABILITY_TASK_SPEC_PARSE = "task_spec_parse"
CAPABILITY_PHOTO_LINK_SUGGEST = "photo_link_suggest"
CAPABILITY_COMPLETION_ANALYSIS = "completion_analysis"
CAPABILITY_OCR_EXTRACT = "ocr_extract"


def _ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _new_request_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    ctx = get_request_id()
    return ctx if ctx and ctx != "-" else uuid.uuid4().hex


@dataclass
class _CallResult:
    ok: bool
    data: BaseModel | None
    text: str | None
    resolved: ResolvedProvider
    prompt: PromptTemplate
    request_id: str
    latency_ms: int
    attempts: int
    token_usage: dict[str, int] | None
    error: AIError | None
    mock: bool


class AIService:
    """AI 能力服务（进程内单例；Provider 由配置解析，业务无感知）。"""

    def __init__(
        self,
        settings: AISettings | None = None,
        *,
        providers: ProviderBundle | None = None,
    ) -> None:
        self._settings = settings or get_ai_settings()
        self._bundle = providers or build_providers(self._settings)

    @property
    def settings(self) -> AISettings:
        return self._settings

    @property
    def providers(self) -> ProviderBundle:
        return self._bundle

    # ------------------------------------------------------------------
    # 能力接口
    # ------------------------------------------------------------------

    def parse_task_spec(
        self,
        session: Session | None,
        *,
        family_id: str | None = None,
        sources: list[SourceInput],
        grade_level: str | None = None,
        request_id: str | None = None,
    ) -> TaskParseOutcome:
        """① 任务输入源解析：图片/文本 → 学科子任务 + 内容项草稿 + 置信度。"""
        prompt = get_prompt(PROMPT_TASK_SPEC_PARSE)
        texts = [s.text for s in sources if s.kind == "text" and s.text]
        images = [s.image for s in sources if s.kind == "image" and s.image is not None]
        resolved = self._bundle.vision if images else self._bundle.llm
        context: dict[str, Any] = {
            "source_texts": texts,
            "image_count": len(images),
            "grade_level": grade_level or "未提供",
        }
        result = self._invoke(
            session,
            capability=CAPABILITY_TASK_SPEC_PARSE,
            resolved=resolved,
            prompt=prompt,
            context=context,
            schema=TaskSpecParseResult,
            images=images,
            family_id=family_id,
            request_id=request_id,
            input_ref={"source_count": len(sources), "text_count": len(texts), "image_count": len(images)},
        )
        if result.ok and isinstance(result.data, TaskSpecParseResult):
            return TaskParseOutcome(
                **self._outcome_kwargs(
                    capability=CAPABILITY_TASK_SPEC_PARSE,
                    result=result,
                    prompt=prompt,
                    ok=True,
                    available=True,
                    degraded=result.resolved.degraded,
                    subjects=result.data.subjects,
                )
            )
        return TaskParseOutcome(
            **self._outcome_kwargs(
                capability=CAPABILITY_TASK_SPEC_PARSE,
                result=result,
                prompt=prompt,
                ok=False,
                available=False,
                degraded=True,
                subjects=[],
            )
        )

    def suggest_photo_links(
        self,
        session: Session | None,
        *,
        family_id: str | None = None,
        photo: PhotoInput,
        candidates: list[SubjectCandidate],
        request_id: str | None = None,
    ) -> PhotoLinkOutcome:
        """② 作业照片挂接建议：照片 → 聚合子任务 N:N + 置信度。"""
        prompt = get_prompt(PROMPT_PHOTO_LINK_SUGGEST)
        resolved = self._bundle.vision
        candidate_payload = [
            {"group_subject_id": c.group_subject_id, "subject": c.subject} for c in candidates
        ]
        context: dict[str, Any] = {"candidates": candidate_payload}
        result = self._invoke(
            session,
            capability=CAPABILITY_PHOTO_LINK_SUGGEST,
            resolved=resolved,
            prompt=prompt,
            context=context,
            schema=PhotoLinkSuggestionResult,
            images=[photo.image],
            family_id=family_id,
            request_id=request_id,
            input_ref={"photo_id": photo.photo_id, "candidate_count": len(candidates)},
        )
        if result.ok and isinstance(result.data, PhotoLinkSuggestionResult):
            valid_ids = {c.group_subject_id for c in candidates}
            # 丢弃模型编造的候选外 id（防止脏建议流入上游）
            links = [link for link in result.data.links if link.group_subject_id in valid_ids]
            return PhotoLinkOutcome(
                **self._outcome_kwargs(
                    capability=CAPABILITY_PHOTO_LINK_SUGGEST,
                    result=result,
                    prompt=prompt,
                    ok=True,
                    available=True,
                    degraded=result.resolved.degraded,
                    links=links,
                )
            )
        return PhotoLinkOutcome(
            **self._outcome_kwargs(
                capability=CAPABILITY_PHOTO_LINK_SUGGEST,
                result=result,
                prompt=prompt,
                ok=False,
                available=False,
                degraded=True,
                links=[],
            )
        )

    def analyze_completion(
        self,
        session: Session | None,
        *,
        family_id: str | None = None,
        subject: str,
        contents: list[str],
        photos: list[PhotoInput],
        request_id: str | None = None,
    ) -> CompletionOutcome:
        """③ 聚合子任务级完成结论（完成/部分完成/未完成/无法判断 + 依据照片 + 置信度）。"""
        prompt = get_prompt(PROMPT_COMPLETION_ANALYSIS)
        resolved = self._bundle.vision
        photo_ids = [p.photo_id for p in photos]
        context: dict[str, Any] = {
            "subject": subject,
            "contents": list(contents),
            "photo_ids": photo_ids,
        }
        result = self._invoke(
            session,
            capability=CAPABILITY_COMPLETION_ANALYSIS,
            resolved=resolved,
            prompt=prompt,
            context=context,
            schema=CompletionAnalysisResult,
            images=[p.image for p in photos],
            family_id=family_id,
            request_id=request_id,
            input_ref={"subject": subject, "photo_ids": photo_ids},
        )
        if result.ok and isinstance(result.data, CompletionAnalysisResult):
            allowed = set(photo_ids)
            evidence = [pid for pid in result.data.evidence_photo_ids if pid in allowed]
            conclusion = result.data.conclusion
            # 不猜原则（ADR-003）：零证据时不得给出确定结论，强制「无法判断」
            if not photo_ids and conclusion != "无法判断":
                conclusion = "无法判断"
                evidence = []
            return CompletionOutcome(
                **self._outcome_kwargs(
                    capability=CAPABILITY_COMPLETION_ANALYSIS,
                    result=result,
                    prompt=prompt,
                    ok=True,
                    available=True,
                    degraded=result.resolved.degraded,
                    conclusion=conclusion,
                    evidence_photo_ids=evidence,
                )
            )
        return CompletionOutcome(
            **self._outcome_kwargs(
                capability=CAPABILITY_COMPLETION_ANALYSIS,
                result=result,
                prompt=prompt,
                ok=False,
                available=False,
                degraded=True,
                conclusion="无法判断",
                evidence_photo_ids=[],
            )
        )

    def extract_text(
        self,
        session: Session | None,
        *,
        family_id: str | None = None,
        images: list[ImageInput],
        instruction: str = "提取图片中的全部文字，仅输出文字内容。",
        request_id: str | None = None,
    ) -> OCRTextOutcome:
        """OCR 基础设施能力（图片 → 文字；供上游可选消费，V1 三链路未强制依赖）。"""
        prompt = get_prompt(PROMPT_OCR_EXTRACT)
        resolved = self._bundle.ocr
        context: dict[str, Any] = {"instruction": instruction}
        result = self._invoke(
            session,
            capability=CAPABILITY_OCR_EXTRACT,
            resolved=resolved,
            prompt=prompt,
            context=context,
            schema=None,
            images=images,
            family_id=family_id,
            request_id=request_id,
            input_ref={"image_count": len(images)},
        )
        if result.ok:
            return OCRTextOutcome(
                **self._outcome_kwargs(
                    capability=CAPABILITY_OCR_EXTRACT,
                    result=result,
                    prompt=prompt,
                    ok=True,
                    available=True,
                    degraded=result.resolved.degraded,
                    confidence=None,
                    text=result.text or "",
                )
            )
        return OCRTextOutcome(
            **self._outcome_kwargs(
                capability=CAPABILITY_OCR_EXTRACT,
                result=result,
                prompt=prompt,
                ok=False,
                available=False,
                degraded=True,
                confidence=None,
                text="",
            )
        )

    # ------------------------------------------------------------------
    # 内部：调用 + 重试 + 记录
    # ------------------------------------------------------------------

    def _invoke(
        self,
        session: Session | None,
        *,
        capability: str,
        resolved: ResolvedProvider,
        prompt: PromptTemplate,
        context: dict[str, Any],
        schema: type[BaseModel] | None,
        images: list[ImageInput] | None = None,
        family_id: str | None = None,
        request_id: str | None = None,
        input_ref: dict[str, Any] | None = None,
    ) -> _CallResult:
        rid = _new_request_id(request_id)
        max_attempts = max(1, int(self._settings.max_retries) + 1)
        total_started = time.perf_counter()
        attempts = 0
        last_error: AIError | None = None
        image_list = list(images or [])

        for attempt in range(1, max_attempts + 1):
            attempts = attempt
            started = time.perf_counter()
            response: ProviderResponse | None = None
            try:
                response = self._call_provider(resolved, prompt, context, schema, image_list)
                data: BaseModel | None = None
                if schema is not None:
                    data = validate_structured(response.text, schema)
                latency = _ms(started)
                record_call(
                    session,
                    request_id=rid,
                    family_id=family_id,
                    capability=capability,
                    provider_kind=resolved.kind,
                    provider_name=response.provider_name or resolved.provider_name,
                    model=response.model or resolved.model,
                    prompt_key=prompt.key,
                    prompt_version=prompt.version,
                    attempt=attempt,
                    latency_ms=latency,
                    token_usage=response.token_usage,
                    result=data if data is not None else {"text": response.text},
                    confidence=getattr(data, "confidence", None) if data is not None else None,
                    status="ok",
                    mock=bool(response.mock),
                    error=None,
                    input_ref=input_ref,
                )
                return _CallResult(
                    ok=True,
                    data=data,
                    text=response.text,
                    resolved=resolved,
                    prompt=prompt,
                    request_id=rid,
                    latency_ms=_ms(total_started),
                    attempts=attempt,
                    token_usage=response.token_usage,
                    error=None,
                    mock=bool(response.mock),
                )
            except AIError as exc:
                last_error = exc
                self._record_error(
                    session, rid=rid, family_id=family_id, capability=capability,
                    resolved=resolved, prompt=prompt, response=response, error=exc,
                    attempt=attempt, latency_ms=_ms(started), input_ref=input_ref,
                )
                if not exc.retryable or attempt >= max_attempts:
                    break
                _backoff(self._settings.retry_backoff_seconds, attempt)
            except Exception:  # noqa: BLE001 - 未预期异常统一降级，不向业务层抛裸异常
                _logger.exception("AI 调用未预期异常 capability=%s", capability)
                last_error = AIError(AIErrorCode.INTERNAL_ERROR, "AI 调用未预期异常", retryable=False)
                self._record_error(
                    session, rid=rid, family_id=family_id, capability=capability,
                    resolved=resolved, prompt=prompt, response=response, error=last_error,
                    attempt=attempt, latency_ms=_ms(started), input_ref=input_ref,
                )
                break

        return _CallResult(
            ok=False,
            data=None,
            text=None,
            resolved=resolved,
            prompt=prompt,
            request_id=rid,
            latency_ms=_ms(total_started),
            attempts=attempts,
            token_usage=None,
            error=last_error or AIError(AIErrorCode.INTERNAL_ERROR, "AI 调用失败"),
            mock=resolved.mock,
        )

    @staticmethod
    def _call_provider(
        resolved: ResolvedProvider,
        prompt: PromptTemplate,
        context: dict[str, Any],
        schema: type[BaseModel] | None,
        images: list[ImageInput],
    ) -> ProviderResponse:
        provider = resolved.provider
        if resolved.kind == PROVIDER_KIND_VISION:
            return provider.analyze(  # type: ignore[attr-defined]
                VisionRequest(prompt=prompt, images=images, context=context, response_schema=schema)
            )
        if resolved.kind == PROVIDER_KIND_LLM:
            return provider.generate(  # type: ignore[attr-defined]
                LLMRequest(prompt=prompt, context=context, response_schema=schema)
            )
        if resolved.kind == PROVIDER_KIND_OCR:
            return provider.extract_text(  # type: ignore[attr-defined]
                OCRRequest(images=images, context=context)
            )
        raise AIError(AIErrorCode.CONFIG_ERROR, f"未知 Provider 类型：{resolved.kind}", retryable=False)

    @staticmethod
    def _record_error(
        session: Session | None,
        *,
        rid: str,
        family_id: str | None,
        capability: str,
        resolved: ResolvedProvider,
        prompt: PromptTemplate,
        response: ProviderResponse | None,
        error: AIError,
        attempt: int,
        latency_ms: int,
        input_ref: dict[str, Any] | None,
    ) -> None:
        record_call(
            session,
            request_id=rid,
            family_id=family_id,
            capability=capability,
            provider_kind=resolved.kind,
            provider_name=(response.provider_name if response else resolved.provider_name),
            model=(response.model if response else resolved.model),
            prompt_key=prompt.key,
            prompt_version=prompt.version,
            attempt=attempt,
            latency_ms=latency_ms,
            token_usage=(response.token_usage if response else None),
            result=None,
            confidence=None,
            status="error",
            mock=bool(response.mock) if response else resolved.mock,
            error=error.as_dict(),
            input_ref=input_ref,
        )

    @staticmethod
    def _outcome_kwargs(
        *,
        capability: str,
        result: _CallResult,
        prompt: PromptTemplate,
        ok: bool,
        available: bool,
        degraded: bool,
        **extra: Any,
    ) -> dict[str, Any]:
        return {
            "capability": capability,
            "ok": ok,
            "available": available,
            "degraded": degraded,
            "mock": result.mock,
            "request_id": result.request_id,
            "provider_name": result.resolved.provider_name,
            "model_name": result.resolved.model,
            "prompt_key": prompt.key,
            "prompt_version": prompt.version,
            "latency_ms": result.latency_ms,
            "attempts": result.attempts,
            "confidence": getattr(result.data, "confidence", None) if result.data is not None else None,
            "token_usage": result.token_usage,
            "error": result.error.code.value if result.error else None,
            "error_message": result.error.message if result.error else None,
            **extra,
        }


def _backoff(base_seconds: float, attempt: int) -> None:
    if base_seconds > 0:
        time.sleep(base_seconds * attempt)


@lru_cache
def get_ai_service() -> AIService:
    """进程内单例（Provider 由配置解析一次）。"""
    return AIService()


def parse_task_spec(session: Session | None, **kwargs: Any) -> TaskParseOutcome:
    """模块级便捷入口（等价 `get_ai_service().parse_task_spec`）。"""
    return get_ai_service().parse_task_spec(session, **kwargs)


def suggest_photo_links(session: Session | None, **kwargs: Any) -> PhotoLinkOutcome:
    """模块级便捷入口（等价 `get_ai_service().suggest_photo_links`）。"""
    return get_ai_service().suggest_photo_links(session, **kwargs)


def analyze_completion(session: Session | None, **kwargs: Any) -> CompletionOutcome:
    """模块级便捷入口（等价 `get_ai_service().analyze_completion`）。"""
    return get_ai_service().analyze_completion(session, **kwargs)


__all__ = [
    "AIService",
    "CAPABILITY_COMPLETION_ANALYSIS",
    "CAPABILITY_OCR_EXTRACT",
    "CAPABILITY_PHOTO_LINK_SUGGEST",
    "CAPABILITY_TASK_SPEC_PARSE",
    "analyze_completion",
    "get_ai_service",
    "parse_task_spec",
    "suggest_photo_links",
]
