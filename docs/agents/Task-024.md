# Task-024 —— M002 挂接建议端点 AI 失败原因可见（`CR-006` 子项 B）

## 1. 背景与目标

### 背景
- **`BUG-005`**：三方 403「余额/配额不足」被误报「鉴权失败」→ DATA-009 留痕失真、排障方向被误导（`Task-015` 已修复，但需暴露给用户）
- **`BUG-006`**：AI 不可用时静默降级 → UI 无信号
- **`BUG-008`**：DATA-009 在 SQLite 锁竞争下静默丢失（只登记不修）

### 目标
在 `API-M002-007` 响应中增加 `last_attempt` 字段，消费 DATA-009 暴露 AI 失败原因（脱敏 + 截断），供前端做「重试」或「手工兜底」提示。

## 2. 契约修订（M002 v0.4.3）

| 项 | 内容 |
|---|---|
| 接口 | `GET /api/v1/photos/{photo_id}/link-suggestions` |
| 变更 | Response +`last_attempt` 可选字段（**成功时为 `null`**） |
| 类型 | `{ "code": AIErrorCode, "message": str }`（脱敏 + ≤200 字） |
| 来源 | `ai_call_records.request_id = photo.upload_request_id`；按 `capability=photo_link_suggest` 过滤最近记录 |
| 版本 | M002 **v0.4.2 → v0.4.3**（Frozen 面内非破坏性） |

## 3. 实施范围

### 写区（M002 内部，禁改其它模块）
- `app/modules/m002/api/link_routes.py`：`get_link_suggestions` 函数 +`LinkSuggestionOut` Schema
- `app/core/ai/records.py`（可选）：如需跨会话读取 DATA-009，确认库连接可用（测试 fixture 已保障）

### 禁区
- `m001/**`、`core/ai/**`（契约层）、`frontend/**`、`docs/**`

## 4. 验收清单（8 条）

| # | 项 | 目标证据 |
|---|---|---|
| 1 | 响应 +`last_attempt` 字段 | `LinkSuggestionOut` 含 `last_attempt: dict \| None`；成功时 `null` |
| 2 | 失败分支红→绿 | 临时移除 `_record_error` → 用例 FAIL（证明判别力）→ 还原 PASS |
| 3 | DATA-009 消费 | `last_attempt.code` = `ai_call_records.error.code`；`message` 脱敏截断 ≤200 |
| 4 | 向后兼容 | 缺省 `last_attempt=null`；既有消费者无视新字段仍 OK |
| 5 | 重试参数不变 | `retry=true` 仍触发建议（不依赖 `last_attempt`） |
| 6 | 全量回归 | `pytest -q --no-header` → **274 / 0 / 0 / 0**（基线 + 新增） |
| 7 | 前端零改动 | 前端可忽略 `last_attempt` 或据此提示（本期不消费） |
| 8 | 迁移可复现 | `-Seed` 后真机验证响应字段集 |

## 5. 交付物
- 契约修订：`docs/modules/M002/MODULE_API.md`
- Schema：`app/modules/m002/schemas.py`（+`last_attempt`）
- 路由：`app/modules/m002/api/link_routes.py`（消费 DATA-009）
- 新增用例：`tests/integration/test_m002_link_failed_reason.py`（4 例：成功/失败分支红→绿/脱敏截断/向后兼容）

## 6. 任务书签发信息
- **提案人**：Project Master
- **日期**：2026-09-17
- **状态**：待实施
- **执行方**：`AGENT-M002`（或用户手动代执行）
- **验收方**：`Task-025`（8 条清单）
