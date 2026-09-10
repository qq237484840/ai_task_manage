"""DATA-009 —— AI 调用记录（可追溯链，含 Mock 标注）。

必填字段（REQ-008 / DATA-009）：model / prompt_version / request_id / latency / token_usage /
result / confidence / error；另附 capability / provider / attempt / mock / input_ref 便于追溯。

写入策略：
- 复用调用方 `Session`（与业务事务同源，**flush 不 commit**，提交由调用方决定）；
- 表在首次写入时按需创建（`ai_call_records` 不依赖 `main.py` 预导入，避免越权改 PM 独占文件）。
"""
from __future__ import annotations

import json
import uuid
import weakref
from typing import Any

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base
from app.core.times import now_iso


def _uid() -> str:
    return str(uuid.uuid4())


class AICallRecord(Base):
    """AI 调用记录（DATA-009，Writer = `app/core/ai/`）。"""

    __tablename__ = "ai_call_records"

    call_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    family_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    capability: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provider_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_key: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_usage: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # ok | error
    mock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=now_iso)


_ENSURED_BINDS: "weakref.WeakSet[Any]" = weakref.WeakSet()


def _ensure_table(bind: Any) -> None:
    if bind is None or bind in _ENSURED_BINDS:
        return
    AICallRecord.__table__.create(bind=bind, checkfirst=True)
    _ENSURED_BINDS.add(bind)


def _dump(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False)


def record_call(session: Session | None, **fields: Any) -> AICallRecord | None:
    """写入一条 DATA-009 记录；`session=None` 时跳过（离线/纯计算场景）。"""
    if session is None:
        return None
    try:
        _ensure_table(session.get_bind())
        record = AICallRecord(
            request_id=str(fields.get("request_id") or _uid()),
            family_id=fields.get("family_id"),
            capability=str(fields.get("capability") or "unknown"),
            provider_kind=str(fields.get("provider_kind") or "unknown"),
            provider_name=str(fields.get("provider_name") or "unknown"),
            model=str(fields.get("model") or "unknown"),
            prompt_key=str(fields.get("prompt_key") or "unknown"),
            prompt_version=str(fields.get("prompt_version") or "unknown"),
            attempt=int(fields.get("attempt") or 1),
            latency_ms=int(fields.get("latency_ms") or 0),
            token_usage=_dump(fields.get("token_usage")),
            result=_dump(fields.get("result")),
            confidence=fields.get("confidence"),
            status=str(fields.get("status") or "error"),
            mock=bool(fields.get("mock")),
            error=_dump(fields.get("error")),
            input_ref=_dump(fields.get("input_ref")),
        )
        session.add(record)
        session.flush()
        return record
    except Exception:  # noqa: BLE001 - 审计写入失败不得中断主链路
        import logging

        logging.getLogger("uvicorn.error").warning("AI 调用记录写入失败", exc_info=True)
        return None


def list_calls_by_request_id(session: Session, request_id: str) -> list[AICallRecord]:
    """按 `request_id` 追溯某次能力调用的全部尝试记录。"""
    _ensure_table(session.get_bind())
    return (
        session.query(AICallRecord)
        .filter(AICallRecord.request_id == request_id)
        .order_by(AICallRecord.attempt.asc(), AICallRecord.created_at.asc())
        .all()
    )


__all__ = ["AICallRecord", "list_calls_by_request_id", "record_call"]
