"""真实三方 Provider（OpenAI 兼容 Chat Completions 协议，ADR-011 默认运行路径）。

- 仅依赖 `httpx`（FastAPI/TestClient 既有依赖），不引入新三方 SDK；
- model / api_key / base_url 全部来自配置，**禁止硬编码**；
- 超时/网络/限流/鉴权/内容拒绝统一映射为 `AIError`，由上层决定重试或降级；
- 由于密钥未就绪，本实现不参与 V1 联调验收（Mock 为最低验收线，Task-006 §6 注）。
"""
from __future__ import annotations

import base64

import httpx

from app.core.ai.errors import AIError, AIErrorCode, from_http_status
from app.core.ai.providers.base import (
    LLMRequest,
    OCRRequest,
    ProviderResponse,
    VisionRequest,
)
from app.core.ai.types import ImageInput

_CHAT_PATH = "/chat/completions"


def _data_uri(image: ImageInput) -> str:
    encoded = base64.b64encode(image.load_bytes()).decode("ascii")
    return f"data:{image.mime};base64,{encoded}"


class _OpenAICompatibleBase:
    provider_name = "openai_compatible"

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str,
        timeout_seconds: float,
        max_tokens: int,
        temperature: float,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_tokens = max_tokens
        self._temperature = temperature

    def _chat(self, messages: list[dict], *, json_mode: bool) -> ProviderResponse:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = httpx.post(
                self._base_url + _CHAT_PATH,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise AIError(AIErrorCode.TIMEOUT, "三方调用超时") from exc
        except httpx.HTTPError as exc:
            raise AIError(AIErrorCode.PROVIDER_UNAVAILABLE, "三方网络不可达") from exc

        if resp.status_code >= 400:
            raise from_http_status(resp.status_code, resp.text)

        try:
            data = resp.json()
            choice = data["choices"][0]
            text = choice["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIError(AIErrorCode.SERVER_ERROR, "三方响应结构异常") from exc

        usage = data.get("usage")
        token_usage = None
        if isinstance(usage, dict):
            token_usage = {
                k: int(v)
                for k, v in usage.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            }
        return ProviderResponse(
            text=text or "",
            model=self.model,
            provider_name=self.provider_name,
            token_usage=token_usage,
            mock=False,
        )


class OpenAICompatibleVisionProvider(_OpenAICompatibleBase):
    """图片理解（Vision）：把提示词与图片（data URI）一并发送。"""

    def analyze(self, request: VisionRequest) -> ProviderResponse:
        content: list[dict] = [{"type": "text", "text": request.prompt.render(**request.context)}]
        for image in request.images:
            content.append({"type": "image_url", "image_url": {"url": _data_uri(image)}})
        messages = [{"role": "user", "content": content}]
        return self._chat(messages, json_mode=request.response_schema is not None)


class OpenAICompatibleLLMProvider(_OpenAICompatibleBase):
    """文本大模型（LLM）。"""

    def generate(self, request: LLMRequest) -> ProviderResponse:
        messages = [{"role": "user", "content": request.prompt.render(**request.context)}]
        return self._chat(messages, json_mode=request.response_schema is not None)


class OpenAICompatibleOCRProvider(_OpenAICompatibleBase):
    """OCR：以图片理解模式提取纯文本（不做 JSON 结构约束）。"""

    def extract_text(self, request: OCRRequest) -> ProviderResponse:
        instruction = str(
            request.context.get("instruction", "提取图片中的全部文字，仅输出文字内容。")
        )
        content: list[dict] = [{"type": "text", "text": instruction}]
        for image in request.images:
            content.append({"type": "image_url", "image_url": {"url": _data_uri(image)}})
        return self._chat([{"role": "user", "content": content}], json_mode=False)


__all__ = [
    "OpenAICompatibleLLMProvider",
    "OpenAICompatibleOCRProvider",
    "OpenAICompatibleVisionProvider",
]
