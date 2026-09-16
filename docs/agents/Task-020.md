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

> **执行者说明**：本任务由 **PM 代执行**（当前 IDE 无具备写权限的执行 subagent）→ 不构成独立第三方复核，限制如实标注。

### ① 状态

**完成**。「重新解析」按钮（`confirmed` 隐藏）+ `reparseTask`（可选 `timeoutMs`，**未改** `http.ts`）+ **如实反馈**全部落地。`vue-tsc -p tsconfig.app.json` **0 error**、`npm run build` **EXIT=0**、**浏览器级 7/7 PASS（真实三方 AI）**、`backend/**` 零写入。

### ② 改动文件清单 + diff 摘要

| 文件 | 性质 | 改动摘要 |
| --- | --- | --- |
| `frontend/src/api/index.ts` | 改（+20 行） | 新增 **`reparseTask(task_id, options?: { timeoutMs? })`** → `POST /tasks/{task_id}/reparse`；仅传参时覆盖单请求 `timeout`（**全局 `http.ts` 未动**） |
| `frontend/src/views/TaskDetailView.vue` | 改（+45 行） | 动作区新增「**重新解析**」按钮（`v-if="canReparse"` = `spec_status ∈ {placeholder, parsed}`，`confirmed` 隐藏）+ 解析中提示；`reparse()` 逻辑：`task.value = updated` 后按 **`spec_status === "parsed" && contents.length > 0`** 判定成功文案，否则提示「AI 未返回解析结果…」；异常走 `toastError` + `load()` 刷新（409 场景） |

### ③ 验证证据原文（**分域**）

**(a) 前端静态级**：
```
$ npx vue-tsc --noEmit -p tsconfig.app.json
TSC_EXIT=0
```

**(b) 构建级**：
```
$ npm run build
dist/assets/TaskDetailView-7e3MOpRs.js    8.17 kB │ gzip: 3.76 kB
✓ built in 3.30s
BUILD_EXIT=0
```

**(c) 浏览器级（真实三方 AI，8010；Edge + `playwright-core`）**：

```
CHECKS total=7 pass=7 fail=0
PASS 布置单照片上传成功（kind=task_spec） :: status=unassigned
setup: ingest spec_status=parsed contents=6
PASS 任务详情页出现「重新解析」按钮
PASS 点击后反馈：已解析出内容项（真实 Vision） :: 已解析出 6 项内容，请到「草稿确认」核对
PASS 成功文案与真实内容项一致（不谎报） :: contents=6
PASS 页面「内容项」标题数与接口一致 :: 内容项（6）
PASS 无 favicon 404 之外的页面 JS 错误
PASS 无 4xx/5xx 资源请求（favicon 除外）
EXIT=0
```
→ **两项关键结论**：① **布置单图片源解析真的通了**（`POST /tasks` 带 `kind=image` 源 → 建任务**即 `parsed` 并产出 6 项内容**，证明 `Task-018`+`Task-019` 的受控取图 → Vision 通路真实生效）；② **「重新解析」正向生效**（第二次调用产出 6 项，与 `placeholder`→`parsed`/`parsed` 整体替换语义一致）。

### ④ 回归与用例数

- `backend/**` **零写入** → 后端全量用例数不减（`Task-019` 后基线 **265 / 0 / 0 / 0**）。
- 前端**无自动化测试框架** → 本任务证据形态 = 类型检查 + 构建 + 浏览器级脚本（**临时脚本已删除**，未纳入回归）。

### ⑤ 写区双证

- **`git status --porcelain`**：`M frontend/src/api/index.ts`、`M frontend/src/views/TaskDetailView.vue`（均写区内）；**未出现** `backend/**`、`frontend/src/api/http.ts`、`frontend/src/views/PhotoListView.vue`、`components/PhotoCard.vue`、`router/**`。
- **mtime 审计**：写区为前端 2 文件（本日）；`backend/**` 自 `Task-019` 提交后未再写。
- `read_lints` = 0。

### ⑥ 兼容性核对

- `http.ts` 全局 `timeout: 15000` **未改**；`reparseTask` 为**新增**函数（无既有调用点）→ 既有链路零影响。
- 重解析请求**单独 60s**（`REPARSE_TIMEOUT_MS`），与 `BUG-007` 修复模式一致。
- `confirmed` 任务不显示按钮 → 前端不触发 409 路径（后端仍保留 409 兜底）。

### ⑦ 遗留 + 需 PM 裁决项

1. **失败分支未在真实服务上构造**（真实 AI 可用 → ingest 即成功）：浏览器级只取到**成功分支**；失败分支（AI 不可用 → 保持 `placeholder` + 如实提示）已由 `Task-019` 的 **API 级用例 5**（`real`+禁兜底 → 不清空）覆盖 → 建议 `Task-021` 补一次浏览器级失败分支。
2. `confirmed` 任务无「取消确认」入口（V1 设计，契约 §2.4 只定义拒绝）→ 前端隐藏按钮，符合现状。
3. **调试记录（如实）**：首轮 1 例断言失败 = 我的定位器 `.card`（`hasText: "内容项"`）命中了**任务概要卡**（其含「内容项 6 项」字样）→ 改用 `h3.section-h` 定位后通过；**非产品缺陷**，脚本已修正。
4. 临时资产（脚本 / 截图 / 合成图）已清理；`Task-021` 验收待执行。

## 5. 不在本任务范围

- M002/M001 后端（`Task-018`/`Task-019`）；验收（`Task-021`）；
- 「AI 未识别的照片」卡片改造（属 `REQ-011` 第一阶段，已完成）；
- `CR-006`（A/B/C）。
