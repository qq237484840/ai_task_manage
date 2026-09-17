# Task-025 任务书 —— `CR-006` 子项 B 验收：`last_attempt` 暴露 AI 失败原因

- **Task ID**：Task-025 ｜ **Agent**：`AGENT-M002`（或 Project Master 直接验收）｜ **Module**：M002（验收）
- **签发**：Project Master，2026-09-17 ｜ **状态**：**已完成（§2 八条全通过；真机 11/11；两组红→绿）** ｜ **Kind**：**验收（只读 + 证据，中）**
- **上游**：`Task-024` 必须已完成并通过自测（契约 v0.4.4 + 实施 + 用例 + 回归）
- **写区（授权）**：`backend/tests/integration/**`（必要时补验收用例）、`.e2e/**`（一次性真机脚本，**用后即删**）、`docs/agents/Task-025.md`（§5）
- **禁止改**：所有生产代码（`backend/app/**`、`frontend/src/**`）、其余 `docs/**` —— **只读验收**（红→绿取证期间的临时改动**必须还原**）

## 1. Objective

用**可复现命令 + 原文输出**确认：`CR-006` 子项 B 在**真实装配路径**下成立 —— `API-M002-007` 如实暴露 AI 失败原因、**成功/无记录时不误导**、留痕读取失败**不阻断主流程**、既有行为**零回归**。

## 2. 验收清单（逐条取证）

| # | 项 | 要求 |
| --- | --- | --- |
| 1 | **字段与键集** | `API-M002-007` 响应含 `last_attempt`；键集 = 基线 3 键 + 1（**多=[] 少=[]**）；**成功 → `null`**（且数据面确有 `status=ok` 留痕） |
| 2 | **失败分支（真实装配路径）** | `real` + 禁 Mock 兜底（无凭据）→ `last_attempt.code = provider_unavailable`；`suggestions=[]` / `status=unassigned` **既有降级语义不变** |
| 3 | **DATA-009 消费正确性** | 响应内容 = **库内实读**（`code`/`message` 逐字一致）；检索键 = `json_extract(input_ref,'$.photo_id')` + `capability='photo_link_suggest'`；**仅** `status='error'` 的记录被暴露（成功记录不得被误读为失败） |
| 4 | **脱敏 + 截断** | 含 `sk-` 特征串的三方响应 → 对外 `message` **无密钥** + 含 `[REDACTED]`；**三方摘要 ≤200 字**（`BUG-005` 约束） |
| 5 | **向后兼容** | 缺省/无记录 → `null`；`retry=true` 语义不变（仍触发建议且**不依赖** `last_attempt`）；前端零消费不影响 |
| 6 | **不阻断** | DATA-009 **表不存在 / 读取异常** → `null` + warning，端点仍 `200`（**须有判别力证据**：移除容错后应失败） |
| 7 | **全量回归** | `pytest` **278 / 0 failed / 0 errors / 0 skipped**；`read_lints = 0` |
| 8 | **只读边界 + 迁移可复现** | 验收期生产代码**零写入**（`git status` + mtime 双证）；`-Seed` 后**真机**（8010）复现响应字段集 |

## 3. 证据纪律（PM 铁律）

- **症状在哪一层，证据就到哪一层**：本子项症状在**响应面**且根因在**数据面关联检索** → 必须**数据面实读**佐证（不得只看响应自述）；
- 桩/替身**必须** docstring 标注并报备；核心结论（#2/#3）**不得仅依赖桩**（本任务实测**零 AI 替身**）；
- 「零改动」须 `git status --porcelain` + **mtime** 双证；红→绿须**亲手回退**取得（且取证后**还原**）；
- 用例级 / 真机级 / 浏览器级证据**分域标注**（本子项**前端零消费** → 浏览器级可不做，但须**显式说明**并给出替代证据）。

## 4. DoD

- [ ] §2 八条逐条取证（命令 + 原文）
- [ ] 至少 2 条**红→绿**判别力原文（#2 检索键 / #6 容错）
- [ ] 写区合规（`git status --porcelain` + mtime）：验收期**生产代码零写入**
- [ ] `read_lints` = 0
- [ ] §5 报告（含分域证据与遗留）；发现的问题**只登记**（ID 由 PM 分配）

## 5. 执行方报告（七段式）

> **执行者说明**：本任务由 **PM 代执行**（本机无具备写权限的执行 subagent）；验收对象 `Task-024` 亦为 PM 代执行 → **不构成独立第三方验收**，限制如实标注。
> **写区扩权说明（PM 裁决）**：§1 写区已含 `.e2e/**`（一次性真机脚本，**用后即删、不入库**）与 `backend/tests/integration/**`；**真机脚本已移出仓库**（`%TEMP%\t025_trash`）。

### ① 状态

**完成**。§2 八条清单**全部通过**；真机 **11/11 PASS**；**两组红→绿**判别力成立（#2 检索键 / #6 容错）；
**验收期生产代码零写入**（红取证改动已还原，`git status` 复核）；**验收发现并补强 1 处覆盖缺口**（#6 用例原本**未触达** `except` 分支）；
**验收发现 1 个新缺陷 `BUG-009`（高，`Confirmed`，只登记不修）**，含**基线对照**证明**非本子项引入**。

### ② 验收清单逐条结论（证据原文）

| # | 项 | 结论 | 证据原文 |
| --- | --- | --- | --- |
| 1 | **字段与键集** | **通过** | 真机 `PASS 01-key-set-baseline+last_attempt :: keys=['last_attempt','photo_id','status','suggestions']`；用例 `test_last_attempt_is_null_when_latest_attempt_succeeds`（**成功 → `null`**，且数据面先确认 `{r.status for r in rows} == {'ok'}`）+ `test_last_attempt_is_null_without_records_and_keys_are_backward_compatible`（`set(body) == 基线 3 键 + last_attempt`，**多=[] 少=[]**） |
| 2 | **失败分支（真实装配路径）** | **通过** | 真机（**真实三方**，非构造）：`PASS 02-failure-exposed :: last_attempt={'code': 'server_error', 'message': '三方服务错误 503 \| 三方摘要: model_not_found: No available channel for model qwen3.8-flash under group default (distributor) (request id: …)'}` + `PASS 02-degrade-semantics-unchanged :: status=unassigned n=0`；用例侧另有 `provider_unavailable`（`real` + 无凭据，零 AI 替身） |
| 3 | **DATA-009 消费正确性** | **通过** | 真机 `PASS 03-data009-record-for-photo :: n=6`、`PASS 03-response==db-read-back :: db_code=server_error resp_code=server_error`、`PASS 03-only-error-exposed :: statuses=['error'×6]`（**按 `json_extract(input_ref,'$.photo_id')` + `capability` 检索**，响应与库内实读逐字一致） |
| 4 | **脱敏 + 截断** | **通过** | 用例 `test_last_attempt_message_is_redacted_and_bounded`（`sk-` 剔除 + `[REDACTED]` + 摘要 `len ≤ 201` + 整体 ≤300）；真机 `PASS 04-redaction-no-secret :: msg_len=168` |
| 5 | **向后兼容** | **通过** | 键集哨兵（见 #1）；真机 `PASS 05-plain-get-no-new-call :: records 6->6 status=200`、`PASS 05-plain-get-keeps-last_attempt`（`retry` 缺省不触发 AI、语义不变）；`e2e` 键集哨兵同步（**仅 1 行**，见 §4） |
| 6 | **不阻断** | **通过（覆盖补强）** | `create_all` 已建出 `ai_call_records` → 原「无记录」断言**触达不到 `except`** → 已改为**显式 `DROP TABLE`**（真实失败模式）后断言 `200` + `last_attempt=null`；红取证见 ③-B |
| 7 | **全量回归** | **通过** | `tests=278 failures=0 errors=0 skipped=0`、`PYTEST_EXIT=0`；`read_lints=0` |
| 8 | **只读边界 + 迁移可复现** | **通过** | 真机（`:8011` + 独立库 `_tmp_t025.db`）两阶段复现（`prepare`：`auto` 造 M001 窗口/学科子任务 → `verify`：`real` + 禁兜底）；验收期**生产代码零写入**（红取证已还原，`git status` 复核）；临时脚本/库/日志已移出仓库 |

### ③ 红→绿判别力（**亲手取证，两组**）

**A. 检索键（#2，核心）**：把检索键回退为错误键（复现原缺陷形态 `AICallRecord.request_id == photo_id`）

```
FF..  → FAILED test_last_attempt_exposes_failure_from_data009
        E AssertionError: {'photo_id': ..., 'status': 'unassigned', 'last_attempt': None, 'suggestions': []}
        FAILED test_last_attempt_message_is_redacted_and_bounded
RED_EXIT=1        # 还原为 json_extract(input_ref,'$.photo_id') → ".... [100%]"  GREEN_EXIT=0
```

**B. 容错分支（#6）**：使 `_last_attempt` 的 `except` 失效（`except ZeroDivisionError`）

```
...F  → FAILED test_last_attempt_is_null_without_records_and_keys_are_backward_compatible
        sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: ai_call_records
        [SQL: SELECT ... WHERE json_extract(ai_call_records.input_ref, ?) = ? ...]
RED6_EXIT=1       # 还原 → ".... [100%]"  GREEN6_EXIT=0
```

→ 证明**留痕读取的容错分支**是「不阻断」的唯一保障。

### ④ 最小扩权（1 处，**仅 1 行**）

- `tests/e2e/test_acceptance_scenarios.py::test_scenario5_*` 响应键集哨兵：`{photo_id, status, suggestions}` → `+ last_attempt`
- **理由**：v0.4.4 为**契约内的新增可选字段**，哨兵须同步；断言仍**逐项从严**（多=[] 少=[]）；
- **其余断言 / 用例语义 / 测试基线零变更**（回归 278 = 基线 274 + 本子项新增 4）。

### ⑤ 契约与治理同步（已由 `Task-024 §5 ⑤` 完成，本任务复核一致）

`MODULE_API.md`（v0.4.4 + DTO + 正文，含**检索键**与**截断口径**的准确表述）、`MODULE_CONTRACT.md`、`MODULE_CHANGELOG.md`（v0.4.4 条目）、`MODULE_REGISTRY.md`（2 处版本链）、`API_REGISTRY.md`、`changes/CR-006.md`、`PROJECT_STATUS.md` / `CHANGELOG.md`（`v0.26.0`）。

### ⑥ 验收发现的新缺陷：**`BUG-009`（高，`Confirmed`，只登记不修）**

**现象**：真机（上传触发的**后台建议线程** × `retry=true` 并发写 DATA-009）→
`sqlite3.OperationalError: database is locked`（`INSERT INTO ai_call_records`）→ 同 Session `db.commit()`
抛 `PendingRollbackError` → **`GET …?retry=true` 返回 500**。

**根因（读码）**：`app/core/ai/records.py:100-104` 的 `except` **只 warning、不 `session.rollback()`** →
Session 进入「待回滚」→ `m002/api/link_routes.py:88` 的同 Session `commit()` 失败。

**确定性复现 + 基线对照**：

```
# 修复版（持写锁构造）
LOCK_HELD
RESP_STATUS=500    RESP_BODY={"code":"INTERNAL_ERROR","message":"服务器内部错误","request_id":"-"}
LOCK_RELEASED
AFTER_UNLOCK_STATUS=200
# 基线对照（git stash 回退本子项代码后重启同配置服务）
LOCK_HELD → RESP_STATUS=500        # ← 基线同样 500 ⇒ 既有缺陷，非本子项引入
```

**影响修正**：`BUG-008` 原判「**主链路不受影响**」在**并发写**场景下**不成立**（本单级别 **高**）。
**建议**：与 `BUG-008` **合并为一个修复任务**（同源、同写区 `app/core/ai/**`），优先级**置于 `CR-006` 子项 C 之前**。
详见 `docs/changes/BUG-009.md`。

### ⑦ 遗留与边界

- **`input_ref` 无独立列/索引** → `json_extract` 检索（V1 数据量小，真机未见瓶颈）；如需索引须 `app/core/ai` 侧变更（走 CR）；
- **`message` 长度口径**：截断约束施加于**三方摘要**（≤200 字），`message` = 统一文案前缀 + 摘要 → 已写入 `MODULE_API.md` 明确，避免误读；
- **浏览器级证据**：本子项**前端零消费**（`frontend/**` 零改动）→ 无浏览器级证据；替代证据 = **真机 API 级 11/11** + 集成级 4 例（**分域标注**）；
- **`BUG-008` / `BUG-009` 均未修复**（本任务只登记）。
