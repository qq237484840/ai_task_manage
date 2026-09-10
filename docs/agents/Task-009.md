# Task-009 任务书 —— 前端「作业」域迁移（照片域 → 作业域，M002 v0.4.0 对齐）

- **Task ID**：Task-009 ｜ **Agent**：`AGENT-M002` ｜ **Module**：M002（前端域，随模块契约）
- **签发**：Project Master，2026-09-10 ｜ **状态**：**已交付 → PM 复核 APPROVED（2026-09-10）** ｜ **Kind**：**实施（前端编码）**
- **启动前置（硬约束）**：M002 契约 **v0.4.0 Frozen（✅ 已实施，Task-008 关闭）** + M001 契约 **v0.2.0 Frozen（✅ 已实施，Task-007 关闭）** + `app/core/ai/`（✅ Task-006 交付，Mock 可用）。**后端一律只读**：本任务**不得修改 `backend/**`**。
- **归属理由（PM 裁决，2026-09-10）**：写区 = 前端作业域 **+ M002 后端**，由 `AGENT-M002` 一人兼有前后端上下文，**规避 `frontend/src/api/index.ts` 的跨 Agent 写冲突**（`AGENT-M001` 的 M001 前端段与 M002 段同文件）。
- **前置依据**：`docs/modules/M002/MODULE_API.md` / `MODULE_CONTRACT.md` / `MODULE_DATA.md` / `MODULE_DESIGN.md`（**v0.4.0 Frozen，唯一契约来源**）、`docs/modules/M001/MODULE_API.md`（`API-M001-019/020` 聚合层查询，消费方）、`docs/changes/CHANGE-003.md` §1 第 9 条 + §2.2 B1~B6、`docs/adr/ADR-013.md`、`docs/agents/Task-008.md`（后端已落地面）
- **任务书登记**：`docs/AGENT_REGISTRY.md`（`AGENT-M002` 行）｜ **验收**：`CHANGE-003` §3 ③ 前端项 + 本任务 §6 DoD；**浏览器级端到端验收由 PM 在 ④ 统一执行**（本任务不含）

## 1. Objective（目标）

把前端**照片域**迁移为**作业域**并与后端 M002 **v0.4.0** / M001 **v0.2.0** 实况对齐：菜单「照片」→「**作业**」；**逐张挂接复核**目标由已废弃的段级（`task_id + subject + group_no`）改为 **`group_subject_id`（聚合学科子任务，N:N）**；列表按**周次 / 窗口（含周末聚合）分组**展示；补齐**挂接建议 / 窗口级门控 / 完成分析（草稿→确认→重跑）**调用面；彻底清除指向已移除端点的死代码。

## 2. 背景：现状缺陷实证（必须由本任务消除）

| # | 缺陷 | 证据 |
| --- | --- | --- |
| D1 | **运行期 404**：采纳/驳回/手工归属三个动作全断 | `frontend/src/api/index.ts` `associatePhoto → POST /photos/{photo_id}/associate`；该端点随 v0.4.0 **已移除**（全仓 `associate` 仅前端命中），`PhotoListView` 的 `acceptSuggestion` / `rejectPhoto` / `doAssign` 全部走此函数 |
| D2 | **API 面缺失**：M002 v0.4.0 五个新端点在前端无任何调用面 | `POST /photos/{id}/links`、`GET /photos/{id}/link-suggestions`、`GET /photo-gates`、`POST /completion-analyses`(+`/confirmation`、`/rerun`) 在 `api/index.ts` 均不存在 |
| D3 | **读已废弃模型**：归属弹层「选任务 → 选学科段」读 `task_items`（V1 已废弃停写）→ 无段可列、确认按钮恒禁用（手工挂接兜底实际不可用） | `PhotoListView.vue` `onTaskChange()` 读 `detail.items`（代码内已留待迁移注释），弹层文案仍为「归属到学科作业段」 |
| D4 | **数据面未对齐**：`Photo` 类型仍为段级 `assignment` / `suggestion`，且缺 `kind` / `links` / 窗口级 `task_id` | `frontend/src/api/types.ts`；后端实况 = `links: LinkDTO[]`（契约 `MODULE_API.md` §API-M002-003） |
| D5 | **入口 `kind` 未显式传递**：`createUploadBatch()` 依赖默认值 | `PhotoUploadView.vue` 调 `createUploadBatch(studentId)`；契约要求「作业」入口权威传 `kind=homework` |

## 3. Requirements（权威源，只读，禁止复制改写）

- `docs/modules/M002/**`（v0.4.0 Frozen）：`MODULE_API.md` §API-M002-001/003/005/007~011 为**唯一契约来源**
- `docs/modules/M001/MODULE_API.md`：`API-M001-019`（聚合列表）/`020`（聚合详情，`subjects[]` 即复核目标来源）
- `docs/adr/ADR-013.md`（双层模型：事实层按天 / 聚合层跨天；判定粒度 = 聚合学科子任务级）
- 后端已落地实况（**只读参考**）：`backend/app/modules/m002/api/**`、`backend/app/modules/m002/clients/*`

## 4. Scope（范围）

### 4.1 本任务交付

| # | 交付 | 说明 |
| --- | --- | --- |
| 1 | **改名「作业」** | 底部导航「照片」→「**作业**」；列表页/上传页标题一致化；**路由 `path` 保留 `/photos`**（避免深链与既有入口破坏），仅改 `name`/文案/图标语义 |
| 2 | **API 面补齐（M002 段）** | `api/index.ts` + `api/types.ts` 增补：`POST /photos/{id}/links`（accept\|reject\|relink，目标 `group_subject_id`/`link_id`）、`GET /photos/{id}/link-suggestions?retry=`、`GET /photo-gates`、`POST /completion-analyses`、`POST /completion-analyses/{id}/confirmation`、`POST /completion-analyses/{id}/rerun`；`GET /photos` 参数补 `kind` / `group_subject_id`；`PhotoListParams`/`Photo` 同步 |
| 3 | **死代码清除** | 删除 `associatePhoto` 及段级 `AssociateParams`/`AssociateResult`/`AssignmentInfo`/`SuggestionInfo`（若仅作业域引用）——**消除 404 根因** |
| 4 | **逐张挂接复核（B5）** | 复核目标改为**聚合学科子任务**（`GET /task-groups/{group_id}` 的 `subjects[]` → `group_subject_id`）；三路径 `accept` / `reject` / **改挂（relink）**；建议态取自 `links`（`source=ai` 且未 `confirmed_at`）；**手工挂接兜底必须保留可用（B6）**；「重试建议」→ `link-suggestions?retry=true` |
| 5 | **周次 / 窗口分组展示** | 列表按**周次 + 窗口类型**分组（显示名取 `task-groups.display_name`：「第 N 周」/「**周末作业**」/假期周），不再按段聚合；`week_index`/`window_type` 文案走 `utils/format.ts` |
| 6 | **窗口级门控（B4）** | `GET /photo-gates` → 展示「**待复核 N 张**」；未满足时分析生成入口**禁用并给出原因**；满足后可生成 |
| 7 | **完成分析（B4/B5）** | 草稿展示（结论 = 完成/部分完成/未完成/**无法判断** + 依据照片 + 置信度）→ 家长**确认（可校正结论）**→ **重跑（仅 draft）**；`409 gate_not_satisfied` / `photo_consumed` / 已确认 等错误原样提示 |
| 8 | **入口 `kind`（B1/B2）** | 「作业」上传**显式传 `kind=homework`**；**上传不填任何内容**（保持现状语义，仅对齐契约字段）；上传完成文案指向复核流程 |
| 9 | **文案与类型** | `api/types.ts` M002 段类型重写（`PhotoLink`/`GateStatus`/`AnalysisItem`/`Conclusion`）；`utils/format.ts` 补结论/门控/窗口文案映射 |
| 10 | **验证** | `npx vue-tsc --noEmit -p tsconfig.app.json` **0 error**；`npm run build` 成功；全前端 `associate` 命中 = **0**；**后端零改动**（`backend/**` git diff 为空） |

### 4.2 Allowed-Files（可写）

- `frontend/src/views/PhotoListView.vue`、`frontend/src/views/PhotoUploadView.vue`
- `frontend/src/api/index.ts`、`frontend/src/api/types.ts`（**仅 M002 段落增改**）
- `frontend/src/components/BottomNav.vue`、`frontend/src/router/index.ts`、`frontend/src/utils/format.ts`
- `frontend/src/components/**`（**仅新增作业域组件**，如复核弹层/分析卡片）
- `docs/modules/M002/MODULE_CHANGELOG.md`（**追加**前端交付小节，不改历史行）

### 4.3 Forbidden-Files / 边界

- **`backend/**` 一律只读**：发现后端与契约不符 → 以 **Request** 报 PM，**不得自行修改实现**（后端已由 Task-008 关闭并 PM 复核）
- **禁止改动 M001 前端任务域**：`TaskListView.vue` / `TaskDetailView.vue` / `TaskEditorView.vue`，及 `api/index.ts`、`api/types.ts`、`utils/format.ts` 中的 **M001 段落**（只读；确需改动 → Request）
- **禁止前端公共基座改动**：`api/http.ts`、`main.ts`、`App.vue`、`stores/**`、`styles/**`（如确需，先 Request）
- **禁止越界修改治理层文档**（AGENT_REGISTRY / API_REGISTRY / DATA_MODEL / CONFIGURATION / CHANGE-003 / ROADMAP / PROJECT_STATUS / CHANGELOG / INDEX / ADR）
- 禁止实现 V2 功能（报告 / 六维评分 / 评语 / 假期计划与评估）；**禁止内容项级判定**（V1 判定粒度 = 聚合子任务(学科)级）
- 禁止自行分配 API / DATA / Task ID

## 5. Dependencies（前置就绪条件）

- **硬前置（✅ 均已满足）**：M002 **v0.4.0** 后端已实施（`API-M002-001/003/005` 修订 + `007~011` 新增，PM 实测路由存在，状态 Active）；M001 **v0.2.0** 后端已实施（`API-M001-019/020` 可用）
- **解阻模式**：AI 建议/分析走 **Mock Provider**（`AT_AI_PROVIDER_MODE=auto` 无密钥即 Mock），前端**不得**因无建议而阻断手工路径
- **本地联调**：`backend/.venv` → `uvicorn app.main:app` + 前端 `vite`（proxy `/api/v1` → `127.0.0.1:8000`）

## 6. Acceptance Criteria（DoD，`AGENT_GUIDE.md` §6）

- [x] 导航与页面文案 = 「**作业**」；`/photos` 路由保留且深链可达（改名不破坏入口）
- [x] 全前端 `associate`（旧端点）命中 = **0**；`associatePhoto` 及段级类型已删除
- [x] M002 v0.4.0 六个新调用面**路径 / 方法 / 字段与契约逐一一致**（含 `action=accept|reject|relink` 与 `group_subject_id`/`link_id`）——**唯 API-M002-007 与 Frozen 契约字面不一致 → 见 §7 Request-1（`CR-004`）**
- [x] 逐张复核三路径可用，复核目标 = **`group_subject_id`**（**不再读 `task_items`**，`detail.items` 命中 = 0）
- [x] 列表按**周次 / 窗口**分组展示，周末聚显示名 = 「**周末作业**」（取自 `task-groups.display_name`）
- [x] 门控可见（「待复核 N 张」）；未满足时分析生成**被禁用**；满足后可生成草稿（前端含 `localGate` 本地重算兜底 —— 后端强制缺陷见 §7 Request-2 / `BUG-002` / `Task-010`）
- [x] 完成分析：草稿 → **确认（可校正结论）** → **重跑（仅 draft）** 全流程 UI 可用；`无法判断` 出口可见；后端 409/422 原样提示
- [x] **无 AI 建议 / AI 降级时手工挂接可用（B6 兜底）**——不得出现「无段可列 → 恒禁用」
- [x] 入口 `kind=homework` 显式传递，「作业」上传**不填内容**
- [x] `vue-tsc -p tsconfig.app.json` **0 error** + `npm run build` 成功；**`backend/**` git diff 为空**
- [x] PM 复核 APPROVED（2026-09-10）→ Task-009 关闭 → `CHANGE-003` ③ 前端项关闭 → ④ 验收（含第 7 条浏览器级）可执行

> 注：本任务**不含**浏览器级端到端验收（PM ④ 统一执行）、真实三方密钥联调（Mock 为最低验收线，`ADR-011`）、M001 任务域返工。

## 7. 交付与 PM 复核结论（2026-09-10）

### 7.1 交付物（8 文件 = 7 改 + 1 新增，全部在 `frontend/src/**`）

`api/types.ts`（M002 段按 v0.4.0 重写 + 段级类型删除）、`api/index.ts`（六调用面补齐 + `associatePhoto` 删除 + `kind` 透传）、`utils/format.ts`（新增文案映射）、`components/BottomNav.vue`（改名「作业」）、`components/PhotoCard.vue`（**新增**）、`router/index.ts`（`name` 改 `homework`，**`path` 保留**）、`views/PhotoListView.vue`（**重做**：窗口分组 + 三路径复核 + 门控 + 完成分析）、`views/PhotoUploadView.vue`（标题 + 显式 `kind=homework`）。

### 7.2 PM 独立复验（未采信自述，2026-09-10）

| 复验项 | 命令 / 方式 | 结果 |
| --- | --- | --- |
| 类型检查 | `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit -p tsconfig.app.json` | **TSC_EXIT=0（0 error）** |
| 生产构建 | `npm run build` | **BUILD_EXIT=0**（含 `PhotoListView` / `PhotoUploadView` chunk） |
| 死代码清除 | 全 `frontend/src` 检索 `associate` | **0 命中** |
| 废弃模型停读 | 检索 `task_items` / `detail.items` | **0 命中** |
| 后端只读 | `git diff --name-only -- backend` | 与开工前**完全相同的 15 个既有文件**，**本任务未新增/修改任何 backend 文件** |
| 实现抽查 | `router/index.ts`（path `/photos` 保留）、`api/index.ts`（六调用面 + `kind` 默认 `homework`）、`PhotoListView.vue`（`group_subject_id` 复核 + 门控 badge + draft/确认/重跑） | 与 §4.1 交付一致 |

**结论：APPROVED**（`m002-dev` 自检与 PM 复验一致；Task-009 关闭）。

### 7.3 执行方 Request 的 PM 裁决（2 条）

**Request-1（API-M002-007 响应：契约 vs 实现不一致）** —— 契约写 `{photo_id, links:[LinkDTO], suggested_at}`；实现（`m002/schemas.py LinkSuggestionOut` + `api/link_routes.py`）为 `{photo_id, status, suggestions:[{link_id, group_subject_id, subject, confidence, source, suggested_at}]}`。
**PM 裁决：以**实现**为准，走契约修订 `CR-004`（Proposed，待用户批准）** —— 理由：`links` 与 `API-M002-003/005` 的「已建立挂接关系」语义冲突，建议态用 `suggestions` 更准确，且实现逐条携带 `confidence/source/suggested_at` 信息更完整。**前端已按运行实现取用，运行期一致，不阻断 ④**；Frozen 契约的正式修订须用户批准后生效。

**Request-2（`GET /photo-gates` 无法按窗口分组 + `POST /completion-analyses` 门控前置失效）** —— **PM 核实为真实缺陷，登记 `BUG-002`，签发 `Task-010`（AGENT-M002）修复**。根因判定（PM 独立核实）：M002 网关消费了**契约外**接口 `get_group_subject`，其返回 `TaskGroupSubjectDTO`（M001 v0.2.0 契约内部服务接口表**未登记**该接口）**不含** `group_key`/`window_type`/`student_id`/`group_id`（group 上下文仅在 `TaskGroupDTO` 上）→ `_to_subject_ref(raw, raw)` 得空串 → `gate_service` 全部落 `""` 单桶、`get_gate(真实 key)` 恒不匹配 → `409 gate_not_satisfied` 不可达。**修复落 M002 侧消费适配，M001 零改动、无需契约变更**。前端 `localGate` 兜底仅为 UI 层，**不能替代后端强制**（非安全边界），故 Task-010 为 ④ 验收的必要前置。
