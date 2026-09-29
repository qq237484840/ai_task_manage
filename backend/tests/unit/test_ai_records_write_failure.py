"""DATA-009 写入失败语义（`BUG-008` / `BUG-009` 合并修复，`Task-026`）。

覆盖：

1. **写失败 → 不得污染调用方事务**（`BUG-009`，高）：`record_call` 返回 `None` 后，同一 Session
   仍可 `commit()` / 查询（修复前 `flush` 失败不回滚 → Session 进「待回滚」→ `PendingRollbackError`
   → 调用方端点 500）；
2. **瞬时锁竞争 → 有限重试**（`BUG-008`，中）：真实 SQLite 持锁 → 首试失败 → 退避后锁被释放 →
   重试写入成功，**不计入丢失**；
3. **留痕丢失必须可观测**：失败即计入 `dropped_record_count()`。

**桩 / 替身说明（PM 铁律 ①）**：本文件**不注入任何替身** —— 用例 1 以**真实删表**（`DROP TABLE`）
制造写入失败；用例 2 用**真实 SQLite 文件库 + 第二连接持写锁**（仅把引擎 `timeout` 调为 0.1s
以缩短 busy 等待、使时序确定）。
"""
from __future__ import annotations

import sqlite3
import threading
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.ai.records import dropped_record_count, record_call


def _make_session(tmp_path, *, timeout: float | None = None):
    """真实 SQLite 文件库 + 独立 engine/session（`timeout` 可缩短 busy 等待）。"""
    db = tmp_path / "records.db"
    connect_args: dict = {"check_same_thread": False}
    if timeout is not None:
        connect_args["timeout"] = timeout
    engine = create_engine(
        f"sqlite:///{db.as_posix()}", connect_args=connect_args, future=True
    )
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    return engine, factory()


# ---------------------------------------------------------------- 1) BUG-009：不污染调用方事务
def test_record_call_write_failure_keeps_session_usable(tmp_path):
    """写失败**必须** rollback → 调用方随后的 `commit`/查询**不得**抛 `PendingRollbackError`。

    构造：**真实删表** —— 首次成功写入已使 bind 进入 `_ENSURED_BINDS`，故 `record_call`
    **不会**重新建表，INSERT 必然失败（`no such table`），且**不替换任何被测层**。
    """
    engine, session = _make_session(tmp_path)

    first = record_call(session, request_id="ok-1", capability="task_spec_parse", status="ok")
    assert first is not None, "前置：首次写入应成功（同时建表）"
    # `record_call` 仅 flush 不 commit → 首写事务仍持写锁，需先提交才能由别处删表
    session.commit()
    before = dropped_record_count()

    with engine.connect() as conn:
        conn.exec_driver_sql("DROP TABLE ai_call_records")

    result = record_call(
        session, request_id="lost-1", capability="photo_link_suggest", status="error"
    )

    assert result is None, "写入失败应返回 None（不抛、不中断主链路）"
    assert dropped_record_count() == before + 1, "留痕丢失必须被计数（BUG-008：不得静默）"
    # 关键断言（BUG-009 根治点）：调用方事务仍可用
    session.commit()  # 修复前：sqlalchemy.exc.PendingRollbackError
    assert session.execute(text("select 1")).scalar() == 1
    session.close()


def test_record_call_failure_does_not_break_followup_business_write(tmp_path):
    """写失败回滚后，调用方**同一事务内的后续业务写入**仍可成功提交（真实业务形态）。"""
    _, session = _make_session(tmp_path)
    assert record_call(session, request_id="ok-1", capability="task_spec_parse") is not None
    session.commit()  # 释放首写持有的写锁

    with session.get_bind().connect() as conn:
        conn.exec_driver_sql("DROP TABLE ai_call_records")

    assert record_call(session, request_id="lost-1", capability="photo_link_suggest") is None

    # 模拟业务侧继续在同一 Session 写入并提交
    session.execute(text("CREATE TABLE IF NOT EXISTS biz_probe (id INTEGER PRIMARY KEY)"))
    session.execute(text("INSERT INTO biz_probe (id) VALUES (1)"))
    session.commit()
    assert session.execute(text("select count(*) from biz_probe")).scalar() == 1
    session.close()


# ---------------------------------------------------------------- 2) BUG-008：瞬时锁 → 有限重试
def test_record_call_retries_once_when_lock_is_released(tmp_path):
    """瞬时锁竞争 → 首试失败 → 退避后锁已释放 → **重试写入成功**，且**不计入丢失**。

    时序（真实锁，无替身；引擎 `timeout=0` → 遇锁**立即**失败）：首试遇锁立即失败
    → 退避 `0.05s` → 持锁方在 `0.02s` 释放 → 重试成功。
    """
    path = tmp_path / "lock.db"
    # `timeout=0` = 无 busy 等待（遇锁**立即** `SQLITE_BUSY`）→ 时序确定；
    # 若用默认/较大 timeout，SQLite busy handler 会**超出**设定值（0.1s 实测等到 ~0.13s），
    # 与「释放时刻」撞车 → 用例会对重试是否发生**失去判别力**。
    engine = create_engine(
        f"sqlite:///{path.as_posix()}",
        connect_args={"timeout": 0, "check_same_thread": False},
        future=True,
    )
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    session = factory()
    assert record_call(session, request_id="prime", capability="prime", status="ok") is not None
    session.commit()  # 释放首写持有的写锁（否则持锁方无法 BEGIN IMMEDIATE）

    holder = sqlite3.connect(
        str(path), isolation_level=None, timeout=1.0, check_same_thread=False
    )
    holder.execute("BEGIN IMMEDIATE")
    holder.execute("UPDATE ai_call_records SET call_id = call_id WHERE rowid = 1")
    released = threading.Event()

    def _release() -> None:
        time.sleep(0.02)  # 早于退避后的重试（0.05s），晚于首试（立即失败）
        holder.execute("ROLLBACK")
        holder.close()
        released.set()

    worker = threading.Thread(target=_release, daemon=True)
    worker.start()

    before = dropped_record_count()
    try:
        record = record_call(
            session, request_id="retry-1", capability="photo_link_suggest", status="error"
        )
    finally:
        worker.join(timeout=5)

    assert released.is_set(), "持锁线程应已释放"
    assert record is not None, "锁释放后重试应成功写入"
    assert dropped_record_count() == before, "重试成功不得计入丢失"
    session.commit()
    session.close()


def test_record_call_counts_drop_when_lock_is_never_released(tmp_path):
    """锁**未**释放 → 重试耗尽 → 计入丢失，且 Session **仍可用**（不污染事务）。"""
    path = tmp_path / "held.db"
    engine = create_engine(
        f"sqlite:///{path.as_posix()}",
        connect_args={"timeout": 0, "check_same_thread": False},
        future=True,
    )
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    session = factory()
    assert record_call(session, request_id="prime", capability="prime", status="ok") is not None
    session.commit()  # 释放首写持有的写锁

    holder = sqlite3.connect(
        str(path), isolation_level=None, timeout=1.0, check_same_thread=False
    )
    holder.execute("BEGIN IMMEDIATE")
    holder.execute("UPDATE ai_call_records SET call_id = call_id WHERE rowid = 1")

    before = dropped_record_count()
    try:
        result = record_call(session, request_id="held-1", capability="photo_link_suggest")
    finally:
        holder.execute("ROLLBACK")
        holder.close()

    assert result is None
    assert dropped_record_count() == before + 1, "重试耗尽后必须计入丢失"
    session.commit()  # BUG-009：不得抛 PendingRollbackError
    assert session.execute(text("select 1")).scalar() == 1
    session.close()
