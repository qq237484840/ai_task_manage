"""挂接建议异步触发调度（进程内异步任务，非消息队列；ADR-013）。

- 默认实现 = 后台线程（daemon），不阻塞上传响应；失败仅告警，绝不影响上传事务。
- 可注入调度器：测试用同步内联调度保证确定性（set_scheduler）。
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable

logger = logging.getLogger("m002.suggestion")


def _thread_scheduler(runner: Callable[[], None]) -> None:
    def _run() -> None:
        try:
            runner()
        except Exception:  # noqa: BLE001 - 异步任务失败不得影响主流程
            logger.exception("async link suggestion failed")

    threading.Thread(target=_run, name="m002-suggestion", daemon=True).start()


_scheduler: Callable[[Callable[[], None]], None] = _thread_scheduler


def set_scheduler(scheduler: Callable[[Callable[[], None]], None] | None) -> None:
    """测试注入内联调度（lambda fn: fn()）；传 None 恢复后台线程。"""
    global _scheduler
    _scheduler = scheduler or _thread_scheduler


def schedule(runner: Callable[[], None]) -> None:
    _scheduler(runner)
