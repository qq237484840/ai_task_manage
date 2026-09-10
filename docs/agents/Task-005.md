# Task-005 任务书 —— M002 契约（九件套）按 CR-003 修订评审

- **Task ID**：Task-005 ｜ **Agent**：AGENT-M002 ｜ **Kind**：契约修订（**契约修订评审，不含编码实施**）
- **签发**：Project Master，2026-09-10 ｜ **状态**：**已交付 → PM 复核 APPROVED（2026-09-10）**（交付物 = M002 九件套 v0.4.0 草案 + API ID 申请清单 + B1~B10 对照 + 破坏性变更/开放项，见 `MODULE_CHANGELOG.md`）
- **前置**：`CR-003` **Approved**（2026-09-10）+ `ADR-013` **Accepted** + `REQ-010` **Approved**；本任务修订 M002 **v0.3.0（Frozen）** 契约为 **v0.4.0 草案**
- **任务书登记**：`docs/AGENT_REGISTRY.md`（AGENT-M002 行）｜ **验收**：本任务书 §5 DoD（PM 复核）

## 1. Objective

按 `CR-003` / `ADR-013` / `REQ-010` 修订 **M002 九件套契约**：上传入口分「任务 / 作业」、作业上传不填内容、归属由**段级 1:N** 放开为**照片 ↔ 聚合子任务 N:N**、新增挂接复核分析与**窗口级门控**。**本任务只改契约与模块文档，不写业务代码。**

## 2. Requirements（依据权威源，只读，禁止复制改写）

- **权威源**：`docs/requirements/CLARIFICATION-2026-09-10.md`（冲突时以其为准）
- **变更登记**：`docs/changes/CR-003.md`（Approved）、`docs/changes/CHANGE-003.md`（执行授权 + **§2.2 契约修订要点清单 B1~B10**）
- **需求**：`docs/requirements/REQ-010.md`（Approved）、`REQ-002`（已精校）
- **架构**：`docs/adr/ADR-013.md`（双层模型）、`docs/CONFIGURATION.md`（归属日边界与锁定规则）
- **数据**：`docs/DATA_MODEL.md`（DATA-003 修订；DATA-012/013/016/017）
- **上游契约**：M001 修订稿（**Task-004 并行，依赖 `belongs` 上下文由 PM 提供；未就绪处标注挂起**）

## 3. Scope

### 3.1 本任务交付（= `CHANGE-003` §2.2 清单 B1~B10）

| # | 交付 |
| --- | --- |
| 1 | `MODULE_DATA.md`：`photos.kind` 新增；`subject`/`group_no` 标 Deprecated；`task_id` 降为窗口级；新增 `photo_subject_links`（**N:N**）/`completion_analyses` |
| 2 | `MODULE_CONTRACT.md`：上传入口分「任务/作业」、**作业上传不填内容**、挂接 → 逐张复核 → **窗口级门控** → 完成分析 → 确认的状态机；降级手工路径**必须保留** |
| 3 | `MODULE_DESIGN.md`：异步挂接触发（幂等）、N:N 挂接设计、跨聚合迁移同步挂接目标、`app/core/ai/` 对接边界 |
| 4 | `MODULE_API.md`（草案）：新增/调整端点（提交 / 挂接建议 / 逐张复核 / 门控查询 / 完成分析确认）（**API ID 留空，由 PM 分配**） |
| 5 | `MODULE_TEST.md`：既有 **112** 基线 + 新增用例（N:N 挂接、门控不提前触发、LLM 降级手工路径、跨聚合迁移无悬挂引用） |
| 6 | `MODULE.md` / `MODULE_SUMMARY.md` / `MODULE_FILES.md` / `MODULE_CHANGELOG.md`：更新并记录本 CHANGE |
| 7 | **漂移清理**：`photos.suggestion_json` 注释中的「**M003 建议快照**」表述（现状仅 `m001`/`m002`）——**代码注释部分已由 PM 预清理**（2026-09-10，14 处注释、零逻辑改动、pytest 112 全绿）；本任务只需完成 `MODULE_DATA.md` 侧表述对齐与复核 |
| 8 | **契约版本**：v0.3.0 → **v0.4.0（草案，待 PM 评审）** |

### 3.2 Allowed-Files（可写）

- `docs/modules/M002/**`（本任务唯一写区）
- `backend/app/modules/m002/` 中**仅限注释**的漂移清理（`suggestion_json` 的 M003 表述）——**不得改动任何逻辑**

### 3.3 Forbidden-Files / 边界

- **禁止写业务逻辑代码**（实施阶段另签任务）
- **禁止自行分配任何 ID**（`ID_GOVERNANCE.md` §总则 1）
- **禁止改动治理层文档**与 M001 契约（由 PM / Task-004 负责；如需变更以 **Request** 提交）
- **禁止触碰 `frontend/**`**（前端接轨按 Task-003 批注与后续任务安排）

## 4. Dependencies / 环境

- 只读参考：M002 现行九件套（v0.3.0 Frozen）、`backend/app/modules/m002/`（**只读**，仅注释清理例外）、`backend/tests/`（112 基线）
- **边界提示（已解除，2026-09-10）**：`CHANGE-003` §6 的 **Q1/Q2/Q3/Q4 已决议关闭**（`ADR-014`）——M003/M004 职责并入 M001（链路 T）/ M002（链路 H）、`REQ-005`~`REQ-007` 后置 V2、横切 `app/core/ai/` = `AGENT-AI`（Task-006）、Task-002 部分冻结。本任务范围内**不应再出现 M003/M004 接口边界或六维/评语/报告的待确认表述**；如发现，直接按 `ADR-014` 口径书写，**不自行引入新边界判定**

## 5. Acceptance Criteria（DoD）

- [ ] `CHANGE-003` §2.2 清单 **B1~B10 逐项落实**（可交叉核对，无遗漏、无越界）
- [ ] 九件套语义自洽：与 `CLARIFICATION` / `REQ-010` / `ADR-013` / `DATA_MODEL` 一致，**无残留「归属到学科作业段 1:N」旧语义**
- [ ] **N:N 挂接**与**窗口级门控**在契约中可验证（含「存在未确认挂接 → 不触发完成分析」的判定条件）
- [ ] 契约要素完整（请求 / 响应 / 错误 / 鉴权 / 幂等 / 事务 / 副作用 / 兼容性）
- [ ] API ID **留空待分配**并列出「申请分配清单」（名称 + 方法/路径 + 用途）
- [ ] `photos.suggestion_json` 的「M003」漂移：**代码注释已由 PM 预清理**（仅注释、零逻辑改动、pytest 112 全绿）；本任务复核并在 `MODULE_DATA.md` 对齐表述
- [ ] 零写越界：改动面仅 `docs/modules/M002/**` + 注释清理

## 6. Expected Deliverables（完成即提交 PM 复核）

1. M002 九件套修订稿（v0.4.0 草案）
2. 「API ID 申请分配清单」（供 PM 登记 `API_REGISTRY.md`）
3. 变更说明：逐条对应 B1~B10 + 破坏性变更清单（对照 v0.3.0）
4. 开放项清单（含待 Q1/Q2/Q3 确认的挂起项）

## 7. PM 批注（2026-09-10，签发）

M002 契约 v0.3.0 系 2026-09-08 用户批准的 Frozen 基线，本次属**破坏性语义修订**，故必须走 `CR-003` + 本任务书显式授权。Task-005 与 Task-004 **并行**，但若 M001 修订稿（`belongs` 上下文 / 聚合层契约）尚未就绪，**相关处先标注挂起**，待 M001 复核通过后补齐，禁止自行定义 M001 侧契约。

## 8. PM 复核结论（2026-09-10，关闭）

- **复核结果 = APPROVED**。B1~B10 逐项落实、九件套语义与 `CLARIFICATION` / `REQ-002` / `REQ-010` / `ADR-013` / `ADR-014` / `DATA_MODEL` 一致；无残留「段级 1:N 归属」旧语义；N:N 挂接与窗口级门控可验证；零写越界（写区 = `docs/modules/M002/**` + 注释清理）。
- **API ID 已由 PM 分配并登记** `API_REGISTRY.md`：`API-M002-007`（挂接建议查询/重试）/ `008`（门控状态）/ `009`（完成分析生成）/ `010`（完成分析确认）/ `011`（完成分析重跑）（状态 Draft，随 ③ 实施转 Active）。
- **`DATA_MODEL.md` DATA-003 字段级已由 PM 同步**（`kind` / `task_id` 降窗口级 / Deprecated 列；DATA-016/017 登记）。
- **开放项处置**：M003/M004 边界（原开放项 4）随 `ADR-014` 闭合；契约 **已于 2026-09-10 由用户批准 → Frozen**（签署区落款）；③ 实施 = **`Task-008`**（同日签发，Task-002 冻结段增量改接）。
- **后续**：本任务关闭；③ 实施（含 `Task-006` 横切 AI 层）可启动（Contract First：② 已 APPROVED）。
