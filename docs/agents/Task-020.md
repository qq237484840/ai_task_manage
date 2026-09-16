# Task-020 任务书 —— `CR-005` 前端：任务详情页「重新解析」入口

- **Task ID**：Task-020 ｜ **Agent**：`AGENT-M001`（任务域前端）｜ **Module**：M001（前端）
- **签发**：Project Master，2026-09-16 ｜ **状态**：**已签发（待执行）** ｜ **Kind**：**需求实施（前端，小）**
- **上游**：`CR-005`（**Approved**）→ `API-M001-022`（`Task-019` 实施）
- **前置**：`Task-019` 的 `API-M001-022` 已就绪（否则按钮调用 404）
- **契约影响**：无（仅消费 `API-M001-022` / `API-M001-009`）
- **写区（授权）**：`frontend/src/views/TaskDetailView.vue`、`frontend/src/api/index.ts`（新增 `reparseTask`）、`frontend/src/api/types.ts`（如需）、`docs/agents/Task-020.md`（§5）
- **禁止改**：`backend/**`、`frontend/src/views/PhotoListView.vue`、`frontend/src/components/PhotoCard.vue`、`frontend/src/api/http.ts`、`frontend/src/router/**`、其余 `docs/**`

## 1. Objective

家长在任务详情页可**一键重新解析**布置单（尤其纯图片布置单），并在失败时得到**如实**反馈（不谎报成功）。

## 2. 任务要求

1. **按钮**：任务详情页动作区新增「**重新解析**」——
   - `spec_status ∈ {placeholder, parsed}` → 可见可用；
   - `spec_status == confirmed` → **隐藏**（或禁用 + 提示「已确认，需先取消确认」—— 二选一，§5 说明）；
   - 请求中 loading + 禁用（防连点）。
2. **API 封装**：`api/index.ts` 新增 `reparseTask(task_id: string, options?: { timeoutMs?: number }): Promise<TaskDetail>` → `POST /tasks/{task_id}/reparse`。
3. **超时**：单请求放宽至 **60s**（真实 Vision 约 15s+；沿用 `BUG-007` 修复模式：**不改** `http.ts` 全局超时）。
4. **反馈（如实）**：
   - 返回后按 `spec_status` / `contents` 判定：变为 `parsed` 且有内容项 → `showToast("已解析出 N 项内容，请到「草稿确认」核对")`；
   - 仍为 `placeholder` 且 `contents==[]` → `showToast("AI 未返回解析结果（可能暂时不可用或图片无法识别），可稍后重试或手工补录")`；
   - 任何情况下**不得**提示「解析成功」而实际无内容项。
5. **刷新**：调用后 `await load()` 重载任务态（`contents` / `spec_status` 同步）；若卡片「AI 未识别的照片」可见，无需联动刷新。

## 3. DoD

- [ ] 「重新解析」按钮按 §2.1 显示/禁用规则落地
- [ ] `reparseTask` 封装（含 `timeoutMs` 可选参数；全局 `http.ts` **未改**）
- [ ] 反馈文案按 §2.4 分流（**无内容项时不得谎报成功**）
- [ ] 成功后任务详情刷新（`contents` / `spec_status` 正确）
- [ ] `vue-tsc -p tsconfig.app.json` = **0 error**；`npm run build` = **EXIT=0**
- [ ] **浏览器级**证据（截图/Network，分域标注）：`placeholder` 任务点「重新解析」→（真实 Vision 可用时）`parsed` + 内容项出现在「内容项」卡；AI 不可用时提示如实
- [ ] `backend/**` 零写入；全量 `pytest` 用例数不减（≥ 251 + `Task-019` 增量）
- [ ] `read_lints` = 0；写区双证
- [ ] §5 七段式报告；**不伪造**（真实 Vision 不可用时标注替代口径）

## 4. 执行方报告（七段式）

> ① 状态 ｜ ② 改动清单 ｜ ③ 证据（类型检查 / 构建 / 浏览器级，分域）｜ ④ 回归与用例数 ｜ ⑤ 写区双证 ｜ ⑥ 兼容性（其它调用点 timeout 不变）｜ ⑦ 遗留 + 需 PM 裁决项

## 5. 不在本任务范围

- M002/M001 后端（`Task-018`/`Task-019`）；验收（`Task-021`）；
- 「AI 未识别的照片」卡片改造（属 `REQ-011` 第一阶段，已完成）；
- `CR-006`（A/B/C）。
