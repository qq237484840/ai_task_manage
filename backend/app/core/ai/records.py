"""DATA-009 —— AI 调用记录（可追溯链，含 Mock 标注）。

必填字段（REQ-008 / DATA-009）：model / prompt_version / request_id / latency / token_usage /
result / confidence / error；另附 capability / provider / attempt / mock / input_ref 便于追溯。

写入策略：
- 复用调用方 `Session`（与业务事务同源，**flush 不 commit**，提交由调用方决定）；
- 表在首次写入时按需创建（`ai_call_records` 不依赖 `main.py` 预导入，避免越权改 PM 独占文件）；
- **写入失败不得污染调用方事务**（`BUG-009`）：任何失败路径都先 `session.rollback()` —— 否则
  Session 进入「待回滚」状态，调用方随后的 `commit`/查询会抛 `PendingRollbackError`（曾致端点 500）；
- **留痕丢失不得静默**（`BUG-008`）：瞬时锁竞争（`OperationalError`）作**有限重试**，
  仍失败则累计 `dropped_record_count()` 并以 **`error`** 级日志输出。
"""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
import weakref
from typing import Any

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base
from app.core.times import now_iso

_logger = logging.getLogger("uvicorn.error")


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


#: DATA-009 写入的**总尝试次数**（首试 + 1 次重试）。pysqlite 默认 `timeout=5s` —— **单次尝试
#: 已自带 5s 等待**，再多只会**线性放大最坏时延**而不提高成功率，故取 2。
_RECORD_MAX_ATTEMPTS = 2

#: 重试退避基数（秒）：第 `attempt` 次失败后等待 `_RECORD_BACKOFF_BASE * attempt`
#: （用于跨过「锁刚释放」窗口；真正的等待由 pysqlite `busy_timeout` 承担）。
_RECORD_BACKOFF_BASE = 0.05

#: 进程内累计「DATA-009 写入失败 = 留痕丢失」次数（`BUG-008` 可观测性出口）
_dropped_lock = threading.Lock()
_dropped_records = 0


def dropped_record_count() -> int:
    """累计的 DATA-009 **留痕丢失**次数（单调递增，线程安全）。

    每丢失一条记录即 +1，并同时以 `error` 级日志输出（含累计值 / `capability` / `request_id`）
    —— 使「留痕缺失」**可被观测**，而非只留一条 warning（`BUG-008`）。
    """
    with _dropped_lock:
        return _dropped_records


def _note_dropped(exc: BaseException, *, capability: str, request_id: str) -> None:
    global _dropped_records
    with _dropped_lock:
        _dropped_records += 1
        total = _dropped_records
    _logger.error(
        "DATA-009 留痕丢失（dropped=%s）capability=%s request_id=%s: %s",
        total,
        capability,
        request_id,
        exc,
    )


def _rollback_quietly(session: Session) -> None:
    """`flush` 失败后**必须**回滚 —— 否则 Session 进入「待回滚」状态，调用方随后的
    `commit`/查询会抛 `PendingRollbackError`（`BUG-009`：曾致 `API-M002-007` 500）。

    回滚自身失败亦不得抛出（留痕写入绝不影响主链路），仅记录。
    """
    try:
        session.rollback()
    except Exception:  # noqa: BLE001 - 回滚失败已无法再补救
        _logger.warning("DATA-009 写入失败后回滚失败（Session 可能不可用）", exc_info=True)


def _build_record(fields: dict[str, Any]) -> AICallRecord:
    """按 DATA-009 字段规格构造一条记录（纯构造，无副作用）。"""
    return AICallRecord(
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


def record_call(session: Session | None, **fields: Any) -> AICallRecord | None:
    """写入一条 DATA-009 记录；`session=None` 时跳过（离线/纯计算场景）。

    返回 `None` = **未留痕** —— 已计入 `dropped_record_count()` 并记 `error` 日志（`BUG-008`）；
    **无论成败都不会污染调用方事务**（`BUG-009`）：每条失败路径都先 `session.rollback()`。
    """
    if session is None:
        return None
    capability = str(fields.get("capability") or "unknown")
    request_id = str(fields.get("request_id") or "")
    try:
        _ensure_table(session.get_bind())
    except Exception as exc:  # noqa: BLE001 - 建表失败不得中断主链路
        _rollback_quietly(session)
        _note_dropped(exc, capability=capability, request_id=request_id)
        return None

    for attempt in range(1, _RECORD_MAX_ATTEMPTS + 1):
        try:
            record = _build_record(fields)
            session.add(record)
            session.flush()
            return record
        except Exception as exc:  # noqa: BLE001 - 审计写入失败不得中断主链路
            _rollback_quietly(session)
            # 仅**瞬时**故障（SQLite 锁竞争 / I/O）重试；其余（如 schema 不符）立即终止，
            # 避免对确定性错误做无意义重试。
            if isinstance(exc, OperationalError) and attempt < _RECORD_MAX_ATTEMPTS:
                time.sleep(_RECORD_BACKOFF_BASE * attempt)
                continue
            _note_dropped(exc, capability=capability, request_id=request_id)
            return None
    return None  # pragma: no cover - 循环内必 return


def list_calls_by_request_id(session: Session, request_id: str) -> list[AICallRecord]:
    """按 `request_id` 追溯某次能力调用的全部尝试记录。"""
    _ensure_table(session.get_bind())
    return (
        session.query(AICallRecord)
        .filter(AICallRecord.request_id == request_id)
        .order_by(AICallRecord.attempt.asc(), AICallRecord.created_at.asc())
        .all()
    )


__all__ = [
    "AICallRecord",
    "dropped_record_count",
    "list_calls_by_request_id",
    "record_call",
]
