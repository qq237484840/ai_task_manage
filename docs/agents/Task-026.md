# Task-026 —— `BUG-008` + `BUG-009` 合并修复：DATA-009 写入失败不污染事务 + 可观测

- **Task ID**：Task-026 ｜ **Agent**：**`AGENT-AI`**（横切 `app/core/ai/` 所有者）｜ **Module**：共享/基础设施（非 Module ID）
- **签发**：Project Master，2026-09-29 ｜ **状态**：**已完成**（实施 + 用例齐备；验收见 `Task-027`，8 条全通过） ｜ **Kind**：**缺陷修复（小）**
- **上游**：`BUG-008`（中，`Confirmed`）、`BUG-009`（**高**，`Confirmed`）—— **同源**（SQLite 单写者锁竞争）**同写区**，故**合并为一个修复任务**；`Task-025` 真机验收已给出**基线对照**证据
- **写区（授权）**：`backend/app/core/ai/records.py`（**唯一生产代码**）+ `backend/tests/**`（新增用例）
- **禁止改**：`m001/**`、`m002/**`、`frontend/**`、`core/ai/**` 其它文件、`core/database.py`、`docs/**`（验收任务书除外）

## 1. Objective

DATA-009（AI 调用留痕）写入失败时：① **不得污染调用方事务**（根除 `BUG-009` 的 `PendingRollbackError` → `500`）；② **不得静默丢失**（根除 `BUG-008`）：瞬时锁竞争**有限重试**，仍失败则**计数 + `error` 日志**使留痕缺失**可被观测**。

## 2. 根因与修复口径

| 缺陷 | 根因（`records.py`） | 修复 |
| --- | --- | --- |
| **BUG-009**（高） | `record_call` 的 `except` **只 warning、不 `session.rollback()`** → flush 失败后 Session 进「待回滚」→ 调用方随后的 `commit`/查询抛 `PendingRollbackError` → `API-M002-007` **500**（`m002/api/link_routes.py:88`） | **任何**失败路径（含 `_ensure_table` 失败）都必须 `session.rollback()`，**保证 Session 可用**地返回 `None` |
| **BUG-008**（中） | 同上 `except` **无重试、无计数、无补偿** → 留痕丢失只出现在 warning 日志 | ① 对**瞬时锁竞争**（`sqlalchemy.exc.OperationalError`）作**有限重试**（总 2 次尝试 + 短退避）；② 仍失败 → 累计 `dropped_record_count()` 并以 **`error`** 级日志输出（含累计值 / `capability` / `request_id`） |

**重试口径（重要）**：pysqlite 默认 `timeout=5s`，**单次尝试已自带 5s 等待**；故重试次数取 **2**（首试 + 1 次重试）——再增加只会**线性放大最坏时延**而不提高成功率。退避 50ms 仅用于跨过「锁刚释放」的窗口。

## 3. 实施清单

| # | 项 | 要求 |
| --- | --- | --- |
| 1 | `_rollback_quietly(session)` | 内部再包 `try/except`（rollback 自身失败也不得抛出） |
| 2 | 写入循环 | 总 2 次尝试；仅对 `OperationalError` 重试；每次失败先 `rollback()`；退避 `0.05s × attempt` |
| 3 | `_ensure_table` 失败 | 同样 `rollback()` + 计数（不污染事务） |
| 4 | 可观测 | `dropped_record_count() -> int`（进程内累计，线程安全）+ 终态 `logger.error`（含 `dropped=` 累计值）；日志由 `warning` 升级为 `error` |
| 5 | 语义不变 | `session=None` 仍 no-op 返回 `None`；成功仍返回 `AICallRecord`；**字段/契约零变更**（DATA-009 不变） |

## 4. 验收清单（由 `Task-027` 执行）

| # | 项 | 要求 |
| --- | --- | --- |
| 1 | 写失败 → Session 可用 | `record_call` 返回 `None`，且同一 Session 随后的 `commit()` **不再**抛 `PendingRollbackError`（**判别力用例**） |
| 2 | 锁释放后重试成功 | **真实 SQLite 锁**（自建短 `timeout` 引擎，无替身）：持锁 → 首次尝试失败 → 释放 → 重试写入成功 |
| 3 | 端点不再 500 | 构造 DATA-009 写入失败 → `GET /photos/{id}/link-suggestions?retry=true` 仍 **200**（业务结果不受影响） |
| 4 | 计数与日志 | `dropped_record_count()` 递增；终态为 `error` 级日志 |
| 5 | 既有用例不减 | `tests/unit/test_ai_records.py` 5 例全绿（含 `session=None` no-op、每次尝试各一条 error 记录） |
| 6 | 全量回归 | **≥ 278**（基线 278 + 新增）**0 failed / 0 errors / 0 skipped**；`read_lints = 0` |
| 7 | 真机复现（关键） | 持写锁构造 → **不再 500**（对比 `Task-025` 记录的 `RESP_STATUS=500` 原文）；解锁后 200 |
| 8 | 只读边界 | 除 `records.py` 外**生产代码零改动**（`git status` + mtime 双证） |

## 5. 证据纪律（PM 铁律）

- 症状在**事务/端点层** → 证据必须到**端点级**（`HTTP 200`）与**真机级**（持锁构造），不得只以单通过关；
- 桩/替身须 docstring 标注；**核心结论（#2/#3/#7）不得仅依赖桩**（#2 用真实 SQLite 锁，#7 用真机）；
- 红→绿须**亲手回退**取得（回退 = 移除 `rollback()` / 关闭重试），取证后**必须还原**；
- 「零改动」须 `git status --porcelain` + **mtime** 双证。

## 6. 已知边界（本任务**不**处理，登记待评估）

- **WAL / `busy_timeout` 全局调优**（`core/database.py`）：可从结构上降低「读者阻塞写者」概率，但属**全局行为变更**（新增 `-wal`/`-shm` 文件、影响全部并发路径）→ **须独立 CR 评估**；
- **健康检查暴露** `ai_records_dropped`：本任务仅提供 `dropped_record_count()` 计数 + 日志，端点/健康检查接线**另立**；
- **同照片并发建议去重**（`suggestion_scheduler` × 同步 `retry`）：属调度策略，另立。

## 7. 任务书签发信息
- **提案人**：Project Master ｜ **日期**：2026-09-29 ｜ **状态**：**已完成**
- **执行方**：`AGENT-AI`（**本机无具备写权限的执行 subagent → PM 代执行**，不构成独立第三方复核，如实标注）
- **交付**：`app/core/ai/records.py`（`_rollback_quietly` / 有限重试 / `dropped_record_count()`）+ 单测 4 例 + 集成 1 例；全量回归 **283 / 0 / 0 / 0**；证据见 `docs/agents/Task-027.md §5`
- **验收方**：`Task-027`（8 条清单）
