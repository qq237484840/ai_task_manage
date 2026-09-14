"""单测：`app/core/ai/errors.py` 的三方状态映射与留痕（`BUG-005` / `Task-015` 修复取证）。

判别力要点：`403` 的配额线索必须落到**独立错误码** `QUOTA_EXHAUSTED`（不可重试），
且 `message` 必须携带**脱敏 + 截断**的三方摘要 —— 否则本文件用例立败。
"""
from __future__ import annotations

from app.core.ai.errors import RETRYABLE_CODES, AIErrorCode, from_http_status

#: 与 `BUG-005 §1` 实测原文同源的三方余额不足响应体
QUOTA_BODY = (
    '{"error":{"code":"pre_consume_token_quota_failed",'
    '"message":"您的 API Key 余额不足：剩余 ¥0.005557，本次请求预估需 ¥0.010639"}}'
)


def test_403_quota_hint_maps_to_dedicated_non_retryable_code():
    """配额不足 → `quota_exhausted`（不可重试），且摘要可读（非「鉴权失败」误报）。"""
    err = from_http_status(403, QUOTA_BODY)

    assert err.code == AIErrorCode.QUOTA_EXHAUSTED
    assert err.code.value == "quota_exhausted"
    assert err.retryable is False
    assert err.code not in RETRYABLE_CODES
    assert err.status_code == 403
    assert "余额不足" in err.message, "应从三方响应摘要中取到真实原因"
    assert "鉴权失败" not in err.message, "不得再误报为鉴权失败"


def test_403_without_quota_hint_stays_auth_error():
    """无配额线索的 403 仍归为鉴权失败（向后兼容，不放宽既有语义）。"""
    err = from_http_status(403, '{"error":{"message":"forbidden"}}')

    assert err.code == AIErrorCode.AUTH_ERROR
    assert err.retryable is False


def test_401_is_auth_error():
    err = from_http_status(401, '{"error":{"message":"invalid api key"}}')

    assert err.code == AIErrorCode.AUTH_ERROR
    assert "invalid api key" in err.message


def test_429_is_rate_limited_and_retryable():
    err = from_http_status(429, '{"error":{"message":"rate limit exceeded"}}')

    assert err.code == AIErrorCode.RATE_LIMITED
    assert err.retryable is True


def test_502_is_server_error_and_retryable():
    err = from_http_status(502, '{"error":{"message":"bad gateway"}}')

    assert err.code == AIErrorCode.SERVER_ERROR
    assert err.retryable is True
    assert "bad gateway" in err.message


def test_secret_like_string_is_redacted():
    """`message` 不得携带密钥特征串（`errors.py` 安全约束）。"""
    err = from_http_status(403, '{"error":{"message":"bad key sk-abcdef123456 rejected"}}')

    assert "sk-abcdef123456" not in err.message
    assert "[REDACTED]" in err.message


def test_oversized_body_is_truncated():
    """超长 body 必须截断（避免 DATA-009/日志被淹没）。"""
    err = from_http_status(500, "x" * 5000)

    assert err.message.endswith("…")
    assert len(err.message) <= 320, "固定文案 + ≤200 字符摘要"


def test_cloudflare_html_body_is_folded():
    """HTML（如 Cloudflare 502 页）折叠为可读标注，不原样塞入。"""
    html = (
        "<!DOCTYPE html><html><head><title>502 Bad Gateway</title></head>"
        "<body><h1>502 Bad Gateway</h1><p>cloudflare</p></body></html>"
    )
    err = from_http_status(502, html)

    assert err.code == AIErrorCode.SERVER_ERROR
    assert "<!DOCTYPE" not in err.message
    assert "<html>" in err.message


def test_as_dict_keeps_contract_shape():
    """DATA-009 `error` 落库结构不变（`code` + `message`）。"""
    payload = from_http_status(403, QUOTA_BODY).as_dict()

    assert set(payload) == {"code", "message"}
    assert payload["code"] == "quota_exhausted"
