# INDEX —— 项目知识地图

> 本文件是整个项目的 **Knowledge Map / 知识导航**。目标是：任何 Agent 在 30 秒内定位到目标知识，而不是扫描全项目。
>
> 维护规则：新增任何文档/模块/API/需求/ADR/Agent 记录后，必须同步更新本索引。若索引与实际不符，视为文档漂移（见 `DEVELOPMENT_GUIDE.md` 的代码-文档一致性要求）。

## 阅读路线（Context Loading Strategy）

```
任务 / Task
  ↓
SYSTEM_SUMMARY（几分钟理解全系统）
  ↓
目标模块 MODULE_SUMMARY（30 秒理解模块）
  ↓
Contract → API → Data → 必要 Code
```

最小必要上下文原则：优先 `索引 → 摘要 → 契约 → 必要代码`，禁止无目的全项目扫描。

## 文档地图

| 文档 | 层级 | 用途 | 状态 |
| --- | --- | --- | --- |
| `PROJECT.md` | L0 项目 | 项目是什么/为什么/给谁用/目标/约束 | V1 已填充 |
| `ROADMAP.md` | L2 计划 | **V1 功能域主线（A~D 里程碑 + 验收 + 横切能力）** | **v0.9.0 基线**（2026-09-08，功能域主线重排）；**2026-09-10 随 ADR-014 收窄：V1 = 域 A/B/C，域 D 后置 V2** |
| `SYSTEM_SUMMARY.md` | 系统摘要 | 几分钟理解整个系统 | V1 已填充 |
| `ARCHITECTURE.md` | L1 系统 | 总体/技术/部署/数据/安全架构 | V1 高层草案 |
| `REQUIREMENTS.md` | 需求 | 需求登记总表（权威源） | Approved（**REQ-001~010**）；**2026-09-10 CR-003 语义重构：REQ-001~007 已精校、REQ-010 新增**；**随 ADR-014：REQ-005~007 → Deferred（后置 V2）** |
| `MODULE_REGISTRY.md` | L3 模块 | 模块导航总表 | V1 已登记（M001~M007）；**2026-09-10 随 CR-003/ADR-014 同步：M001/M002 契约修订已完成（PM 复核 APPROVED）；M003/M004 → Deferred（职责并入 M001/M002）；M005~M007 → Deferred（V2）** |
| `API_REGISTRY.md` | L4 接口 | API 导航总表 | 启用（契约阶段登记） |
| `DATA_MODEL.md` | L5 数据 | 核心数据/所有权 | V1 实体草案（**DATA-012~018 新增**，v0.13.0） |
| `CONFIGURATION.md` | 治理 | 配置项登记（含生效与锁定规则） | **已启用**（2026-09-10，CR-003 归属与窗口配置） |
| `AGENT_REGISTRY.md` | Agent | Agent 分工与权限 | V1 已登记（含 AGENT-M001~M007）；**Task-004（AGENT-M001）/ Task-005（AGENT-M002）已完成（PM 复核 APPROVED，2026-09-10）**；**随 ADR-014：新增 `AGENT-AI`（Task-006）、AGENT-M003~M007 → Inactive**；**2026-09-10（v0.17.0）：`Task-006`/`Task-007`/`Task-008` 已完成（PM 复核 APPROVED）；签发 `Task-009`（AGENT-M002，前端「作业」域迁移）**；**2026-09-10（v0.18.0）：`Task-009` 已完成；签发 `Task-010`**；**2026-09-10（v0.19.0）：`Task-010` 已完成（PM 复核 APPROVED）；`BUG-002` → Verified；登记 `TD-001`/`TD-002`（`TECH_DEBT.md` 启用）**；**2026-09-10（v0.20.0）：`CR-004` 经用户批准 → **Applied**（M002 契约 v0.4.0 → v0.4.1）；签发 `Task-011`（AGENT-M002，阶段 ④ 验收 + 全系统回归）**；**2026-09-10（v0.21.0）：`Task-011` 已完成（PM 独立复核 = ④ **条件达成**，不通过收口）；`BUG-003`/`BUG-004` → **Confirmed**；签发 `Task-012`（AGENT-M001）/ `Task-013`（AGENT-AI）并行修复 AI 通路缺陷**；**2026-09-10（v0.22.0）：`Task-012`/`Task-013` 修复收口（`Fixed`）+ `Task-014`（AGENT-M002）**去替身复审**经 PM 亲手判别力复现成立 → `BUG-003`/`BUG-004` → **Verified**；`CHANGE-003` → **Closed**；`TD-003` → Closed** |
| `AGENT_GUIDE.md` | Agent | 模块 Agent 操作规范/交付物 | 已启用 |
| `DEVELOPMENT_GUIDE.md` | 治理 | 开发流程/变更治理/评审 | 已启用 |
| `ID_GOVERNANCE.md` | 治理 | ID 分配规则与唯一性约束 | 已启用 |
| `PROJECT_STATUS.md` | 状态 | 当前阶段/风险/待决 | **v0.22.0**（④ 验收**收口** = `Task-014` 去替身复审经 PM 复核成立；`BUG-003`/`BUG-004` → **Verified**；`CHANGE-003` → **Closed**；M001/M002 均 **Stable**；`CR-004` Applied → M002 契约 **v0.4.1**） |
| `CHANGELOG.md` | 记录 | 变更历史 | **v0.22.0** |
| `ASSUMPTIONS.md` | 记录 | 假设登记 | ASM-001~011 |
| `RISK_REGISTER.md` | 记录 | 风险登记 | 已启用（**RISK-001~012**；RISK-010/011 随 CR-003 新增；**RISK-012 随 ADR-014 新增**） |
| `requirements/REQ-001~010.md` | 需求 | 单条需求详情 | Approved（REQ-010 随 CR-003，2026-09-10；REQ-001~007 已按 CR-003 精校）；**REQ-005~007 → Deferred（V2，随 ADR-014）** |
| `adr/ADR-001.md` | ADR | 架构决策记录 | 已启用 |
| `adr/ADR-002.md` | ADR | V1 范围控制 | Accepted |
| `adr/ADR-003.md` | ADR | AI 评价边界与原则 | Accepted |
| `adr/ADR-004.md` | ADR | 技术栈：H5 + FastAPI + SQLite 单体（PD-003） | Accepted |
| `adr/ADR-005.md` | ADR | 纯家庭模式身份模型（PD-004） | Accepted |
| `adr/ADR-006.md` | ADR | 正确度分科混合判定（PD-005） | **Superseded（→ ADR-010，v0.9.0）** |
| `adr/ADR-007.md` | ADR | AI Provider 抽象 + Mock 先行（PD-006） | **Superseded（→ ADR-011，v0.9.0）** |
| `adr/ADR-008.md` | ADR | 学校基础字典=全局共享只读（REQ-009/DATA-011，ADR-005 限定例外） | Accepted |
| `adr/ADR-009.md` | ADR | 两级主体身份：家庭账号家长 + 学生子账号（PD-016） | Accepted（落地随 ACR-001） |
| `adr/ADR-010.md` | ADR | 内容级主客观全判 + 端到端直判（PD-018/021/022，取代 ADR-006） | **Superseded（判定粒度 → ADR-013，v0.13.0）**；直判/依据/置信度/复核/不武断原则由 ADR-013 继承 |
| `adr/ADR-011.md` | ADR | AI Provider 真实三方默认，Mock 降级（PD-019，取代 ADR-007） | **Accepted**（2026-09-08 随 ACR-002） |
| `adr/ADR-012.md` | ADR | 前端技术栈统一：Vue3+Vite+TS+Vant 4，FastAPI 托管 dist（PD-025） | **Accepted**（2026-09-08） |
| `adr/ADR-013.md` | ADR | **作业归属与判定双层模型：按天事实层 + 跨天聚合层（判定落聚合层）** | **Accepted**（2026-09-10，随 CR-003；取代 ADR-010 判定粒度） |
| `adr/ADR-014.md` | ADR | **V1 范围收窄与横切 AI 接入层执行方**（M003/M004 职责吸收；M005~M007 与 REQ-005~007 后置 V2；`app/core/ai/` = `AGENT-AI`） | **Accepted**（2026-09-10，用户逐项拍板；关闭 CHANGE-003 §6 Q1~Q3） |
| `requirements/CLARIFICATION-2026-09-10.md` | 需求 | **需求澄清定稿（A~F 分支 + 差距分析 + V1 范围 + 验收剧本 7 条）** | **用户逐条确认**（2026-09-10）；需求 ID = **REQ-010**（已分配） |
| `changes/CR-003.md` | 变更 | 作业任务语义重构 + 归属与判定双层模型 | **Approved**（2026-09-10） |
| `changes/CHANGE-003.md` | 变更执行 | CR-003 执行（① 需求落库 → ② 契约修订评审 → ③ 实施 → ④ 验收剧本 7 条） | **已完成（Closed，2026-09-10 PM 复核 APPROVED）**（② = Task-004/005 契约定稿；③ = Task-006/007/008/009/010（`BUG-002` → Verified）；**④ = `Task-011` 取证 → `Task-012`/`Task-013` 修复 → `Task-014` 去替身复审经 PM 复核成立 → 双 BUG Verified → ④ 判达成**） |
| `changes/BUG-001.md` | 缺陷 | 任务列表页空筛选 query（`?status=&student_id=`）→ 422 | **已修复**（2026-09-10） |
| `changes/BUG-002.md` | 缺陷 | `GET /photo-gates` 无法按窗口分组 + 完成分析门控前置失效（M002 消费契约外 `get_group_subject`，`group_key` 恒空） | **Verified（`Task-010` 修复交付，PM 复核 APPROVED 2026-09-10）** |
| `changes/BUG-003.md` | 缺陷 | `MockVisionProvider` 读 `candidate_subjects` 而 `AIService` 注入 `candidates` → Mock 挂接建议恒空 | **Verified（`Task-013` 修复 + `Task-013-D1` API 面补证 + `Task-014` 去替身复审，PM 亲手红→绿 2026-09-10）** |
| `changes/BUG-004.md` | 缺陷 | M001 `default_parser` 以位置参数调用 keyword-only `parse_task_spec` → 核心 AI 解析链路被 `except Exception: pass` 静默降级 | **Verified（`Task-012` 修复 + `Task-014` 真实装配路径复审成立，PM 复核 2026-09-10）** |
| `changes/CR-004.md` | 变更 | M002 `API-M002-007` 挂接建议响应体修订（以运行实现为准：`status` + `suggestions[]`） | **Applied（用户批准 2026-09-10；M002 契约 v0.4.0 → v0.4.1；仅文档，前后端零改动）** |
| `agents/Task-004.md` | Agent 任务 | M001 九件套按 CR-003 修订（→ v0.2.0） | **已完成（PM 复核 APPROVED + 用户批准 Frozen，2026-09-10）**（AGENT-M001） |
| `agents/Task-005.md` | Agent 任务 | M002 九件套按 CR-003 修订（→ v0.4.0） | **已完成（PM 复核 APPROVED + 用户批准 Frozen，2026-09-10）**（AGENT-M002） |
| `agents/Task-006.md` | Agent 任务 | 横切 AI 接入层 `app/core/ai/` 实现（Provider/prompt/schema 校验/降级/调用记录） | **已完成（PM 复核 APPROVED，2026-09-10；专属 39 例）**（AGENT-AI） |
| `agents/Task-007.md` | Agent 任务 | **M001 实施**：事实层按天 → `WindowResolver` → 聚合层 → 链路 T | **已完成（PM 复核 APPROVED，2026-09-10；含前端任务域）**（AGENT-M001） |
| `agents/Task-008.md` | Agent 任务 | **M002 实施**：入口 `kind` → N:N 挂接 → 逐张复核 → 窗口级门控 → 完成分析 | **已完成（PM 复核 APPROVED，2026-09-10；`Task-002` 冻结段增量改接收口）**（AGENT-M002） |
| `agents/Task-009.md` | Agent 任务 | **前端「作业」域迁移**：改名「作业」+ 周次/周末分组 + M002 v0.4.0 前端调用面 + 挂接复核改 `group_subject_id` + 门控/完成分析 UI | **已完成（PM 复核 APPROVED，2026-09-10）**（AGENT-M002；交付 8 文件含新增 `PhotoCard.vue`） |
| `agents/Task-010.md` | Agent 任务 | **门控链路缺陷修复（`BUG-002`）**：`GET /photo-gates` 按窗口分组 + `POST /completion-analyses` 门控前置生效（409 可达）+ `LinkReviewOut.gate` 正确 + 真机 M001↔M002 集成用例 | **已完成（PM 复核 APPROVED，2026-09-10；`BUG-002` → Verified；真机集成 4 例）**（AGENT-M002） |
| `agents/Task-011.md` | Agent 任务 | **阶段 ④ 验收**：`CLARIFICATION` §5 验收剧本 **7 条**（含浏览器级）+ 全系统回归（域 A/B/C；Mock 必跑 / 真实三方双跑）+ 只读边界（业务代码零改动，缺陷只登记不修复） | **已完成（PM 独立复核 2026-09-10：④ = 条件达成，不通过收口；§8 结论）**（AGENT-M002） |
| `agents/Task-012.md` | Agent 任务 | **`BUG-004` 修复（高）**：链路 T 经 `app/core/ai.parse_task_spec` 真跑（关键字传参 + `SourceInput` 转换）+ 降级可观测（`logger.warning`）+ `ai_call_records` 取证 | **已完成（PM 复核成立 = `Fixed`，2026-09-10；增补 §5D 归因更正 + 最小扩权 1 行裁决）**（AGENT-M001） |
| `agents/Task-013.md` | Agent 任务 | **`BUG-003` 修复（中）**：Mock 挂接建议读 key 对齐 `candidates` + 经 `AIService` 装配路径的防漂移用例 + 整改「直调 Mock + 手写 context」用例 | **已完成（PM 复核成立 = `Fixed`；含 `Task-013-D1` API 面补证，2026-09-10）**（AGENT-AI） |
| `agents/Task-014.md` | Agent 任务 | **④ 验收去替身复审**：移除 `m002_ai_port` 端口替身 + 边界 2 例走真实 AI 通路 + `TD-003` 垫片清理 + 剧本 4/5 真机复跑 + 浏览器级剧本 5 | **已完成（PM 复核成立，2026-09-10；去替身审计 10 条；`TD-003` → Closed）**（AGENT-M002） |
| `modules/M001/` | 模块九件套 | M001 作业任务管理 | **Stable v0.1.2**（CHANGE-001 Applied；API-M001-013~017 Active）；**契约 v0.2.0 —— Frozen（用户批准 2026-09-10）；③ 实施完成（Task-007，PM 复核 APPROVED）** |
| `modules/M002/` | 模块九件套 | M002 作业图片采集与归属 | **Stable（契约 v0.4.1 Frozen，`CR-004` Applied）**（③ 实施完成（`Task-008`，PM 复核 APPROVED）；**Task-002 增量改接收口**，PD-029；**前端「作业」域 = `Task-009` 已完成**；**门控链路缺陷 = `BUG-002` → Verified（`Task-010` 关闭）**；**④ 验收收口 = `Task-011` 取证 → `Task-012`/`Task-013` 修复 → `Task-014` 去替身复审经 PM 复核成立（`BUG-003` → Verified，2026-09-10）**） |
| `changes/CR-001.md` | 变更 | 任务=多学科作业登记单容器 + `group_no`（PD-014/015） | **Approved**（2026-09-08） |
| `changes/ACR-001.md` | 变更 | 两级主体认证（家长 + 学生子账号，ADR-009/PD-016） | **Approved**（2026-09-08） |
| `changes/CR-002.md` | 变更 | 内容级判定链数据面重构（布置登记识别/逐题判定/报告复核定稿） | **Approved**（2026-09-08，v0.9.0） |
| `changes/ACR-002.md` | 变更 | 判定与 Provider 架构重构（ADR-006/007 Superseded） | **Approved**（2026-09-08，v0.9.0） |
| `changes/CHANGE-001.md` | 变更执行 | CR-001/CR-002/ACR-001/ACR-002 合并执行（M001） | **已完成/Applied**（2026-09-08 PM 复核 APPROVED） |
| `changes/CHANGE-002.md` | 变更执行 | 前端技术栈切换（ADR-012：零构建 H5 → Vue3+Vite+TS+Vant 4） | **执行中（Executing）**（Task-003，2026-09-08） |

## ID 命名空间速查

| 前缀 | 含义 | 示例 | 权威规则 |
| --- | --- | --- | --- |
| `REQ-` | 需求 | `REQ-001` | `docs/requirements/REQ-001.md` |
| `M` | 模块 | `M001` | `docs/modules/M001/MODULE.md` |
| `API-Mxxx-nnn` | API | `API-M001-001` | `docs/modules/M001/MODULE_API.md` |
| `DATA-nnn` | 数据实体 | `DATA-001` | `docs/DATA_MODEL.md` |
| `ADR-nnn` | 架构决策 | `ADR-001` | `docs/adr/ADR-nnn.md` |
| `CR-nnn` | 变更请求 | `CR-001` | `docs/changes/CR-001.md` |
| `ACR-nnn` | 架构变更请求 | `ACR-001` | `docs/changes/ACR-001.md` |
| `CHANGE-nnn` | 重大变更 | `CHANGE-001` | `docs/changes/CHANGE-001.md` |
| `BUG-nnn` | Bug | `BUG-001` | `docs/changes/BUG-001.md` |
| `TD-nnn` | 技术债务 | `TD-001` | `docs/TECH_DEBT.md` |
| `RISK-nnn` | 风险 | `RISK-001` | `docs/RISK_REGISTER.md` |
| `ASM-nnn` | 假设 | `ASM-001` | `docs/ASSUMPTIONS.md` |
| `AGENT-nnn` | Agent | `AGENT-001` | `docs/AGENT_REGISTRY.md` |

分配权、格式与唯一性约束：见 `ID_GOVERNANCE.md`。

## 规划中的知识位置（首次使用时创建，勿提前造空模板）

| 路径 | 存放内容 | 触发时机 |
| --- | --- | --- |
| `docs/requirements/REQ-*.md` | 单个需求详情 | 已启用（REQ-001~010，新增需求时继续建） |
| `docs/domains/D0xx/` | 领域文档 | 系统规模扩大需要 Domain 层时 |
| `docs/modules/Mxxx/` | 模块九件套 | 已启用（M001 **Stable v0.1.2**（契约 **v0.2.0 Frozen**，③ 实施完成 = Task-007）；M002 **Stable**（契约 **v0.4.1 Frozen（`CR-004` Applied）**，③ 实施完成 = Task-008，前端作业域 = Task-009 已完成；门控链路修复 = Task-010 已完成（`BUG-002` Verified）；**④ 验收收口 = Task-014 去替身复审经 PM 复核成立（`BUG-003` Verified，2026-09-10）**）；**M003~M007 → Deferred（V1 不创建，ADR-014）**） |
| `docs/changes/` | CR/ACR/CHANGE/BUG 记录 | 已启用（CR-001/002、ACR-001/002 → **CHANGE-001 Applied**、**CHANGE-002 执行中**；**CR-003 Approved → CHANGE-003 执行中（② + ③ 后端/横切 + ③ 前端 + ③ 门控修复均已完成 = ③ 全部收口；④ 验收 = `Task-011` 已执行（PM 复核 = 条件达成，AI 通路缺陷修复后复审））**；**BUG-001 已修复**；**BUG-002 已 Verified（Task-010 修复并关闭）**；**CR-004 Applied（用户批准 2026-09-10；M002 契约 → v0.4.1）**；**`BUG-003`/`BUG-004` → Verified（`Task-012`/`Task-013` 修复 + `Task-014` 去替身复审，2026-09-10）**；**`CHANGE-003` → Closed（④ 判达成）**；**`TECH_DEBT.md` 启用（TD-001/TD-002；`TD-003` → Closed）**） |
| `docs/agents/` | Agent 任务单/过程记录 | 已启用（Task-002 已完成（随 Task-008 增量改接收口）/Task-003 Active；Task-004/Task-005 已完成（契约定稿）；**Task-006/Task-007/Task-008 已完成（PM 复核 APPROVED，2026-09-10）**；**Task-009 已完成（PM 复核 APPROVED，前端「作业」域迁移）**；**Task-010 已完成（门控链路修复 `BUG-002` → Verified）**；**Task-011 已完成（④ 条件达成，PM 复核）**；**`Task-012`（AGENT-M001）/ `Task-013`（AGENT-AI）/ `Task-014`（AGENT-M002）均已完成（PM 复核成立，2026-09-10；AI 通路缺陷修复 + 去替身复审）**） |
| `docs/TECH_DEBT.md` | 技术债务 | **已启用**（TD-001 `get_group_subject` 全量扫描 N+1；TD-002 契约未暴露 `window_task_id`/`task_status`；**TD-003 签名兼容垫片 → Closed（`Task-014` 清理，2026-09-10）**；PM 裁决不立 TD-004） |
| `docs/CONFIGURATION.md` | 配置项登记 | **已启用**（2026-09-10，CR-003 归属与窗口配置；评分权重 → **后置 V2**（ADR-014）；AI Provider 配置 → **已登记（§五 `AT_AI_*`，2026-09-10 随 Task-006 交付回填）**） |
| `docs/EXTERNAL_SYSTEMS.md` | 外部系统登记 | AI Provider 接入确认后 |
| `docs/DEPENDENCIES.md` | 第三方依赖登记 | 首个第三方依赖 |
| `docs/FEATURE_MATRIX.md` | 功能追踪矩阵 | V1 完成标准链路追踪需要时 |

## 快速查找

- 找模块 → `MODULE_REGISTRY.md`
- 找 API → `API_REGISTRY.md` → `MODULE_API.md`
- 找数据实体 → `DATA_MODEL.md`
- 找需求 → `REQUIREMENTS.md` → `requirements/REQ-xxx.md`
- 找决策原因 → `adr/`
- 找 Agent 职责 → `AGENT_REGISTRY.md`、`AGENT_GUIDE.md`
- 找变更记录 → `CHANGELOG.md` + `docs/changes/`
- 找风险 → `RISK_REGISTER.md`；当前阻塞 → `PROJECT_STATUS.md` 的 PD 列表
