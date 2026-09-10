"""AI 接入层错误分类与映射（网络 / 限额 / 内容拒绝 / 超时 / 输出不合规）。

原则（Task-006 §3.1 / ADR-011）：
- 区分 **可重试**（超时/限流/服务端错误/输出不合规）与 **不可重试**（鉴权/配置/内容拒绝）；
- 上游不需要感知具体厂商：本层统一映射为 `AIErrorCode`，降级时返回明确「不可用」信号。
"""
from __future__ import annotations

from enum import Enum


class AIErrorCode(str, Enum):
    """统一下游可识别的错误码（写入 DATA-009 `error` 字段）。"""

    PROVIDER_UNAVAILABLE = "provider_unavailable"  # 三方未配置/连接失败
    TIMEOUT = "timeout"  # 调用超时
    RATE_LIMITED = "rate_limited"  # 限额/限流
    CONTENT_REFUSED = "content_refused"  # 内容安全拒绝
    AUTH_ERROR = "auth_error"  # 鉴权失败（密钥无效）
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


def from_http_status(status_code: int, body: str = "") -> AIError:
    """把三方 HTTP 状态映射为统一错误码（网络层异常由 Provider 另行捕获）。"""
    text = (body or "").lower()
    if status_code in (401, 403):
        return AIError(AIErrorCode.AUTH_ERROR, "三方鉴权失败", status_code=status_code)
    if status_code == 429:
        return AIError(AIErrorCode.RATE_LIMITED, "三方限流/限额", status_code=status_code)
    if status_code in (400, 422) and any(
        kw in text for kw in ("content", "policy", "safety", "refus", "moderation")
    ):
        return AIError(AIErrorCode.CONTENT_REFUSED, "内容被三方拒绝", status_code=status_code)
    if status_code >= 500:
        return AIError(AIErrorCode.SERVER_ERROR, f"三方服务错误 {status_code}", status_code=status_code)
    if status_code >= 400:
        return AIError(
            AIErrorCode.CONFIG_ERROR,
            f"三方请求非法 {status_code}",
            retryable=False,
            status_code=status_code,
        )
    return AIError(AIErrorCode.INTERNAL_ERROR, f"三方返回异常 {status_code}", status_code=status_code)


__all__ = ["AIError", "AIErrorCode", "RETRYABLE_CODES", "from_http_status"]
