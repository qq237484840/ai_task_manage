# AGENT_REGISTRY —— Agent 登记表

> 维护：Project Master。新增/调整 Agent 职责、权限、任务时必须更新。
> 每个 Agent 遵守：**Read Scope / Write Scope / Review Scope**（读写审查三权限），禁止越权（见 `AGENT_GUIDE.md`）。
>
> 状态：**已启用**（2026-09-08 登记 V1 模块 Agent）。**M001 Stable 代码基线 v0.1.2 → 契约 v0.2.0 Frozen（用户批准 2026-09-10）**（Task-004 交付 + PM 复核 APPROVED；实施 = **Task-007**）；**M002 代码基线 v0.3.0 → 契约 v0.4.0 Frozen（用户批准 2026-09-10）**（Task-005 交付 + PM 复核 APPROVED；实施 = **Task-008**，Task-002 冻结段增量改接）；**AGENT-M001 Active（Task-003 前端技术栈切换 / ADR-012/CHANGE-002；Task-007 M001 实施）**；**AGENT-M002 Active（Task-008 M002 实施）**；**AGENT-AI Active（Task-006，可启动）**；**AGENT-M003~AGENT-M007 → Inactive（V1 不启用，`ADR-014`）** —— V1 有效 Agent = `AGENT-001` + `AGENT-M001` + `AGENT-M002` + `AGENT-AI`。
>
> **2026-09-10 变更（v0.13.0，CR-003 / ADR-013 / CHANGE-003）**：`CR-003` Approved + `ADR-013` Accepted（双层模型）→ 签发 **Task-004**（AGENT-M001，M001 契约 → v0.2.0 草案）与 **Task-005**（AGENT-M002，M002 契约 → v0.4.0 草案），二者**均为契约文档修订，不写业务代码**；`CHANGE-003` **Executing**。
>
> **2026-09-10 边界决议（v0.14.0，ADR-014，CHANGE-003 §6 Q1~Q4 全部关闭）**：**新增 `AGENT-AI`**（横切 AI 接入层 `app/core/ai/`），签发 **Task-006**（**待启动**：前置 = ② 契约评审 APPROVED）；（**后续 2026-09-10**：② 已完成 = Task-004/005 PM 复核 APPROVED → **Task-006 转为可启动**）**AGENT-M003~AGENT-M007 → Inactive**（V1 不启用：M003/M004 职责并入 M001/M002，M005~M007 后置 V2）；**Task-002 采用「部分冻结 + 定稿后增量改接」**（PD-029）。
>
> **2026-09-10 实施阶段启动（v0.16.0，③ 解禁）**：契约 **M001 v0.2.0 / M002 v0.4.0 经用户批准 Frozen**（`CHANGE-003` ② 关闭）→ 签发 **`Task-007`**（AGENT-M001，M001 实施：事实层按天 → `WindowResolver` → 聚合层 → 链路 T）与 **`Task-008`**（AGENT-M002，M002 实施：入口 `kind` → N:N 挂接 → 逐张复核 → 窗口级门控 → 完成分析；**Task-002 冻结段增量改接**）；**`Task-006`**（AGENT-AI，`app/core/ai/`）**并行可启动**。
>
> **2026-09-10 ③ 实施收口 + 前端任务签发（v0.17.0）**：**`Task-006` / `Task-007` / `Task-008` 三线交付并经 PM 复核 APPROVED**（`CHANGE-003` ③ 后端与横切全部落地：`app/core/ai/` 39 例、M001 v0.2.0 实施、M002 v0.4.0 实施；`main.py` 启动期幂等自愈已接线；全量 `pytest` = **207 passed / 0 failed**）；**`API-M001-018~021` / `API-M002-007~011` Draft → Active**。签发 **`Task-009`**（**AGENT-M002**，前端「作业」域迁移：菜单改名「作业」→ 周次/周末分组 → M002 v0.4.0 前端调用面补齐 → 挂接复核改 `group_subject_id` → 门控/完成分析 UI）——**PM 裁决归属 `AGENT-M002`**（写区 = 前端作业域 + M002 后端，**规避 `frontend/src/api/index.ts` 的跨 Agent 写冲突**）；**`backend/**` 对本任务只读**。
>
> **2026-09-10 `Task-009` 收口 + 门控链路缺陷修复签发（v0.18.0）**：**`Task-009`（前端「作业」域迁移）交付并经 PM 复核 APPROVED**（`vue-tsc -p tsconfig.app.json` **0 error**、`npm run build` **EXIT=0**、全前端 `associate` / `task_items` 命中 **0**、`backend/**` diff 为空；交付 8 文件含新增 `components/PhotoCard.vue`）→ **`CHANGE-003` ③ 前端项关闭**。执行方上报 2 条 Request：**Request-1**（`API-M002-007` 契约 vs 实现不一致）→ PM 裁决**以运行实现为准**，登记 **`CR-004`（Proposed，待用户批准）**；**Request-2**（`GET /photo-gates` 无法按窗口分组 + 完成分析门控前置失效）→ PM 独立核实为**真实后端缺陷**，登记 **`BUG-002`** 并签发 **`Task-010`（AGENT-M002）** 修复 —— **根因 = M002 网关消费了 M001 契约外且不含 group 上下文的 `get_group_subject`**（`group_key` 恒空 → 门控单桶聚合、`409 gate_not_satisfied` 不可达）；**修复落 M002 侧消费适配，M001 零改动、无需契约变更**。**`Task-010` 为 ④ 验收必要前置**（前端 `localGate` 仅为展示层兜底，不构成强制）。
>
> **2026-09-10 `Task-010` 收口（v0.19.0）**：**`BUG-002`（门控链路）修复交付并经 PM 复核 APPROVED → `BUG-002` = Verified、`Task-010` 关闭、`CHANGE-003` ③ 后端修复项关闭** —— `get_group_subject` 默认路径改走**契约内** `list_groups` 回填 group 上下文、**移除契约外消费**；新增真机 `tests/integration/test_m002_gate_real_m001.py` **4 例**（弃 `FakeGateway` 桩，红→绿取证）；全量 `pytest` **211 passed / 0 failed**（基线 207 + 4）；**M001 零改动 / 契约文本零改动 / 前端零改动**（PM 以 diff + mtime 审计双重确认）。PM 复核保留两条后续项 = **`TD-001`**（全量扫描 N+1 放大）+ **`TD-002`**（契约未暴露 `window_task_id`/`task_status`）→ `docs/TECH_DEBT.md` 启用。**④ 验收剧本 7 条已解除前置阻塞、可启动**。
>
> **2026-09-10 `CR-004` Applied + `Task-011` 签发（v0.20.0）**：**`CR-004` 经用户批准 → Applied** —— M002 契约 **v0.4.0 → v0.4.1**（仅 `API-M002-007` 响应体：`{photo_id, status, suggestions:[LinkSuggestionItem]}`，**非破坏性**；**前端零返工、后端零代码改动**，属「文档追平实现」；PM 读码核实 `schemas.py` + `link_routes.py` 后落地 9 处文档）。**签发 `Task-011`（AGENT-M002）阶段 ④ 验收** = `CLARIFICATION` §5 **验收剧本 7 条**（含浏览器级）+ 全系统回归（域 A/B/C；Mock 必跑 / 真实三方双跑）；**只读边界**：业务代码零改动，缺陷只登记不修复（`TD-001`/`TD-002` 不属本任务）。
>
> **2026-09-10 `Task-011` 复核 + AI 通路缺陷派单（v0.21.0）**：**`Task-011` 已完成** —— PM **独立复核（未采信自述，全部复现）**：`pytest -q -rxX` → exit 0 / **227** 点 / **2 xfail**；`vue-tsc -p tsconfig.app.json` → **TSC_EXIT=0**；`npm run build` → **BUILD_EXIT=0**；**只读边界成立**（`git diff` 8 文件全属既有基线 + **mtime 审计 COUNT=0**）；浏览器级证据采信（`.e2e/acceptance.mjs` 真实 Edge 驱动 `frontend/dist`）。**PM 裁决 = ④ 条件达成（不通过收口）**，3 项缺口：`BUG-004`（高，链路 T 核心 AI 解析通路不可达 —— M001 位置参数调用 keyword-only `parse_task_spec` + `except Exception: pass` 静默兜底）、`BUG-003`（中，Mock 读 `candidate_subjects` 而服务注入 `candidates` → 建议恒空）、真实三方无密钥未覆盖（已知边界）。两缺陷经 **PM 读码逐字确认 → Confirmed**，**派单 `Task-012`（`AGENT-M001`）/ `Task-013`（`AGENT-AI`）并行修复**；修复后由 **`Task-014`（`AGENT-M002`）去替身复审** → ④ 再判。
>
> **2026-09-10 ④ 收口（v0.22.0）**：**`Task-012`/`Task-013` 修复均经 PM 复核成立（`Fixed`）+ `Task-014`（`AGENT-M002`）去替身复审经 PM 独立复核成立**（亲手判别力：关 Mock 兜底 → 边界 2 例 `FF`/`RED_EXIT=1`；还原 → 4 passed/`GREEN_EXIT=0`；全量 `pytest` **237 / 0 failed**；浏览器级剧本 5 **18/18 PASS**；写区双证成立；`TD-003` 垫片清理 + PM 裁决不立 `TD-004`）→ **`BUG-003`/`BUG-004` → `Verified`** → **④ 判达成 → `CHANGE-003` 关闭（Closed）**。**三个任务均已完成关闭，无 Active 任务**；已知边界 = 真实三方 AI 无密钥（Mock 通路证据显著标注）。

## Agent 登记表

| Agent ID | 名称 | 职责 | 关联模块 | Read Scope | Write Scope | 状态 | 当前任务 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `AGENT-001` | Project Master（总控） | 需求/架构/模块/接口/数据治理、Agent 分工、变更治理、知识体系、最终审核 | 全部 | 全部文档 | 治理层文档（docs 根、Registry、ADR、变更记录）；不直接代写模块业务代码 | Active | **CHANGE-001 复核 APPROVED（2026-09-08）→ 收口 v0.11.0**（API-M001-013~017 登记、M001 定稿 v0.1.2）；**Task-002 签发**（AGENT-M002 编码 M002 v0.3.0）；**v0.12.0：ADR-012 前端技术栈切换确认（用户 Q1~Q3）+ CHANGE-002 立项 + Task-003 签发**（AGENT-M001）；监督 Task-003（前端切换 DoD）与 M002 编码（模块级 DoD），域 M-A 全量验收随**链路 T/H + `app/core/ai/`**（原 M003 职责）统一执行 |
| `AGENT-M001` | 作业任务管理 Agent | 模块内设计/编码/测试/文档；创建任务域 | M001 | PROJECT/ARCHITECTURE/M001/上游与依赖方 API | M001 | Active | **`Task-007`（M001 实施，2026-09-10 签发，可启动）**：契约 **v0.2.0 Frozen** 已就绪 → 事实层按天 → `WindowResolver` → 聚合层 → 链路 T。前序：Task-004（契约修订）已 PM 复核 APPROVED；**Task-003（前端技术栈切换 / ADR-012/CHANGE-002）并行**（写区不重叠）；Task-001 / Task-CHG 已完成（M001 v0.1.2 Stable，89 测试全绿）；**`Task-007`（M001 实施）→ 已完成（PM 复核 APPROVED，2026-09-10）**；**追加：`Task-012`（`BUG-004` 修复，高）2026-09-10 签发 → 已完成（PM 复核成立 = `Fixed`）** —— 写区 `modules/m001/services/task_parser.py` + M001 侧用例；根因经 PM 读码确认（位置参数调用 keyword-only `parse_task_spec` + `except Exception: pass` 静默兜底，降级不可观测）；修法 = 关键字传参 + `SourceInput` 转换（只转发文本源）+ `logger.warning` 可观测 + `session` 单行下传（PM 裁决「最小扩权」）；`BUG-004` → **Verified**（经 `Task-014` 复审） |
| `AGENT-M002` | 作业图片采集与归属 Agent | 上传/质检/归一/受控存储/照片归属状态机（AI 挂接建议 + 逐张复核兜底，**N:N**，随 CR-003） | M002 | +M001 API（**契约 v0.2.0 Frozen**，聚合层内部接口）、`app/core/ai/`（挂接与分析） | M002 | **Active**（`Task-008` 实施，2026-09-10 签发，可启动） | **`Task-008`（M002 实施，2026-09-10 签发，可启动）**：契约 **v0.4.0 Frozen** 已就绪 → 入口 `kind` → **N:N 挂接** → 逐张复核 → 窗口级门控 → 完成分析。**Task-002 处置（PD-029 / `ADR-014` 决议 5）**：**部分冻结 + 增量改接** —— 质检/归一/受控存储/受控取图/双主体 API 保持；**「归属/挂接」段自本任务起按 v0.4.0 增量改接**，返工面限归属段。前序 Task-005（契约修订）已 PM 复核 APPROVED。**追加：`Task-009`（前端「作业」域迁移，2026-09-10 签发，可启动）** —— 菜单改名「作业」+ 周次/周末分组展示 + M002 v0.4.0 前端调用面（`/photos/{id}/links`、`/link-suggestions`、`/photo-gates`、`/completion-analyses*`）+ 挂接复核改 `group_subject_id`（不再读 `task_items`）+ 门控/完成分析 UI；**`backend/**` 只读**，禁改 M001 前端段。**已完成 → PM 复核 APPROVED（2026-09-10）**；**追加：`Task-010`（门控链路缺陷修复，`BUG-002`）→ 已完成（PM 复核 APPROVED，2026-09-10）**；**追加：`Task-011`（阶段 ④ 验收 + 全系统回归）→ 已完成（PM 独立复核 2026-09-10：④ = 条件达成，不通过收口）**；**追加：`Task-014`（④ 去替身复审：移除 `m002_ai_port` 端口替身 + 边界 2 例走真实 AI 通路 + `TD-003` 垫片清理 + 剧本 4/5 真机 + 浏览器级剧本 5）→ 已完成（PM 复核成立，2026-09-10；`BUG-003` → Verified，`CHANGE-003` → Closed）** |
| `AGENT-M003` | ~~AI 作业识别 Agent~~ | ~~任务布置单解析（链路 T）+ 挂接建议（链路 H）~~ → **职责并入 M001（链路 T）+ M002（链路 H）+ `app/core/ai/`** | ~~M003~~（Deferred） | — | —（V1 不启用） | **Inactive** | **V1 不启用（`ADR-014` 决议 1）**；Module ID 保留，V2 回归时重评估 |
| `AGENT-M004` | ~~作业任务匹配 Agent~~ | ~~聚合子任务级完成结论~~ → **职责并入 M002** | ~~M004~~（Deferred） | — | —（V1 不启用） | **Inactive** | **V1 不启用（`ADR-014` 决议 1）** |
| `AGENT-M005` | ~~AI 作业质量评价 Agent~~ | ~~六维评分~~ → **后置 V2**（`REQ-005` Deferred） | ~~M005~~（Deferred） | — | —（V1 不启用） | **Inactive** | **V1 不启用（`ADR-014` 决议 2）**；V2 回归时重评估 |
| `AGENT-M006` | ~~AI 教师评价 Agent~~ | ~~评语与分级重写建议~~ → **后置 V2**（`REQ-006` Deferred） | ~~M006~~（Deferred） | — | —（V1 不启用） | **Inactive** | **V1 不启用（`ADR-014` 决议 2）** |
| `AGENT-M007` | ~~今日报告 Agent~~ | ~~聚合展示~~ → **后置 V2**（`REQ-007` Deferred） | ~~M007~~（Deferred） | — | —（V1 不启用） | **Inactive** | **V1 不启用（`ADR-014` 决议 2）** |
| `AGENT-AI` | 横切 AI 接入层 Agent | **`app/core/ai/`**：Provider 抽象（Vision/OCR/LLM）+ prompt 版本管理 + 结果 **schema 校验** + 超时/重试/**降级** + `DATA-009` 统一调用记录；**不承载业务语义** | 横切（**不设业务 Module ID**） | M001/M002 契约（结果结构边界）、`ADR-011`、`docs/CONFIGURATION.md` | **`backend/app/core/ai/**` + `backend/tests/**`**（新增用例） | **Active（可启动）** | **Task-006**（2026-09-10 签发，任务书 `docs/agents/Task-006.md`）；**启动前置 = `CHANGE-003` ② 契约评审 APPROVED 已于 2026-09-10 满足**（Contract First）；**`Task-006` → 已完成（PM 复核 APPROVED，2026-09-10）**；**追加：`Task-013`（`BUG-003` 修复，中）2026-09-10 签发 → 已完成（PM 复核成立 = `Fixed`，含 `Task-013-D1` API 面补证）** —— 写区 `backend/app/core/ai/**` + AI 层用例（新增独立文件）；根因经 PM 读码确认（Mock 读 `candidate_subjects` vs 服务注入 `candidates`；且既有用例直调 Provider 手写 key → 漏检）；`BUG-003` → **Verified**（经 `Task-014` 去替身复审） |

Read Scope 基座 = 全部治理文档（INDEX/规则/Registry）；上表为模块级追加。Write Scope 均含本模块 `docs/modules/Mxxx/` 与后续 `src/modules/Mxxx/`。

## 角色划分总则

- **决策者（用户/项目所有者）**：提供需求、拍板关键决策
- **Project Master**：治理、架构、分配任务、验收
- **模块 Agent**：模块内设计/编码/测试/文档，不越权改动其他模块
- **分工与权限模型**：见 `AGENT_GUIDE.md`（Read/Write/Request/Forbidden）

## 越权边界（对模块 Agent 生效）

- Request（可申请，不得直接改）：依赖模块 API 变更、共享代码变更、核心数据模型变更
- Forbidden：直接修改其他模块代码/API/数据库；修改总体架构；提前实现 V2+ 功能（ADR-002）

## Agent ID 规则

格式 `AGENT-001` / `AGENT-M001`；分配权归属 Project Master（详见 `ID_GOVERNANCE.md`）。

## 当前待分配

| 事项 | 说明 |
| --- | --- |
| 模块任务单 | **Task-001/Task-CHG 已完成**（M001 v0.1.2）；**Task-002 已完成**（冻结段随 `Task-008` 增量改接收口，PD-029）；**Task-003 Active**（AGENT-M001 前端技术栈切换，`docs/agents/Task-003.md`）；**Task-004 / Task-005 已完成**（契约修订，PM 复核 APPROVED 2026-09-10）；**`Task-006` / `Task-007` / `Task-008` 已完成**（PM 复核 APPROVED 2026-09-10：`app/core/ai/` / M001 实施 / M002 实施）；**`Task-009` 已完成**（PM 复核 APPROVED 2026-09-10，前端「作业」域迁移）；**`Task-010` 已完成**（PM 复核 APPROVED 2026-09-10，门控链路修复 `BUG-002` → Verified，`docs/agents/Task-010.md`） |
| **`Task-011` 已完成**（AGENT-M002，阶段 ④ 验收剧本 7 条 + 全系统回归；PM 复核 = **条件达成**，见 `docs/agents/Task-011.md` §8） |
| **`Task-012` 已完成（PM 复核成立 = `Fixed`）**（AGENT-M001，`BUG-004` 修复：链路 T 核心 AI 通路可达 + 降级可观测 → `Verified`，`docs/agents/Task-012.md`） |
| **`Task-013` 已完成（PM 复核成立 = `Fixed`，含 `Task-013-D1`）**（AGENT-AI，`BUG-003` 修复：Mock 挂接建议 key 对齐 + 装配路径防漂移用例 → `Verified`，`docs/agents/Task-013.md`） |
| **`Task-014` 已完成（PM 复核成立）**（AGENT-M002，④ 去替身复审：移除 `m002_ai_port` + `TD-003` 清理 + 剧本 4/5 真机 + 浏览器级 18/18，`docs/agents/Task-014.md`）→ **`CHANGE-003` 关闭，任务队列清空（无 Active）** |
| 横切 AI 接入层 | `app/core/ai/`（Provider 抽象 + prompt + schema 校验 + 降级）**执行方 = `AGENT-AI`**（`ADR-014` 决议 3；任务书 `docs/agents/Task-006.md`）——**已分配，无待分配项** |

## 模块开发顺序（需求 §三，随 `ADR-014` 收窄）

`M001 → M002 → （V1 共享/基础设施：app/core/ai/）→ 全系统回归`

> **收窄说明（2026-09-10，`ADR-014`）**：原序列 `M001 → M002 → M003 → M004 → M005 → M006 → M007` **不再适用于 V1** —— M003/M004 职责已并入 M001/M002（链路 T/H），M005~M007 后置 V2。**V1 内不再签发 M003~M007 的模块任务**；"前序未验收不进入下一核心模块"的约束在 M001 → M002 之间继续生效。
