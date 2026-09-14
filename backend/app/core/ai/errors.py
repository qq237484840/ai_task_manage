"""AI 接入层错误分类与映射（网络 / 限额 / 内容拒绝 / 超时 / 输出不合规）。

原则（Task-006 §3.1 / ADR-011）：
- 区分 **可重试**（超时/限流/服务端错误/输出不合规）与 **不可重试**（鉴权/配置/内容拒绝）；
- 上游不需要感知具体厂商：本层统一映射为 `AIErrorCode`，降级时返回明确「不可用」信号。

`BUG-005` 修复（`Task-015`）：
- `403` 不再一律视为「鉴权失败」——先按**配额线索**识别「账户余额/配额不足」
  （`QUOTA_EXHAUSTED`，**不可重试**），无线索才归为 `AUTH_ERROR`；
- 4xx/5xx 的 `message` 附**脱敏 + 截断**的三方响应摘要，使 DATA-009 记录可直接定位故障；
- `message` 安全约束不变：**禁止携带密钥等敏感内容**（见 `AIError.__init__`）。
"""
from __future__ import annotations

import json
import re
from enum import Enum


class AIErrorCode(str, Enum):
    """统一下游可识别的错误码（写入 DATA-009 `error` 字段）。"""

    PROVIDER_UNAVAILABLE = "provider_unavailable"  # 三方未配置/连接失败
    TIMEOUT = "timeout"  # 调用超时
    RATE_LIMITED = "rate_limited"  # 限额/限流（可退避重试）
    CONTENT_REFUSED = "content_refused"  # 内容安全拒绝
    AUTH_ERROR = "auth_error"  # 鉴权失败（密钥无效）
    QUOTA_EXHAUSTED = "quota_exhausted"  # 账户余额/配额不足（不可重试，需人工充值）
    INVALID_OUTPUT = "invalid_output"  # 返回不符合 schema
    CONFIG_ERROR = "config_error"  # 配置缺失/非法
    SERVER_ERROR = "server_error"  # 三方 5xx
    INTERNAL_ERROR = "internal_error"  # 本层未预期异常


#: 可重试错误码（指数退避后再次尝试）
RETRYABLE_CODES: frozenset[AIErrorCode] = frozenset(
    {
        AIErrorCode.TIMEOUT,
        AIErrorCode.RATE_LIMITED,
        AIErrorCode.SERVER_ERROR,
        AIErrorCode.INVALID_OUTPUT,
        AIErrorCode.PROVIDER_UNAVAILABLE,
    }
)

#: `403` 中指向「账户余额/配额」的线索词 —— 命中即判为额度耗尽（而非鉴权失败）。
#: 覆盖 OpenAI 兼容生态常见写法（`insufficient_quota` / `pre_consume_token_quota_failed`）与中文文案。
_QUOTA_HINTS: tuple[str, ...] = (
    "quota",
    "insufficient_quota",
    "balance",
    "pre_consume",
    "余额",
    "额度",
)

#: 三方响应摘要长度上限（写入 `message`；避免 HTML / 超长 body 淹没日志与 DATA-009）
_SUMMARY_LIMIT = 200

#: 摘要脱敏规则：剔除密钥特征串 / `Authorization` 形字样（`message` 禁携带敏感内容）
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9_\-]{4,}"),
    re.compile(r"(?i)authorization\s*[:=]\s*\S+"),
)


class AIError(Exception):
    """AI 调用错误基类；`code` 为对外统一错误码，`retryable` 决定是否重试。"""

    def __init__(
        self,
        code: AIErrorCode | str,
        message: str = "",
        *,
        retryable: bool | None = None,
        status_code: int | None = None,
    ) -> None:
        self.code = AIErrorCode(code)
        self.retryable = self.code in RETRYABLE_CODES if retryable is None else retryable
        self.status_code = status_code
        # message 面向内部日志/降级信号；禁止携带密钥等敏感内容
        super().__init__(message or self.code.value)

    @property
    def message(self) -> str:
        return str(self.args[0]) if self.args else self.code.value

    def as_dict(self) -> dict:
        """写入 DATA-009 `error` 字段的结构（不含敏感信息）。"""
        return {"code": self.code.value, "message": self.message}


def _redact(text: str) -> str:
    """剔除密钥特征串（`message` 安全约束）。"""
    out = text
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub("[REDACTED]", out)
    return out


def _extract_error_text(data: object) -> str:
    """从 JSON 错误体提取可读原因（优先 `error.code` + `error.message`）。"""
    if not isinstance(data, dict):
        return ""
    err = data.get("error")
    scope = err if isinstance(err, dict) else data
    if not isinstance(scope, dict):
        return ""
    message = scope.get("message")
    code = scope.get("code")
    if isinstance(message, str) and message.strip():
        if isinstance(code, str) and code.strip():
            return f"{code.strip()}: {message.strip()}"
        return message.strip()
    if isinstance(code, str) and code.strip():
        return code.strip()
    return ""


def _summarize_body(body: str, *, limit: int = _SUMMARY_LIMIT) -> str:
    """三方响应摘要：提取可读原因 → 脱敏 → 截断（HTML 折叠为 `<html>` 标注）。"""
    raw = (body or "").strip()
    if not raw:
        return ""
    text = ""
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        parsed = None
    if parsed is not None:
        text = _extract_error_text(parsed)
    if not text:
        head = raw[:200].lower()
        if head.startswith("<!doctype") or head.startswith("<html") or "<html" in head:
            text = "<html>"
        else:
            text = re.sub(r"\s+", " ", raw)
    text = _redact(text).strip()
    if len(text) > limit:
        text = text[:limit] + "…"
    return text


def from_http_status(status_code: int, body: str = "") -> AIError:
    """把三方 HTTP 状态映射为统一错误码（网络层异常由 Provider 另行捕获）。

    `BUG-005`：`403` **先判配额线索**（→ `QUOTA_EXHAUSTED`，不可重试），无线索才是 `AUTH_ERROR`；
    并统一在 `message` 附加**脱敏 + 截断**的三方摘要，便于据 DATA-009 直接排障。
    """
    text = (body or "").lower()
    summary = _summarize_body(body)
    detail = f" | 三方摘要: {summary}" if summary else ""

    if status_code == 401:
        return AIError(AIErrorCode.AUTH_ERROR, f"三方鉴权失败{detail}", status_code=status_code)
    if status_code == 403:
        if any(hint in text for hint in _QUOTA_HINTS):
            return AIError(
                AIErrorCode.QUOTA_EXHAUSTED,
                f"三方账户余额/配额不足（不可重试，需充值）{detail}",
                status_code=status_code,
            )
        return AIError(AIErrorCode.AUTH_ERROR, f"三方鉴权失败{detail}", status_code=status_code)
    if status_code == 429:
        return AIError(AIErrorCode.RATE_LIMITED, f"三方限流/限额{detail}", status_code=status_code)
    if status_code in (400, 422) and any(
        kw in text for kw in ("content", "policy", "safety", "refus", "moderation")
    ):
        return AIError(AIErrorCode.CONTENT_REFUSED, f"内容被三方拒绝{detail}", status_code=status_code)
    if status_code >= 500:
        return AIError(
            AIErrorCode.SERVER_ERROR, f"三方服务错误 {status_code}{detail}", status_code=status_code
        )
    if status_code >= 400:
        return AIError(
            AIErrorCode.CONFIG_ERROR,
            f"三方请求非法 {status_code}{detail}",
            retryable=False,
            status_code=status_code,
        )
    return AIError(AIErrorCode.INTERNAL_ERROR, f"三方返回异常 {status_code}", status_code=status_code)


__all__ = ["AIError", "AIErrorCode", "RETRYABLE_CODES", "from_http_status"]
