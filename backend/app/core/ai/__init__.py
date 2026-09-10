"""横切 AI 接入层 `app/core/ai/`（Task-006 / AGENT-AI；ADR-011 / ADR-014）。

唯一边界：本层只负责「可靠地调用 AI 并保证输出可校验、可追溯、可降级」，不承载业务语义。

对外公开面（供 M001 链路 T / M002 链路 H 调用）：
- `AIService.parse_task_spec` → 任务输入源解析（学科子任务 + 内容项草稿 + 置信度）
- `AIService.suggest_photo_links` → 作业照片挂接建议（N:N + 置信度）
- `AIService.analyze_completion` → 聚合子任务级完成结论（含 `无法判断` 出口）
- `get_ai_service()` 进程内单例；`parse_task_spec` / `suggest_photo_links` / `analyze_completion`
  为模块级便捷入口。
"""
from __future__ import annotations

from app.core.ai.config import AISettings, get_ai_settings
from app.core.ai.errors import AIError, AIErrorCode
from app.core.ai.providers.registry import ProviderBundle, build_providers
from app.core.ai.records import AICallRecord, list_calls_by_request_id, record_call
from app.core.ai.schemas import (
    CompletionAnalysisResult,
    ParsedContentItem,
    ParsedSubject,
    PhotoLinkSuggestionResult,
    SuggestedLink,
    TaskSpecParseResult,
)
from app.core.ai.service import (
    CAPABILITY_COMPLETION_ANALYSIS,
    CAPABILITY_OCR_EXTRACT,
    CAPABILITY_PHOTO_LINK_SUGGEST,
    CAPABILITY_TASK_SPEC_PARSE,
    AIService,
    analyze_completion,
    get_ai_service,
    parse_task_spec,
    suggest_photo_links,
)
from app.core.ai.types import (
    AIOutcome,
    CompletionOutcome,
    ImageInput,
    OCRTextOutcome,
    PhotoInput,
    PhotoLinkOutcome,
    SourceInput,
    SubjectCandidate,
    TaskParseOutcome,
)

__all__ = [
    "AICallRecord",
    "AIError",
    "AIErrorCode",
    "AIOutcome",
    "AIService",
    "AISettings",
    "CAPABILITY_COMPLETION_ANALYSIS",
    "CAPABILITY_OCR_EXTRACT",
    "CAPABILITY_PHOTO_LINK_SUGGEST",
    "CAPABILITY_TASK_SPEC_PARSE",
    "CompletionAnalysisResult",
    "CompletionOutcome",
    "ImageInput",
    "OCRTextOutcome",
    "ParsedContentItem",
    "ParsedSubject",
    "PhotoInput",
    "PhotoLinkOutcome",
    "PhotoLinkSuggestionResult",
    "ProviderBundle",
    "SourceInput",
    "SubjectCandidate",
    "SuggestedLink",
    "TaskParseOutcome",
    "TaskSpecParseResult",
    "analyze_completion",
    "build_providers",
    "get_ai_service",
    "get_ai_settings",
    "list_calls_by_request_id",
    "parse_task_spec",
    "record_call",
    "suggest_photo_links",
]
