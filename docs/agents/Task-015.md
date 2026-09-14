# Task-015 任务书 —— 修复 `BUG-005`：三方错误分类与留痕失真（403 余额/配额被误报「鉴权失败」+ 响应体丢弃）

- **Task ID**：Task-015 ｜ **Agent**：`AGENT-AI`（`ai-dev`）｜ **Module**：横切 `app/core/ai`（AI 接入层）
- **签发**：Project Master，2026-09-14 ｜ **状态**：**已签发（待执行）** ｜ **Kind**：**缺陷修复（中）**
- **缺陷单**：`docs/changes/BUG-005.md`（当前 `Confirmed`；**状态位由 PM 置位，执行方不得修改**）
- **启动前置（已满足）**：全量 `pytest` 基线 **237 tests / 0 failed / 0 errors / 0 skipped**；真实三方 AI 已联调通过（见 `docs/PROJECT_STATUS.md` 2026-09-14 条目）。
- **契约影响**：**无 API 契约变更**。`AIErrorCode` **新增一个枚举成员**（DATA-009 `error.code` 取值域扩大 = 向后兼容）；对应文档登记（`docs/DATA_MODEL.md` 取值表 / `docs/CONFIGURATION.md`）**由 PM 负责**，执行方不写 `docs/**`。
- **写区（授权）**：
  1. `backend/app/core/ai/errors.py`（**唯一**生产代码写区）
  2. `backend/tests/unit/test_ai_errors.py`（**新增文件**）
  3. `backend/tests/unit/test_ai_service.py`（**仅在**既有断言因新语义必须同步时，且须在 §5 逐条说明「原断言 → 新断言 → 理由」）
- **禁止改**：`backend/app/core/ai/**` **除 `errors.py`**（`providers/**`、`service.py`、`config.py`、`prompts.py`、`types.py` 一律禁改）、`backend/app/modules/**`、`frontend/**`、`docs/**`（含 `docs/changes/BUG-005.md` 状态位）、`.e2e/**`、任何契约文本。
- **并行说明**：与 `Task-016`（`BUG-006`，写区 `m001/services/task_parser.py`）**文件零重叠、无依赖，可并行执行**。若执行中发现必须改动对方写区文件 → **停下回报**，不得越区。

## 1. Objective

让「三方返回了什么」被**如实分类与留痕**：`403 余额/配额不足` 不再被误报为「三方鉴权失败」，且三方响应摘要（**脱敏 + 截断**）进入 DATA-009 `error.message`，使线上 AI 故障**可由记录直接定位**，无需另写复现脚本。

## 2. 背景（PM 读码确认 + 实测原文；**勿再自行推断**）

| # | 事实 | 证据（文件:行） |
| --- | --- | --- |
| 1 | 403 被无条件映射为 `AUTH_ERROR` | `backend/app/core/ai/errors.py:67-68`：`if status_code in (401, 403): return AIError(AIErrorCode.AUTH_ERROR, "三方鉴权失败", ...)` |
| 2 | `body` 仅参与 400/422 内容安全判定，其余分支**丢弃** | `errors.py:66`（`text = (body or "").lower()`）→ `:71-74` 使用 `text`；`:68` / `:70` / `:76` / `:78` 的 message 全为常量 |
| 3 | **实测**：余额不足返回 `403` + `pre_consume_token_quota_failed`，系统记录却为 `{"code":"auth_error","message":"三方鉴权失败"}` | `docs/changes/BUG-005.md §1`（三方响应原文 + DATA-009 原文） |
| 4 | 该误报**直接误导排障方向** | 同一 payload 直连 200 → 排查被引向「密钥/URL/env 覆盖」，实际原因 = 账户配额不足（PM 当日实测） |
| 5 | `message` 已有安全约束（**必须保持**） | `errors.py:52`：「message 面向内部日志/降级信号；**禁止携带密钥等敏感内容**」 |
| 6 | 现有枚举 9 项，**无「额度耗尽」语义位** | `errors.py:12-23`（`PROVIDER_UNAVAILABLE` / `TIMEOUT` / `RATE_LIMITED` / `CONTENT_REFUSED` / `AUTH_ERROR` / `INVALID_OUTPUT` / `CONFIG_ERROR` / `SERVER_ERROR` / `INTERNAL_ERROR`） |
| 7 | `RATE_LIMITED` 属**可重试**，语义不可复用为「额度耗尽」 | `errors.py:27-35` `RETRYABLE_CODES` 含 `RATE_LIMITED` |
| 8 | 真实场景存在 **502 + Cloudflare HTML 错误页**（body 非 JSON） | `docs/changes/BUG-005.md §7`（2026-09-14 实测） |

## 3. 任务要求

### 3.1 新增配额/余额错误码（**必做**）

- `AIErrorCode` 新增成员：`QUOTA_EXHAUSTED = "quota_exhausted"`（注释语义：账户余额 / 配额不足或额度耗尽）；
- **不得**加入 `RETRYABLE_CODES`（重试无意义）；
- 语义边界（写入代码注释，供后续消费方对齐）：
  - `RATE_LIMITED` = **限流**（可退避重试）；
  - `QUOTA_EXHAUSTED` = **额度/余额耗尽**（不可重试，需人工充值）；
  - `AUTH_ERROR` = **密钥无效 / 鉴权被拒**。

### 3.2 403 精细化分支（**必做**）

`from_http_status` 中 **401 语义不变**；`403` 改为「先判配额线索、再判鉴权」：

- 触发条件（可按实现微调，但须在 §5 逐条说明）：`status_code == 403` 且 `text` 命中任一关键词 —— `quota`、`insufficient_quota`、`balance`、`pre_consume`、`余额`、`额度`；
- 命中 → `AIError(AIErrorCode.QUOTA_EXHAUSTED, ...)`（`retryable=False`）；
- 未命中 → 维持 `AIErrorCode.AUTH_ERROR`（**向后兼容**：既有 403 断言不得放宽）。

### 3.3 三方响应摘要进入 `message`（**必做：脱敏 + 截断**）

对 `401 / 403 / 429 / 5xx` 分支（含新增配额分支）在 `message` 中附三方响应摘要：

1. **截断**：摘要 ≤ **200 字符**；
2. **脱敏**：剔除密钥特征串（至少处理 `sk-` 前缀串、`Authorization` 形字样）；
3. **优先提取**：若 body 可解析为 JSON → 优先取 `error.message` / `error.code` / `message`；不可解析则取纯文本片段；
4. **HTML 容错**：body 为 HTML（如 Cloudflare 错误页）→ 折叠为可读纯文本或标注 `<html>` 摘要，**不得原样整段塞入**；
5. `AIError.as_dict()` 输出结构**保持不变**（`{"code", "message"}`）；
6. 必须通过 §3.4 的**脱敏断言**（message 不含密钥串）—— 不得破坏 `errors.py:52` 约束。

### 3.4 测试（**必做**）

新增 `backend/tests/unit/test_ai_errors.py`，至少覆盖：

| # | 用例 | 断言要点 |
| --- | --- | --- |
| 1 | `from_http_status(403, '{"code":"pre_consume_token_quota_failed","message":"…余额不足…"}')` | `code == "quota_exhausted"` 且 `retryable is False` |
| 2 | `from_http_status(403, '{"error":{"message":"forbidden"}}')`（无配额线索） | `code == "auth_error"` |
| 3 | `from_http_status(401, ...)` | `code == "auth_error"` |
| 4 | `from_http_status(429, ...)` | `code == "rate_limited"` 且 `retryable is True` |
| 5 | `from_http_status(502, ...)` | `code == "server_error"` 且 `retryable is True` |
| 6 | **脱敏**：body 含 `sk-abcdef123456` | `message` **不含**该串 |
| 7 | **截断**：body 长度 5000+ | `message` 长度受控（≤200 摘要 + 固定文案） |
| 8 | **HTML 容错**：`status_code=502` + Cloudflare HTML | 不抛异常且 message 可读 |

- 若必须同步既有 `tests/unit/test_ai_service.py` 断言 → §5 逐条列出「原断言 → 新断言 → 理由」，**禁止静默放宽**；
- §5 须附**判别力证据**：将 403 分支临时回退为旧映射 → 用例 1 变红（`RED_EXIT≠0`）；恢复 → 全绿（`GREEN_EXIT=0`）。

## 4. DoD（交付判定）

- [ ] `QUOTA_EXHAUSTED` 已新增且**不在** `RETRYABLE_CODES`
- [ ] 403 命中配额线索 → `quota_exhausted`；未命中 → `auth_error`；401 语义不变
- [ ] `message` 摘要**已脱敏 + ≤200 字符**；HTML / 超长 body 不破坏可读性
- [ ] `backend/tests/unit/test_ai_errors.py` 新增并覆盖 §3.4 全部 8 项
- [ ] 既有 `test_ai_service.py` / `test_ai_providers.py` / `test_ai_records.py` 断言**零放宽**（如同步过，§5 逐条说明）
- [ ] 全量 `pytest`：**0 failed / 0 errors / 0 skipped**，用例数 **≥ 237**（新增用例应使总数增加）
- [ ] `read_lints` = 0；写区合规（`git status --porcelain` + **mtime 审计**）：`providers/**`、`service.py`、`config.py`、`modules/**`、`frontend/**`、`docs/**`、`.e2e/**` **零写入**
- [ ] §5 七段式报告完成，含**红→绿判别力原文**（命令 + 输出）
- [ ] **不伪造**：证据须来自可复现命令；若某项证据物理不可得（如外部中转不可用）→ **停下回报** 并显式标注替代手段（如 `httpx.MockTransport`）与证据形态，**不得冒充真实三方联调证据**

## 5. 执行方报告（七段式）

> **执行者说明**：本任务由 **PM 代执行**（当前 IDE 无具备写权限的执行 subagent，仅有只读 `code-explorer` 可用）。因此「执行方自述」与「PM 复核」出自同一操作者 —— **不构成独立第三方验证**，此限制如实标注；下述证据均为**可复现命令 + 原文输出**。

### ① 状态

**完成**。`AIErrorCode.QUOTA_EXHAUSTED` 已新增（**未入** `RETRYABLE_CODES`）；`403` 按配额线索精细化；4xx/5xx `message` 附**脱敏 + ≤200 字符**三方摘要。新增 `backend/tests/unit/test_ai_errors.py`（**9 例**）全绿；红→绿判别力成立；全量回归 **251 / 0 failed / 0 errors / 0 skipped**（基线 237 + 本任务 9 + `Task-016` 5）。既有 `test_ai_service.py` / `test_ai_schemas.py` 断言**零同步、零放宽**。

### ② 改动文件清单 + diff 摘要

| 文件 | 性质 | 改动摘要 |
| --- | --- | --- |
| `backend/app/core/ai/errors.py` | 改（约 +60 行） | ① 枚举新增 `QUOTA_EXHAUSTED = "quota_exhausted"`（注释：账户余额/配额不足，不可重试）；② 新增 `_QUOTA_HINTS`（`quota` / `insufficient_quota` / `balance` / `pre_consume` / `余额` / `额度`）、`_SUMMARY_LIMIT = 200`、`_SECRET_PATTERNS`、`_redact()`、`_extract_error_text()`、`_summarize_body()`；③ `from_http_status` 重构：**401 分支语义不变** → **403 先判配额线索** → 429/400·422 内容拒绝/5xx/4xx 统一追加 `" \| 三方摘要: …"`；④ 既有中文固定文案**逐字保留** |
| `backend/tests/unit/test_ai_errors.py` | **新增**（9 例） | 配额码与非可重试性 / 无线索 403 仍 `auth_error` / 401 / 429 / 502 / **脱敏** / **截断** / **HTML 折叠** / `as_dict` 结构不变 |

### ③ 红→绿 / 判别力证据原文

**红**（临时把 403 分支回退为旧映射 `if status_code in (401, 403)`）：

```
FAILED tests/unit/test_ai_errors.py::test_403_quota_hint_maps_to_dedicated_non_retryable_code
E   AssertionError: assert <AIErrorCode.AUTH_ERROR: 'auth_error'> == <AIErrorCode.QUOTA_EXHAUSTED: 'quota_exhausted'>
FAILED tests/unit/test_ai_errors.py::test_as_dict_keeps_contract_shape
E   AssertionError: assert 'auth_error' == 'quota_exhausted'
RED_EXIT=1
```

**绿**（还原修复）：`tests/unit/test_ai_errors.py` **9 passed** → `EXIT=0`（含于下方全量）。

### ④ 全量回归原文

```
$ pytest --no-header -q --tb=short --junitxml=../.pm_t015_t016.xml
........................................................................ [ 28%]
..............................X..X...................................... [ 57%]
........................................................................ [ 86%]
...................................                                     [100%]
tests=251 failures=0 errors=0 skipped=0
GREEN_EXIT=0
```

`X..X` = 既有 `BUG-003` / `BUG-004` 双哨兵自然 **XPASS**（未删除、未放宽）。

### ⑤ 写区合规自证（双证）

- **`git status --porcelain`**：`M backend/app/core/ai/errors.py`（写区内）、`?? backend/tests/unit/test_ai_errors.py`（新增）；**未出现** `service.py` / `config.py` / `providers/**` / `modules/**` / `frontend/**` / `docs/**` / `.e2e/**` 任何条目。
- **mtime 审计**：写区 = `errors.py` **09-14 15:48:34**；禁改区 = `service.py` 09-10 16:54:31、`config.py` 09-10 16:52:45、`providers/openai_compatible.py` 09-10 16:53:32、`m001/services/task_service.py` 09-10 20:11:26、`m002` 最新文件 09-10 20:26:54 → **全部早于写区起点（15:47）→ 零写入成立**。
- `read_lints` = 0。

### ⑥ 契约 / 兼容性影响核对

- `AIErrorCode` 新增成员属**取值域扩大**（`str, Enum`）；全仓消费点 = `providers/openai_compatible.py:77`（`raise from_http_status(...)`）+ `service.py` 的 DATA-009 `as_dict()` 落库 → **无枚举穷举分支**，向后兼容。
- `message` 为**追加式**变更（保留既有中文前缀，追加 `" | 三方摘要: …"`）→ 无文案破坏。
- 安全：摘要已脱敏（`sk-*`、`Authorization` 形字样 → `[REDACTED]`）且 ≤200 字符，符合 `errors.py` 既有约束（`message` 禁携带敏感内容）。
- **待 PM 登记文档**：`docs/DATA_MODEL.md`（DATA-009 `error.code` 取值表）、`docs/CONFIGURATION.md`（如需）。

### ⑦ 遗留 + 需 PM 裁决项

1. `docs/DATA_MODEL.md` 登记 `quota_exhausted` 取值 → **PM**（本任务禁改 `docs/**`）。
2. `BUG-005` 状态置位 → **PM**。
3. **真实三方端到端复验**（中转稳定时命中真实 403/502 并读 DATA-009 原文）→ 建议 PM 另行补一次；本任务未将其纳入 DoD，避免外部中转波动影响回归稳定性。

## 6. 不在本任务范围

- `docs/**` 文档登记（`DATA_MODEL.md` 错误码取值表、`CONFIGURATION.md`）→ **PM**；
- `BUG-005` 状态位置 `Fixed` / `Verified` → **PM**；
- 其他缺陷（`BUG-006` → `Task-016`）、技术债 `TD-001` / `TD-002`、V2 域 D → 不在本任务；
- **降级/重试策略本身的行为变更**（如「配额耗尽后自动熔断」「余额不足时提前告警」）→ 需另立 CR，**不在本任务**；
- 真实三方联调复跑（环境依赖）→ 不在本任务（`Task-015` 只保证分类与留痕正确）。

---

**写区自检（PM 铁律 ⑧）**：本任务交付物 = `backend/app/core/ai/errors.py`（1 处生产代码）+ `backend/tests/unit/test_ai_errors.py`（新增）+ 可选 `test_ai_service.py` 同步 + 本任务书 §5 追加 → **全部 ⊆ §写区**；`docs/**` 与 Forbidden 区**零写入**。
