# Task-024 —— M002 挂接建议端点 AI 失败原因可见（`CR-006` 子项 B）

## 1. 背景与目标

### 背景
- **`BUG-005`**：三方 403「余额/配额不足」被误报「鉴权失败」→ DATA-009 留痕失真、排障方向被误导（`Task-015` 已修复，但需暴露给用户）
- **`BUG-006`**：AI 不可用时静默降级 → UI 无信号
- **`BUG-008`**：DATA-009 在 SQLite 锁竞争下静默丢失（只登记不修）

### 目标
在 `API-M002-007` 响应中增加 `last_attempt` 字段，消费 DATA-009 暴露 AI 失败原因（脱敏 + 截断），供前端做「重试」或「手工兜底」提示。

## 2. 契约修订（M002 v0.4.4）

| 项 | 内容 |
|---|---|
| 接口 | `GET /api/v1/photos/{photo_id}/link-suggestions` |
| 变更 | Response +`last_attempt` 可选字段（**成功 / 无记录 / 读取异常时为 `null`**） |
| 类型 | `{ "code": AIErrorCode, "message": str }`（脱敏；三方摘要截断 ≤200 字，继承 `BUG-005`） |
| 来源 | **DATA-009**（`ai_call_records`）**只读**：按 `json_extract(input_ref,'$.photo_id') = photo_id` + `capability='photo_link_suggest'` 取**最近一条**；仅该条为 `status='error'` 时暴露 |
| 版本 | M002 **v0.4.3 → v0.4.4**（Frozen 面内非破坏性） |

> **版本校正（2026-09-17，PM）**：本任务书初版误写「v0.4.2 → v0.4.3」，与**子项 A 已占用的 v0.4.3** 冲突 → 子项 B 应为 **v0.4.3 → v0.4.4**（子项 C 顺延 v0.4.5）。

## 3. 实施范围

### 写区（M002 内部，禁改其它模块）
- `app/modules/m002/api/link_routes.py`：`get_link_suggestions` 函数 +`_last_attempt()` 采集器 + `LinkSuggestionOut` Schema
- `app/modules/m002/schemas.py`：`LinkSuggestionOut` +`last_attempt`（+ `Any` 导入）
- 新增 `tests/integration/test_m002_link_failed_reason.py`（4 例）
- **最小扩权**：`tests/e2e/test_acceptance_scenarios.py`（**仅 1 行**键集哨兵，见 §5 ④）

### 禁区
- `m001/**`、`core/ai/**`（契约层）、`frontend/**`、`docs/**`（除本任务书与 §5 登记的契约同步）

## 4. 验收清单（8 条）

| # | 项 | 目标证据 |
|---|---|---|
| 1 | 响应 +`last_attempt` 字段 | `LinkSuggestionOut` 含 `last_attempt: dict \| None`；成功时 `null` |
| 2 | 失败分支红→绿 | 检索键回退为错误键 → 用例 FAIL（证明判别力）→ 还原 PASS |
| 3 | DATA-009 消费 | `last_attempt.code` = `ai_call_records.error.code`；`message` 脱敏 + 三方摘要 ≤200 字 |
| 4 | 向后兼容 | 缺省 `last_attempt=null`；既有消费者无视新字段仍 OK |
| 5 | 重试参数不变 | `retry=true` 仍触发建议（不依赖 `last_attempt`） |
| 6 | 全量回归 | `pytest -q --no-header` → **278 / 0 / 0 / 0**（基线 274 + 新增 4） |
| 7 | 前端零改动 | 前端可忽略 `last_attempt` 或据此提示（本期不消费） |
| 8 | 迁移可复现 | 无 schema 变更；`-Seed` 后真机验证响应字段集 |

## 5. 交付与证据（2026-09-17，PM 代执行）

> **执行方式限制**：本机 IDE 无具备写权限的执行 subagent（仅只读 `code-explorer`）→ 由 **PM 代执行**，**不构成独立第三方复核**（如实标注）。

### ① 实施前复核：原实施提交（`1afb33c`）的 5 处硬缺口（已全部修复）

| # | 缺口 | 结论 |
|---|---|---|
| 1 | `link_routes.py:78` 以 **`photo.upload_request_id`** 过滤 —— 该列在 `photos` 表/`Photo` 模型**均不存在**（全后端仅此 1 处出现）→ `AttributeError` 被宽 `except` 吞 → **`last_attempt` 恒 `null`（功能不可用）** | **已修复**：改用 `json_extract(input_ref,'$.photo_id')`（采纳 CR-006 实施前核验 #5 的结论）+ `capability` 过滤 |
| 2 | `recent.error.code.value` 类型误用 —— `error` 为 `Text`（`_dump` 写入的 **JSON 字符串**） | **已修复**：`json.loads(recent.error)` 后取 `code`/`message` |
| 3 | `Any` 未导入（注解在用）；`ai_svc = get_ai_service()` 赋值后未使用（死代码） | **已修复**：补 `from typing import Any`；删除死代码（Pydantic 对未解析名回退 `Any` 曾掩盖此问题） |
| 4 | 承诺的用例 `tests/integration/test_m002_link_failed_reason.py`（4 例）**未创建** | **已补齐**（本任务数据见 ②） |
| 5 | 契约文档**仅同步 1 处**（`MODULE_API.md`）；`MODULE_CONTRACT` / `MODULE_CHANGELOG` / `MODULE_REGISTRY` / `API_REGISTRY` 未同步；任务书状态仍「待实施」；未签发验收任务 | **已补齐**（见 ⑤） |

### ② 新增用例（4 例，`tests/integration/test_m002_link_failed_reason.py`）

| 用例 | 覆盖 | 结论 |
|---|---|---|
| `test_last_attempt_is_null_when_latest_attempt_succeeds` | 成功 → `null`（**先数据面确认确有 `status=ok` 留痕**，排除「没读到」） | PASS |
| `test_last_attempt_exposes_failure_from_data009` | **失败分支**：`real` + 禁兜底（无凭据）→ `provider_unavailable` → 响应 = DATA-009 实读（`code`/`message` 逐字一致） | PASS |
| `test_last_attempt_message_is_redacted_and_bounded` | 脱敏 + 截断（`sk-` → `[REDACTED]`；三方摘要 ≤200 字）；`quota_exhausted` 下游可见（`BUG-005` 成果） | PASS |
| `test_last_attempt_is_null_without_records_and_keys_are_backward_compatible` | 无记录（表未建）→ `null` 且**不报错**；键集 = v0.4.2 基线 3 键 + 新增 1（多=[] 少=[]） | PASS |

**桩 / 替身说明（PM 铁律 ①）**：本文件**不注入任何 AI 替身** —— 用例 1/2 走真实 `DefaultAiClient` → 真实 `app/core/ai` → 真实 DATA-009 写入；用例 3 以 DATA-009 的**生产写入 API**（`record_call` + `from_http_status`）落一条历史留痕（与生产同源，非替身），并**关闭「上传即建议」**以消除同秒多记录的排序歧义。

### ③ 红→绿判别力（**亲手取证**）

```
# 红：把检索键回退为错误键（复现原缺陷的「键错」形态）
        AICallRecord.request_id == str(photo_id)
FF..  → FAILED test_last_attempt_exposes_failure_from_data009
        E AssertionError: {'...', 'last_attempt': None, 'suggestions': []}
        FAILED test_last_attempt_message_is_redacted_and_bounded
RED_EXIT=1

# 绿：还原为 json_extract(input_ref,'$.photo_id')
....  [100%]      GREEN_EXIT=0
```

### ④ 最小扩权（1 处，**仅 1 行**）

- `tests/e2e/test_acceptance_scenarios.py::test_scenario5_*`：响应键集哨兵 `{photo_id, status, suggestions}` → `{photo_id, status, suggestions, last_attempt}`
- **理由**：v0.4.4 为**契约内的新增可选字段**，哨兵必须同步；断言仍**逐项从严**（多=[] 少=[]），哨兵作用（捕获**非预期**形状漂移）不变
- 其余断言、用例语义、测试基线**零变更**

### ⑤ 契约与治理同步（8 处）

`MODULE_API.md`（v0.4.4 头部 + DTO 约定 + API-M002-007 正文，含**检索键**与**截断约束**的准确表述）、`MODULE_CONTRACT.md`（版本 + 签署区）、`MODULE_CHANGELOG.md`（新增 v0.4.4 条目，含已知边界）、`MODULE_REGISTRY.md`（2 处版本链）、`API_REGISTRY.md`（`API-M002-007` 版本列 + 2026-09-17 纪要）、`changes/CR-006.md`（落地记录）、`PROJECT_STATUS.md` / `CHANGELOG.md`（顶层 `v0.26.0`）

### ⑥ 全量回归（PM 实测）

```
tests=278 failures=0 errors=0 skipped=0   EXIT=0      （基线 274 + 新增 4）
read_lints = 0
```

### ⑦ 边界与遗留

- **`input_ref` 无独立列/索引** → 以 `json_extract` 检索（V1 数据量小，未观测到瓶颈）。若后续成为性能问题，**表达式索引需 `app/core/ai` 侧变更** → 届时按 CR 处理
- **`message` 长度**：契约原表述「≤200 字」实指**三方摘要**（`BUG-005` 约束）；`message` = 统一文案前缀 + 摘要 → **已在 `MODULE_API.md` 明确**，避免误读
- **`BUG-008`**（DATA-009 锁竞争静默丢失）**未修复**，与本子项同批**仅评估**：若留痕丢失 → `last_attempt` 为 `null`（**降级为「无信息」而非错误信息**，不误导）

## 6. 任务书签发信息
- **提案人**：Project Master
- **日期**：2026-09-17（初版）/ **2026-09-17 收口**
- **状态**：**已完成**（契约 v0.4.4 + 实施 + 用例 + 回归齐备）
- **执行方**：`AGENT-M002`（**PM 代执行**，不构成独立第三方复核）
- **验收方**：`Task-025`（8 条清单）
