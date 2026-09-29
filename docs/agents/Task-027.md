# Task-027 任务书 —— `BUG-008` + `BUG-009` 合并修复验收（`Task-026`）

- **Task ID**：Task-027 ｜ **Agent**：`AGENT-AI`（或 Project Master 直接验收）｜ **Module**：共享/基础设施（验收）
- **签发**：Project Master，2026-09-29 ｜ **状态**：**已签发（待执行）** ｜ **Kind**：**验收（只读 + 证据，中）**
- **上游**：`Task-026` 必须已完成并通过自测
- **写区（授权）**：`backend/tests/**`（必要时补验收用例）、`.e2e/**`（一次性真机脚本，**用后即删**）、`docs/agents/Task-027.md`（§5）
- **禁止改**：所有生产代码（`backend/app/**`、`frontend/src/**`）、其余 `docs/**` —— **只读验收**（红取证期间的临时改动**必须还原**）

## 1. Objective

用**可复现命令 + 原文输出**确认：DATA-009 写入失败时 ① **不污染调用方事务**（根除 500）、② **留痕丢失可观测**、③ 瞬时锁竞争可**重试成功**、④ 既有行为**零回归**。

## 2. 验收清单（逐条取证）

| # | 项 | 要求 |
| --- | --- | --- |
| 1 | **写失败不污染事务** | `record_call` 返回 `None` 后，同一 Session 可 `commit()` / 查询（**判别力**：移除 `rollback()` 必败） |
| 2 | **瞬时锁 → 重试成功** | **真实 SQLite 锁**：首试失败 → 锁释放 → 重试写入成功且**不计入丢失**（**判别力**：关闭重试必败） |
| 3 | **端点不再 500** | 构造写入失败（真实删表）→ `GET /photos/{id}/link-suggestions?retry=true` 仍 **200**，且 **AI 建议照常落库**（回滚不得吞掉业务结果） |
| 4 | **丢失可观测** | `dropped_record_count()` 递增；终态日志由 `warning` → **`error`**（含 `dropped=` 累计值 / `capability` / `request_id`） |
| 5 | **既有用例不减** | `tests/unit/test_ai_records.py` 5 例全绿（含 `session=None` no-op、每次尝试各一条 error 记录） |
| 6 | **全量回归** | **283 / 0 failed / 0 errors / 0 skipped**（基线 278 + 新增 5）；`read_lints = 0` |
| 7 | **真机复现（关键）** | 持写锁构造（`BEGIN IMMEDIATE`）→ `retry=true` **不再 500**（对照 `Task-025` 记录的 `RESP_STATUS=500` 原文，同一构造）；解锁后 200 且留痕恢复 |
| 8 | **只读边界** | 除 `app/core/ai/records.py` 外**生产代码零改动**（`git status` + mtime 双证）；临时脚本/库/日志已移出仓库 |

## 3. 证据纪律（PM 铁律）

- 症状在**事务/端点层** → 证据必须到**端点级**（HTTP 200）与**真机级**（持锁构造），不得只以单通过关；
- 桩/替身须 docstring 标注；**核心结论不得仅依赖桩**（#2 用真实 SQLite 锁，#7 用真机）；
- 红→绿须**亲手回退**取得（回退 = 移除 `rollback()` / 关闭重试），取证后**必须还原**；
- **时序类用例须说明时序假设**（SQLite busy handler 会**超出**设定 `timeout`，须以 `timeout=0` 消除等待使时序确定）。

## 4. DoD

- [ ] §2 八条逐条取证（命令 + 原文）
- [ ] 至少 2 条**红→绿**判别力原文（`rollback` / 重试）
- [ ] 写区合规（`git status --porcelain` + mtime）：验收期**生产代码零写入**
- [ ] `read_lints` = 0
- [ ] §5 报告（含分域证据与遗留）；发现的问题**只登记**（ID 由 PM 分配）

## 5. 执行方报告（七段式）

> **执行者说明**：本任务由 **PM 代执行**（本机无具备写权限的执行 subagent）；修复方 `Task-026` 亦为 PM 代执行 → **不构成独立第三方验收**，限制如实标注。
> **写区扩权说明（PM 裁决）**：§1 写区已含 `.e2e/**`（一次性真机脚本）与 `backend/tests/**`；**真机脚本/库/日志已移出仓库**（`%TEMP%\t026_trash`），工作区仅余预期改动。

### ① 状态

**完成**。§2 八条**全部通过**；真机 **7/7 PASS**；**两组红→绿**判别力成立（`rollback` / 重试）；
全量回归 **283 / 0 / 0 / 0**（基线 278 + 新增 5）；`read_lints=0`；**生产代码仅 `app/core/ai/records.py` 改动**（`git status` 复核）。
**验收发现并修正 1 处用例判别力缺口**（重试用例首版**对重试无判别力**，见 ③-B 与 ⑦）。

### ② 验收清单逐条结论（证据原文）

| # | 项 | 结论 | 证据原文 |
| --- | --- | --- | --- |
| 1 | **写失败不污染事务** | **通过** | 用例 `test_record_call_write_failure_keeps_session_usable`（**真实删表**造写入失败）→ `record_call` 返回 `None` 后 `session.commit()` + `select 1` 正常；另有 `test_record_call_failure_does_not_break_followup_business_write`（同一事务后续业务写入照常提交） |
| 2 | **瞬时锁 → 重试成功** | **通过** | 用例 `test_record_call_retries_once_when_lock_is_released`（**真实 SQLite 锁** + 第二连接持写锁，引擎 `timeout=0`）：首试立即失败 → 退避 `0.05s` → 持锁方 `0.02s` 释放 → 重试写入成功；`dropped_record_count()` **不变** |
| 3 | **端点不再 500** | **通过** | 用例 `test_link_suggestions_returns_200_when_data009_write_fails`：真实删表 → `GET /photos/{id}/link-suggestions?retry=true` → **`200`**、`last_attempt=null`、**`suggestions` 非空且 `status=suggested`**（回滚**未吞掉** AI 建议） |
| 4 | **丢失可观测** | **通过** | 用例断言 `dropped_record_count()` 递增；**真机服务端日志 5 条 `ERROR`**：`DATA-009 留痕丢失（dropped=1…5）capability=photo_link_suggest request_id=…: (sqlite3.OperationalError) database is locked`（日志级别由 `warning` 升至 `error`） |
| 5 | **既有用例不减** | **通过** | `tests/unit/test_ai_records.py` 5 例全绿（含 `session=None` no-op、`max_retries` 下每次尝试各 1 条 error 记录、Mock 标注） |
| 6 | **全量回归** | **通过** | `tests=283 failures=0 errors=0 skipped=0`、`PYTEST_EXIT=0`；`read_lints=0` |
| 7 | **真机复现（关键）** | **通过** | 真机 **7/7 PASS**（`:8011` + 独立库 `_tmp_t026.db`，两阶段）：`PASS 01-locked-retry-not-500 :: status=200 elapsed=23.5s body={…"status":"unassigned","last_attempt":null}`（**对照 `Task-025` 同构造原文 `RESP_STATUS=500`**）；`PASS 04-lock-construction-effective :: records 0->0`（持锁期间写入**确实**失败 = 构造有效）；`PASS 06-after-unlock-records-restored :: records 0->1`；`PASS 07-last_attempt-matches-latest-attempt :: latest_status=ok last_attempt=None` |
| 8 | **只读边界** | **通过** | 验收期**仅** `app/core/ai/records.py` 为生产改动（红取证已还原，`git status` 复核）；临时脚本/库/日志已全部移出仓库 |

### ③ 红→绿判别力（**亲手取证，两组**）

**A. `rollback`（`BUG-009` 根治点）**：把 `_rollback_quietly` 置为空操作（= 修复前「只 warning、不 rollback」）

```
FF.FF → FAILED test_record_call_write_failure_keeps_session_usable
        sqlalchemy.exc.PendingRollbackError: This Session's transaction has been rolled back
        due to a previous exception during flush ... Original exception was:
        (sqlite3.OperationalError) no such table: ai_call_records
        FAILED test_record_call_failure_does_not_break_followup_business_write
        FAILED test_record_call_counts_drop_when_lock_is_never_released
        FAILED test_link_suggestions_returns_200_when_data009_write_fails  ← 端点级（500）
RED_EXIT=1        # 还原 → "..... [100%]"  GREEN_EXIT=0
```

**B. 重试策略（`BUG-008`）**：`_RECORD_MAX_ATTEMPTS = 1`（关闭重试）

```
..F. → FAILED test_record_call_retries_once_when_lock_is_released
       AssertionError: 锁释放后重试应成功写入
       assert None is not None
       ERROR uvicorn.error DATA-009 留痕丢失（dropped=3）... (sqlite3.OperationalError) database is locked
RED_RETRY_EXIT=1  # 还原为 2 → "..... [100%]"  GREEN_EXIT=0
```

### ④ 全量回归

```
tests=283 failures=0 errors=0 skipped=0   PYTEST_EXIT=0      （基线 278 + 新增 5：单测 4 + 集成 1）
read_lints = 0
```

### ⑤ 契约与数据面影响

**无契约变更**：DATA-009 字段、`API-M002-007` 响应、错误语义均不变；新增仅为 `records.py` 的**内部**可观测出口 `dropped_record_count()`（`__all__` 已导出）。

### ⑥ 遗留与边界（本任务**不**处理，已在 `Task-026 §6` 登记）

- **WAL / `busy_timeout` 全局调优未启用** —— 真机持锁期间**仍会丢失留痕**（现已计数 + `error` 日志，不再静默）；结构性根治（`core/database.py`）须独立 CR 评估；
- **持锁请求时延**：真机实测 `23.5s`（首轮 `63.5s`）= AI 层内部重试 ×（pysqlite `busy_timeout=5s` × 2 次写入尝试）叠加，属**既有** AI 重试与锁等待行为，**非本次引入**；若需收敛，须连同 WAL 与 `max_retries` 一并评估；
- **健康检查未接线**：`dropped_record_count()` 目前仅供日志/进程内查询，端点暴露另立。

### ⑦ 验收发现并修正的用例判别力缺口（`Task-023`/`Task-025` 同类教训的第三例）

重试用例**首版**（引擎 `timeout=0.1s`、持锁方 `0.12s` 释放）在**关闭重试**时**仍然通过** —— 根因：
**SQLite busy handler 会超出设定的 `timeout`**（`0.1s` 实测等到 ~`0.13s`），与释放时刻撞车 → 首试**直接成功**，
用例**从未触发重试**却仍判绿。

→ 已改为引擎 `timeout=0`（遇锁**立即** `SQLITE_BUSY`，无等待）+ 持锁方 `0.02s` 释放 → 时序确定，
关闭重试即 `RED_RETRY_EXIT=1`（见 ③-B）。**教训：时序类用例必须消除「隐性等待」，并以红取证确认其判别力。**
