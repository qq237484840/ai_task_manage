# API_REGISTRY —— API 登记总表（导航）

> 维护：Project Master / 各模块 Owner Agent。
> 注意：本表只做 **导航与状态登记**；API 的完整定义（请求/响应/错误/契约）以所属模块的 `MODULE_API.md` 为权威源，本表不复制定义（Single Source of Truth，见 `DEVELOPMENT_GUIDE.md`）。
>
> **2026-09-10 变更（v0.13.0，CR-003 / CHANGE-003）**：`CR-003` Approved + `ADR-013` Accepted（双层模型）→ **M001（API-M001-001~017）与 M002（API-M002-001~006）契约均待按 CR-003 修订**（Task-004 / Task-005）；**新增端点 API ID 由 Project Master 分配**（禁止模块 Agent 自行编号），申请清单见本文末「CR-003 待分配 API ID」。
>
> **2026-09-10 V1 范围决议（v0.14.0，`ADR-014`）**：**V1 仅登记 M001 + M002 两模块 API** + 横切 `app/core/ai/` 的内部能力接口（**不设 API ID**，非对外 HTTP 端点，由 M001/M002 契约引用）；**M003~M007 的对外 API 不在 V1 登记范围**（模块 Deferred）。**V1 的 API 分配申请仅限 M001/M002 契约修订所需端点**；M005~M007 相关端点申请随 V2 回归。
>
> 状态：**V1 启用，M001 Frozen / M002 Frozen 已登记**（2026-09-08）。API-M001-001~012 **Frozen**（修改须走 CR；M001 变更 `CR-001`/`ACR-001`/`CR-002`/`ACR-002` 均 **Approved** 并随 **CHANGE-001 已完成（PM 复核 APPROVED，2026-09-08）**落地，冻结面契约按变更后实况更新于 `MODULE_API.md`）；**API-M001-013~017 新增登记（Active，ACR-001 学生子账号端点，CHANGE-001 引入）**；API-M002-001~006 **Frozen**（契约基线 **v0.3.0**，2026-09-08 用户批准；先采后认重构 + 内容级判定口径；v0.1.0 四接口语义废弃）；~~M003~M007 在各自契约阶段逐条登记~~ → **M003~M007 → Deferred（V1 不登记，`ADR-014`）**；登记前不得实现无契约接口。**2026-09-10（CR-003 / CHANGE-003 ② 完成）**：M001/M002 契约修订交付并经 PM 复核 APPROVED → 新增 **`API-M001-018~021`**、**`API-M002-007~011`**（状态 **Draft**，随 ③ 实施转 Active；既有 `API-M001-007/009/010`、`API-M002-001/002/003/005` 为**语义修订**，不新增 ID）。**2026-09-10（③ 实施完成，`Task-007`/`Task-008` 交付 + PM 独立复验）**：`API-M001-018~021`、`API-M002-007~011` **Draft → Active**（PM 实测路由存在 + 用例覆盖）；`API-M002-005` 路径按 v0.4.0 修订为 `POST /api/v1/photos/{photo_id}/links`（原 `/associate` 已移除，属已批准契约内的语义修订）。**2026-09-10（`CR-004` Applied，M002 契约 v0.4.0 → v0.4.1）**：`API-M002-007` 响应体以**运行实现为准**修订为 `{photo_id, status, suggestions:[LinkSuggestionItem]}`（**非破坏性**；前端零返工、后端零代码改动；状态保持 **Active**，端点在册不变）。

## API 登记表

| API ID | 名称 | Owner 模块 | 版本 | 状态 | 方法/路径(摘要) | 详细定义位置 |
| --- | --- | --- | --- | --- | --- | --- |
| API-M001-001 | 注册家庭账号 | M001 | v0.1 | Frozen | POST `/api/v1/family/register` | `docs/modules/M001/MODULE_API.md` |
| API-M001-002 | 家庭登录 | M001 | v0.1 | Frozen | POST `/api/v1/family/login` | `docs/modules/M001/MODULE_API.md` |
| API-M001-003 | 家庭登出 | M001 | v0.1 | Frozen | POST `/api/v1/family/logout` | `docs/modules/M001/MODULE_API.md` |
| API-M001-004 | 创建学生档案 | M001 | v0.1 | Frozen | POST `/api/v1/students` | `docs/modules/M001/MODULE_API.md` |
| API-M001-005 | 学生档案列表 | M001 | v0.1 | Frozen | GET `/api/v1/students` | `docs/modules/M001/MODULE_API.md` |
| API-M001-006 | 更新学生档案 | M001 | v0.1 | Frozen | PATCH `/api/v1/students/{student_id}` | `docs/modules/M001/MODULE_API.md` |
| API-M001-007 | 创建作业任务 | M001 | v0.1 | Frozen | POST `/api/v1/tasks` | `docs/modules/M001/MODULE_API.md` |
| API-M001-008 | 任务列表 | M001 | v0.1 | Frozen | GET `/api/v1/tasks` | `docs/modules/M001/MODULE_API.md` |
| API-M001-009 | 任务详情 | M001 | v0.1 | Frozen | GET `/api/v1/tasks/{task_id}` | `docs/modules/M001/MODULE_API.md` |
| API-M001-010 | 更新任务 | M001 | v0.1 | Frozen | PATCH `/api/v1/tasks/{task_id}` | `docs/modules/M001/MODULE_API.md` |
| API-M001-011 | 推进任务状态 | M001 | v0.1 | Frozen | POST `/api/v1/tasks/{task_id}/status` | `docs/modules/M001/MODULE_API.md` |
| API-M001-012 | 学校字典列表 | M001 | v0.1 | Frozen | GET `/api/v1/schools` | `docs/modules/M001/MODULE_API.md` |
| API-M001-013 | 开通学生子账号 | M001 | v0.1 | Active | POST `/api/v1/students/{student_id}/account` | `docs/modules/M001/MODULE_API.md` |
| API-M001-014 | 更新学生子账号 | M001 | v0.1 | Active | PATCH `/api/v1/students/{student_id}/account` | `docs/modules/M001/MODULE_API.md` |
| API-M001-015 | 学生登录 | M001 | v0.1 | Active | POST `/api/v1/student/login` | `docs/modules/M001/MODULE_API.md` |
| API-M001-016 | 学生登出 | M001 | v0.1 | Active | POST `/api/v1/student/logout` | `docs/modules/M001/MODULE_API.md` |
| API-M001-017 | 学生主体信息 | M001 | v0.1 | Active | GET `/api/v1/student/me` | `docs/modules/M001/MODULE_API.md` |
| API-M001-018 | 解析结果确认（含隐式确认） | M001 | v0.2.0 | Active | POST `/api/v1/tasks/{task_id}/parse-confirmation` | `docs/modules/M001/MODULE_API.md` |
| API-M001-019 | 聚合任务列表 | M001 | v0.2.0 | Active | GET `/api/v1/task-groups` | `docs/modules/M001/MODULE_API.md` |
| API-M001-020 | 聚合任务详情 | M001 | v0.2.0 | Active | GET `/api/v1/task-groups/{group_id}` | `docs/modules/M001/MODULE_API.md` |
| API-M001-021 | 手工改归属日 | M001 | v0.2.0 | Active | POST `/api/v1/tasks/{task_id}/belong-date` | `docs/modules/M001/MODULE_API.md` |
| API-M002-001 | 创建上传批次 | M002 | v0.3.0 | Frozen | POST `/api/v1/upload-batches` | `docs/modules/M002/MODULE_API.md` |
| API-M002-002 | 上传作业照片 | M002 | v0.3.0 | Frozen | POST `/api/v1/photos` | `docs/modules/M002/MODULE_API.md` |
| API-M002-003 | 照片列表/待处理队列 | M002 | v0.3.0 | Frozen | GET `/api/v1/photos` | `docs/modules/M002/MODULE_API.md` |
| API-M002-004 | 受控取图 | M002 | v0.3.0 | Frozen | GET `/api/v1/photos/{photo_id}/content` | `docs/modules/M002/MODULE_API.md` |
| API-M002-005 | 照片挂接复核（逐张 accept/reject/relink，v0.4.0 语义修订；原「照片归属操作」`/associate` 已移除） | M002 | v0.4.0 | Frozen | POST `/api/v1/photos/{photo_id}/links` | `docs/modules/M002/MODULE_API.md` |
| API-M002-006 | 撤销/清理照片 | M002 | v0.3.0 | Frozen | DELETE `/api/v1/photos/{photo_id}` | `docs/modules/M002/MODULE_API.md` |
| API-M002-007 | 挂接建议查询/重试（v0.4.1 响应体 = `{photo_id, status, suggestions[]}`，`CR-004` Applied） | M002 | v0.4.1 | Active | GET `/api/v1/photos/{photo_id}/link-suggestions` | `docs/modules/M002/MODULE_API.md` |
| API-M002-008 | 门控状态查询 | M002 | v0.4.0 | Active | GET `/api/v1/photo-gates` | `docs/modules/M002/MODULE_API.md` |
| API-M002-009 | 完成分析生成 | M002 | v0.4.0 | Active | POST `/api/v1/completion-analyses` | `docs/modules/M002/MODULE_API.md` |
| API-M002-010 | 完成分析确认 | M002 | v0.4.0 | Active | POST `/api/v1/completion-analyses/{analysis_id}/confirmation` | `docs/modules/M002/MODULE_API.md` |
| API-M002-011 | 完成分析重跑 | M002 | v0.4.0 | Active | POST `/api/v1/completion-analyses/{analysis_id}/rerun` | `docs/modules/M002/MODULE_API.md` |

## 规划中的 API 所有权（待契约设计）

| 模块 | 预期对外能力（占位，非契约） |
| --- | --- |
| M001 | 作业任务 CRUD、任务状态推进、任务查询（供采集/判定/评分）；**随 CR-003 新增**：输入源上传、导入确认（含隐式确认）、归属窗口查询、聚合查询 | 
| M002 | 已登记 API-M002-001~006（Frozen，v0.3.0；上传批次/照片上传/照片列表/受控取图/归属操作/撤销清理）；**随 CR-003 修订**：入口 `kind`、N:N 挂接建议、逐张复核、门控查询、完成分析确认 | 
| ~~M003~~ | **Deferred（V1 不登记）**：任务布置单解析（链路 T）归 **M001**、挂接建议（链路 H）归 **M002**（`ADR-014` 决议 1） | 
| ~~M004~~ | **Deferred（V1 不登记）**：聚合子任务级完成结论归 **M002**（`ADR-014` 决议 1） | 
| ~~M005~~ | **Deferred（V2，V1 不登记）**：评分执行与结果查询（`ADR-014` 决议 2） | 
| ~~M006~~ | **Deferred（V2，V1 不登记）**：教师评价生成与查询（`ADR-014` 决议 2） | 
| ~~M007~~ | **Deferred（V2，V1 不登记）**：今日报告生成与查询（`ADR-014` 决议 2） | 
| AI 抽象 | Provider 统一调用契约（Vision/OCR/LLM）、调用记录写入；**随 CR-003**：落位 `app/core/ai/` —— **执行方 = `AGENT-AI`（Task-006）**；**非对外 HTTP 端点（内部能力接口，不分配 API ID）** | 

## API ID 规则

- 格式 `API-M001-001`（`API-<ModuleID>-<模块内序号>`），连续编号不重复
- 分配权归属 Project Master（详见 `ID_GOVERNANCE.md`）

## API 状态机

`Draft → Active → Frozen → Deprecated → Removed`

- 进入 `Frozen` 后，修改必须走变更流程（CR），禁止无记录修改其他模块已使用的 API
- Breaking Change 处理：版本化 / 兼容 / 迁移 / 弃用 / 通知消费者（规则见 `DEVELOPMENT_GUIDE.md`）

## API 契约要素（权威模板，属模块 `MODULE_API.md`）

每个 API 至少描述：API ID / Name / Description / Owner Module / Version / Method / Path / Authentication / Authorization / Request / Response / Error / Timeout / Rate Limit / Idempotency / Transaction / Side Effect / Compatibility / Example。

## CR-003 新增 API ID（申请清单 → **已由 PM 分配**，2026-09-10）

> 来源：`docs/changes/CHANGE-003.md` §2.1 A9 / §2.2 B8。Task-004 / Task-005 交付「申请分配清单」后由 Project Master 分配正式 ID 并回填上表。**禁止模块 Agent 自行编号**（`ID_GOVERNANCE.md`）。
>
> **V1 范围收窄（2026-09-10，`ADR-014`）**：本清单**仅受理 M001 / M002 契约修订所需端点**；横切 `app/core/ai/` 的能力接口为**内部契约（不分配 API ID）**；M005~M007 相关对外端点申请随 **V2** 回归。

| 申请方 | 预期端点（占位，非契约） | 分配 ID |
| --- | --- | --- |
| M001（Task-004） | **已分配（2026-09-10）**：解析结果确认 → `API-M001-018`；聚合任务列表 → `API-M001-019`；聚合任务详情 → `API-M001-020`；手工改归属日 → `API-M001-021`（**注**：任务输入源上传 = 修订既有 `API-M001-007`（POST `/tasks`），解析草稿随任务详情 `API-M001-009`，**均不新增 ID**） | **API-M001-018~021**（状态 Draft，随实施转 Active） |
| M002（Task-005） | **已分配（2026-09-10）**：挂接建议查询/重试 → `API-M002-007`；门控状态查询 → `API-M002-008`；完成分析生成 → `API-M002-009`；完成分析确认 → `API-M002-010`；完成分析重跑 → `API-M002-011`（**注**：入口 `kind` = 修订 `API-M002-001`，逐张复核 = 修订 `API-M002-005`，**均不新增 ID**） | **API-M002-007~011**（状态 Draft，随实施转 Active） |
| 横切 `app/core/ai/` | Provider 统一调用契约、调用记录写入 —— **执行方 = `AGENT-AI`（Task-006）**；**内部能力接口，由 M001/M002 契约引用，不分配 API ID** | *不适用* |
