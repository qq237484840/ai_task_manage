"""Mock Provider（测试桩 / 离线降级，ADR-011）。

- **确定性**：相同输入必得相同输出，便于单测与验收断言（无随机、无外部依赖）。
- **显著标注**：`model` 以 `mock-` 前缀命名，产物 `mock=True`，禁止静默冒充真实结果。
- 输出仍为**原始 JSON 文本**，与真实 Provider 同路径经 schema 校验（不跳过校验）。
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from app.core.ai.prompts import (
    PROMPT_COMPLETION_ANALYSIS,
    PROMPT_PHOTO_LINK_SUGGEST,
    PROMPT_TASK_SPEC_PARSE,
)
from app.core.ai.providers.base import (
    LLMRequest,
    OCRRequest,
    ProviderResponse,
    VisionRequest,
)

MOCK_VISION_MODEL = "mock-vision"
MOCK_LLM_MODEL = "mock-llm"
MOCK_OCR_MODEL = "mock-ocr"

_SUBJECT_ALIASES = {
    "语文": "chinese",
    "数学": "math",
    "英语": "english",
    "物理": "physics",
    "化学": "chemistry",
    "生物": "biology",
    "历史": "history",
    "地理": "geography",
    "政治": "politics",
    "道法": "morality",
    "道德与法治": "morality",
    "科学": "science",
    "体育": "pe",
    "美术": "art",
    "音乐": "music",
    "信息": "it",
    "信息技术": "it",
}

_DEFAULT_PARSE_CONFIDENCE = 0.8


def _sleep(latency_ms: int) -> None:
    if latency_ms > 0:
        time.sleep(latency_ms / 1000.0)


def _normalize_subject(label: str) -> str:
    label = label.strip()
    return _SUBJECT_ALIASES.get(label, label.lower())


def _parse_task_spec(texts: list[str], image_count: int) -> dict[str, Any]:
    subjects: dict[str, list[str]] = {}
    order: list[str] = []
    for text in texts:
        for chunk in re.split(r"[;\n；]+", text or ""):
            chunk = chunk.strip()
            if not chunk:
                continue
            match = re.match(r"^([^:：]{1,10})[:：]\s*(.+)$", chunk)
            if match:
                subject = _normalize_subject(match.group(1))
                body = match.group(2)
            else:
                subject = "general"
                body = chunk
            items = [part.strip() for part in re.split(r"[、,，]+", body) if part.strip()]
            if subject not in subjects:
                subjects[subject] = []
                order.append(subject)
            subjects[subject].extend(items)

    if not order and image_count > 0:
        # 图片-only 且无文本：返回显式可识别的 Mock 产物，提示需人工确认
        return {
            "subjects": [
                {
                    "subject": "unknown",
                    "contents": [{"text": "(mock) 图片内容未解析，请人工确认"}],
                    "confidence": 0.2,
                }
            ],
            "confidence": 0.2,
        }

    return {
        "subjects": [
            {
                "subject": subject,
                "contents": [{"text": text} for text in subjects[subject]],
                "confidence": _DEFAULT_PARSE_CONFIDENCE,
            }
            for subject in order
        ],
        "confidence": _DEFAULT_PARSE_CONFIDENCE if order else 0.0,
    }


def _suggest_links(candidates: list[dict[str, str]]) -> dict[str, Any]:
    links = [
        {
            "group_subject_id": str(item["group_subject_id"]),
            "subject": str(item["subject"]),
            "confidence": 0.8,
        }
        for item in candidates
    ]
    return {"links": links, "confidence": 0.8 if links else 0.0}


def _analyze_completion(photo_ids: list[str]) -> dict[str, Any]:
    if photo_ids:
        return {
            "conclusion": "完成",
            "evidence_photo_ids": list(photo_ids),
            "confidence": 0.7,
        }
    return {"conclusion": "无法判断", "evidence_photo_ids": [], "confidence": 0.0}


def _mock_payload(prompt_key: str, context: dict[str, Any]) -> dict[str, Any]:
    override = context.get("mock_override")
    if isinstance(override, dict):
        # override 仅改变数据来源；仍走 schema 校验，不合规则被拦截
        return override
    if prompt_key == PROMPT_TASK_SPEC_PARSE:
        texts = [str(t) for t in context.get("source_texts", []) if t]
        return _parse_task_spec(texts, int(context.get("image_count", 0) or 0))
    if prompt_key == PROMPT_PHOTO_LINK_SUGGEST:
        # 键名必须与 AIService 注入（service.py）及 prompt 变量 `$candidates` 一致；
        # 历史 BUG-003：此处曾误读 `candidate_subjects` → 建议恒空（静默失效）。
        return _suggest_links(list(context.get("candidates", []) or []))
    if prompt_key == PROMPT_COMPLETION_ANALYSIS:
        return _analyze_completion([str(p) for p in context.get("photo_ids", []) or []])
    # 未识别能力：返回空 JSON 对象（会被 schema 校验拦截 → 降级）
    return {}


class MockVisionProvider:
    provider_name = "mock"
    model = MOCK_VISION_MODEL

    def __init__(self, *, latency_ms: int = 0) -> None:
        self._latency_ms = latency_ms

    def analyze(self, request: VisionRequest) -> ProviderResponse:
        _sleep(self._latency_ms)
        payload = _mock_payload(request.prompt.key, request.context)
        return ProviderResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model=self.model,
            provider_name=self.provider_name,
            token_usage=None,
            mock=True,
        )


class MockLLMProvider:
    provider_name = "mock"
    model = MOCK_LLM_MODEL

    def __init__(self, *, latency_ms: int = 0) -> None:
        self._latency_ms = latency_ms

    def generate(self, request: LLMRequest) -> ProviderResponse:
        _sleep(self._latency_ms)
        payload = _mock_payload(request.prompt.key, request.context)
        return ProviderResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model=self.model,
            provider_name=self.provider_name,
            token_usage=None,
            mock=True,
        )


class MockOCRProvider:
    provider_name = "mock"
    model = MOCK_OCR_MODEL

    def __init__(self, *, latency_ms: int = 0) -> None:
        self._latency_ms = latency_ms

    def extract_text(self, request: OCRRequest) -> ProviderResponse:
        _sleep(self._latency_ms)
        text = str(request.context.get("mock_ocr_text", "(mock) OCR 未接入真实引擎"))
        return ProviderResponse(
            text=text,
            model=self.model,
            provider_name=self.provider_name,
            token_usage=None,
            mock=True,
        )


__all__ = [
    "MOCK_LLM_MODEL",
    "MOCK_OCR_MODEL",
    "MOCK_VISION_MODEL",
    "MockLLMProvider",
    "MockOCRProvider",
    "MockVisionProvider",
]
