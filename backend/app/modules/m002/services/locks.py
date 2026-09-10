"""进程级键互斥（契约 D8 并发控制）。

- 同批次上传 / 同任务归属 / 单照片删除以命名键串行化；SQLite 单库单写者 + 本锁 →
  极端争用 409（上传处捕获 IntegrityError/OperationalError 转 concurrent_conflict）。
- 语义：锁粒度越小并发越好；键命名 {域}:{family_id}:{业务id}。
"""
from __future__ import annotations

import threading
from contextlib import contextmanager

_guard = threading.Lock()
_keys: dict[str, dict] = {}


@contextmanager
def keyed_lock(key: str):
    with _guard:
        entry = _keys.setdefault(key, {"lock": threading.Lock(), "users": 0})
        entry["users"] += 1
        lock: threading.Lock = entry["lock"]
    try:
        with lock:
            yield
    finally:
        with _guard:
            entry["users"] -= 1
            if entry["users"] == 0:
                _keys.pop(key, None)
