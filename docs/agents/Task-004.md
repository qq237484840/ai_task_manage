# Task-004 任务书 —— M001 契约（九件套）按 CR-003 修订评审

- **Task ID**：Task-004 ｜ **Agent**：AGENT-M001 ｜ **Kind**：契约修订（**契约修订评审，不含编码实施**）
- **签发**：Project Master，2026-09-10 ｜ **状态**：**已交付 → PM 复核 APPROVED（2026-09-10）**（交付物 = M001 九件套 v0.2.0 草案 + API ID 申请清单 + A1~A11 对照 + 破坏性变更/开放项，见 `MODULE_CHANGELOG.md`）
- **前置**：`CR-003` **Approved**（2026-09-10 用户逐条确认）+ `ADR-013` **Accepted** + `REQ-010` **Approved**；本任务授权**打开 M001 Stable v0.1.2 冻结面**（仅契约文档层）
- **任务书登记**：`docs/AGENT_REGISTRY.md`（AGENT-M001 行）｜ **验收**：本任务书 §5 DoD（PM 复核）

## 1. Objective

按 `CR-003` / `ADR-013` / `REQ-010` 修订 **M001 九件套契约**，使 M001 的契约层与「**按天事实层 + 跨天聚合层**」新语义一致，供后续实施阶段（Task-006+）直接依据。**本任务只改契约与模块文档，不写业务代码。**

## 2. Requirements（依据权威源，只读，禁止复制改写）

- **权威源**：`docs/requirements/CLARIFICATION-2026-09-10.md`（冲突时以其为准）
- **变更登记**：`docs/changes/CR-003.md`（Approved）、`docs/changes/CHANGE-003.md`（执行授权 + **§2.1 契约修订要点清单 A1~A11**）
- **需求**：`docs/requirements/REQ-010.md`（Approved）、`REQ-001`（已精校）
- **架构**：`docs/adr/ADR-013.md`（双层模型）、`docs/adr/ADR-010.md`（判定粒度 Superseded）
- **数据**：`docs/DATA_MODEL.md`（DATA-001/014/015 及 DATA-012/013 关联）
- **配置**：`docs/CONFIGURATION.md`（`AT_TIMEZONE`/`AT_TERM_START`/`AT_TERM_END`/`AT_DAY_CUTOFF` 与生效锁定规则）

## 3. Scope

### 3.1 本任务交付（= `CHANGE-003` §2.1 清单 A1~A11）

| # | 交付 |
| --- | --- |
| 1 | `MODULE_DATA.md`：`tasks` 字段与唯一键修订；`task_items` 标 Deprecated；新增 `task_contents`/`task_spec_sources`/`task_groups`/`task_group_subjects` |
| 2 | `MODULE_CONTRACT.md`：任务创建流程（输入源 → AI 解析草稿 → 确认 / 隐式确认）、`spec_status` 状态机、**配置锁定语义**、**手工改归属日连锁规则** |
| 3 | `MODULE_DESIGN.md`：归属引擎 `WindowResolver`（策略接口）+ 聚合生成与 `policy_version` 锁定设计 |
| 4 | `MODULE_API.md`（草案）：新增/调整端点定义（**API ID 留空，由 PM 分配**） |
| 5 | `MODULE_TEST.md`：既有 89 基线 + 新增用例设计（归属边界 4 点、周次起算、周末聚合、唯一键冲突、配置锁定按学生隔离） |
| 6 | `MODULE.md` / `MODULE_SUMMARY.md` / `MODULE_FILES.md` / `MODULE_CHANGELOG.md`：按新契约更新，`MODULE_CHANGELOG` 记录本 CHANGE |
| 7 | **契约版本**：v0.1.2 → **v0.2.0（草案，待 PM 评审）** |

### 3.2 Allowed-Files（可写）

- `docs/modules/M001/**`（本任务唯一写区）

### 3.3 Forbidden-Files / 边界

- **禁止写业务代码**（`backend/**`、`frontend/**`）——实施阶段另签任务
- **禁止自行分配任何 ID**（API / DATA / CR / CHANGE / Task；`ID_GOVERNANCE.md` §总则 1）
- **禁止改动治理层文档**：`REQUIREMENTS.md` / `DATA_MODEL.md` / `INDEX.md` / `ROADMAP.md` / `PROJECT_STATUS.md` / `MODULE_REGISTRY.md` / `API_REGISTRY.md` / `AGENT_*` / `CONFIGURATION.md`（由 PM 同步；如需变更以 **Request** 提交）
- 禁止修改 M002 契约与本 CHANGE 清单；禁止扩大/缩小 `CHANGE-003` §2.1 范围

## 4. Dependencies / 环境

- 只读参考：M001 现行九件套（v0.1.2）、`backend/app/modules/m001/`（了解现状实现，**不得修改**）、`backend/tests/`（89 基线）
- **边界提示（已解除，2026-09-10）**：`CHANGE-003` §6 的 **Q1/Q2/Q3 已决议关闭**（`ADR-014`）——**M003/M004 职责并入 M001/M002**、**`REQ-005`~`REQ-007` 后置 V2**、横切 `app/core/ai/` = `AGENT-AI`。本任务范围内**不应再出现 M003~M007 边界或六维/评语/报告归属的待确认表述**；如发现，直接按 `ADR-014` 口径书写，**不自行引入新边界判定**

## 5. Acceptance Criteria（DoD）

- [ ] `CHANGE-003` §2.1 清单 **A1~A11 逐项落实**（可交叉核对，无遗漏、无越界）
- [ ] 九件套齐备且语义自洽：与 `CLARIFICATION` / `REQ-010` / `ADR-013` / `DATA_MODEL` 逐条一致，无残留「登记单容器 / 学科作业段 `group_no` / 逐题判定」旧语义
- [ ] 契约要素完整（`AGENT_GUIDE.md` §6）：请求 / 响应 / 错误 / 鉴权 / 幂等 / 事务 / 副作用 / 兼容性
- [ ] API ID **留空待分配**并列出「申请分配清单」（名称 + 方法/路径 + 用途）
- [ ] 新增用例设计可验证「配置锁定按学生隔离」（验收剧本第 3 条）
- [ ] 开放项（Q1/Q2/Q3 相关）显式登记，无隐藏假设
- [ ] 零写越界：`git status` 改动面仅 `docs/modules/M001/**`

## 6. Expected Deliverables（完成即提交 PM 复核）

1. M001 九件套修订稿（v0.2.0 草案）
2. 「API ID 申请分配清单」（供 PM 登记 `API_REGISTRY.md`）
3. 变更说明：逐条对应 A1~A11 + 与旧契约的差异点（破坏性变更清单）
4. 开放项清单（含待 Q1/Q2/Q3 确认的挂起项）

## 7. PM 批注（2026-09-10，签发）

本任务为 `CR-003` 处理路径的**第 ② 步（契约修订评审）**。**实施（第 ③ 步）不得在本任务 PM 复核 APPROVED 前启动**（Contract First）。若执行中发现 `CHANGE-003` §2.1 清单与 `CLARIFICATION` 权威源冲突 → **以权威源为准**并以 Request 报 PM，禁止自行取舍。

## 8. PM 复核结论（2026-09-10，关闭）

- **复核结果 = APPROVED**。A1~A11 逐项落实、九件套语义与 `CLARIFICATION` / `REQ-010` / `ADR-013` / `ADR-014` / `DATA_MODEL` 一致；无残留「多学科登记单容器 / 学科作业段 `group_no` / 逐题判定」旧语义；配置锁定按学生隔离用例可验证；零写越界（写区仅 `docs/modules/M001/**`）。
- **API ID 已由 PM 分配并登记** `API_REGISTRY.md`：`API-M001-018`（解析结果确认）/ `019`（聚合任务列表）/ `020`（聚合任务详情）/ `021`（手工改归属日）（状态 Draft，随 ③ 实施转 Active；任务输入源上传 = 修订既有 `API-M001-007`，不新增 ID）。
- **`DATA_MODEL.md` DATA-001 字段级已由 PM 同步**（新增列 / 唯一键 / `task_items` Deprecated；DATA-012~015 登记）。
- **开放项处置**：Q1/Q2/Q3 边界挂起项随 `ADR-014` 闭合；契约 **已于 2026-09-10 由用户批准 → Frozen**（签署区落款）；③ 实施 = **`Task-007`**（同日签发）。
- **后续**：本任务关闭；③ 实施（含 `Task-006` 横切 AI 层）可启动（Contract First：② 已 APPROVED）。
