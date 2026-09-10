# Task-002 任务书 —— M002 作业图片采集与归属（实现）

- **Task ID**：Task-002 ｜ **Agent**：AGENT-M002 ｜ **Module**：M002（作业图片采集与归属）
- **签发**：Project Master，2026-09-08 ｜ **状态**：**Active（部分冻结）**（2026-09-10 起，见下方处置决议）
- **前置**：CHANGE-001 **已完成/Applied**（M001 v0.1.2 Stable，2026-09-08 PM 复核 APPROVED）；M001 依赖侧接口已就绪
- **任务书登记**：`docs/AGENT_REGISTRY.md`（AGENT-M002 行）｜ 验收：**M002 模块级 DoD（本任务自含）**；域 **M-A 全量验收随链路 T/H 落地（M001 契约 v0.2.0 + M002 v0.4.0 + 横切 `app/core/ai/`；原 M003 职责）后统一执行**（2026-09-08 PM 审计 grill 定稿；2026-09-10 随 `ADR-014` 更新）
- **前端技术栈接轨注（2026-09-08，ADR-012/CHANGE-002/Task-003）**：本任务前端基础 UI 改为按**新前端栈**（Vue3 + Vite + TypeScript + Vant 4，`frontend/src`）实现；依赖 **Task-003（AGENT-M001）** 验收后接轨——Task-003 Active 期间 AGENT-M002 **不触碰 `frontend/`**，后端模块编码并行不受阻

## 处置决议（2026-09-10 · `CHANGE-003` §6 Q4 / `ADR-014` 决议 5 / PD-029）

> **决议：部分冻结 + 契约定稿后增量改接**（用户 2026-09-10 拍板；背景：本任务按 M002 契约 **v0.3.0** 编码「归属 = 学科作业段 1:N」，而 Task-005 将契约改为 **v0.4.0**「N:N 挂接 + 窗口级门控 + `completion_analyses`」）。

| 段 | 处置 | 依据 |
| --- | --- | --- |
| **归属 / 挂接段**（照片归属状态机、`photos.subject`/`group_no`、段级 1:N 约束、建议态承载、触发点） | **冻结**：不再按 v0.3.0 继续编码/扩展；已有实现保留待改接 | `CHANGE-003` §2.2 B1/B3/B5 |
| **与 CR-003 无关段**（上传批次、质检规则矩阵、轻量归一、受控存储与受控取图、双主体认证与越权、分页/上限 D5~D8） | **允许收尾**（可继续编码与测试） | 口径未被 CR-003 触及 |
| **改接方式** | Task-005 定稿（M002 v0.4.0）**且** `CHANGE-003` ② 评审 **APPROVED** 后，按 v0.4.0 **增量改接**（**返工面限于归属/挂接段**），由 PM 另签发实施任务 | Contract First（`DEVELOPMENT_GUIDE.md`） |
| **前端基础 UI 段** | 维持原注：按新栈实现、Task-003 验收后接轨；接轨时**直接对齐 v0.4.0 口径**（逐张复核 + 门控），不做 v0.3.0 界面 | ADR-012 / CHANGE-002 / B2/B5 |

**约束**：冻结期间不得以 v0.3.0 归属口径新增契约外能力；发现 v0.3.0 与 v0.4.0 冲突点 → 以 Request 报 PM，禁止自行扩缩契约。

## 1. Objective（目标）

按 M002 契约基线 **v0.3.0（Frozen，2026-09-08 用户批准）**实现作业图片采集与归属全部能力：上传批次组织、本地规则图片质检（不合格不入库 + 逐图报告）、轻量归一与受控存储、**先采后认**照片归属状态机（`unassigned→suggested→assigned/rejected`）、家长/学生双主体兜底 API、对 M001 `mark_in_progress` 的幂等推进，以及 **AI 挂接建议写入口**（`suggestion_json`/`consumed_at`）预留（建议由横切 `app/core/ai/` 生成、经 M002 链路 H 消费；原「`M003` 建议写端口」前向引用随 `ADR-014` 撤销，M003 → Deferred）。

## 2. Requirements（依据权威源，只读，禁止复制改写）

- **模块九件套（字段级/契约级权威源）**：`docs/modules/M002/MODULE_*.md`（MODULE/CONTRACT/API/DATA/DESIGN/FILES/SUMMARY/TEST/CHANGELOG）
- REQ-002（需求单）；决策 PD-010~016；ADR-009（两级主体）、ADR-011（真实三方默认，Mock 为测试桩）
- CHANGE-001 完成状态（M001 v0.1.2：学科作业段 `(subject,group_no)` 段级查询、family/student 双型认证、`AuthContext`、命名空间隔离防爆破均已落地）
- 现有共享基座：`backend/app/shared/`（auth 双主体/security/exceptions）、`backend/app/api/v1/deps.py`、`backend/app/core/config.py`（图片目录/阈值配置化入口）、M001 全部既有约定

## 3. Scope（范围）

### 3.1 本任务交付

| 交付 | 说明 |
| --- | --- |
| 后端 `modules/m002/` | 上传批次/照片实体与状态机、质检（QualityChecker 协议 + 本地规则 v1.0 + 阈值配置化）、归一、受控存储、归属 Repository/Service（含 M003 建议写入口与 `consumed_at` 置位/消费校验、未消费撤销）、首次 assigned 幂等触发 M001 `mark_in_progress` |
| REST API | `API-M002-001~006`（Frozen 契约断言实现；双主体：student 仅本人、family 可代传本家任一生） |
| 内部接口 | M002 服务接口供**链路 H 挂接链路**与后续消费者调用（照片证据供给、待处理队列、suggestion 写入口）——**AI 建议由横切 `app/core/ai/` 生成（Task-006），本任务只交付写侧与状态机** |
| 测试 | 新增 M002 用例（质检规则矩阵/状态机迁移/越权矩阵/存储与撤销/事务）+ 既有 **89 项 M001 测试不回归**，全部通过 |
| 前端基础 UI | `frontend/src`（**新栈：Vue3 + Vite + TS + Vant 4，Task-003 验收后接轨实现**）：照片上传（任务学科作业段选择 or 不预选混合上传）、逐图质检结果、照片列表与归属确认/驳回/撤销的最小可用页面（复用 M001 双主体登录与会话）；O-2/O-6 完整体验打磨可留后续前端任务 |
| 文档 | M002 九件套按落盘实况回填 + `MODULE_CHANGELOG.md` 记录 + `DATA_MODEL.md`（DATA-003 字段级）同步 |

### 3.2 Allowed-Files（可写）

- `backend/app/modules/m002/**`、`backend/app/api/v1/`（仅 M002 专属路由文件）、`backend/app/core/`（若需图片目录/质检阈值配置项，走 Request 最小化）
- `backend/tests/**`（新增 m002 用例，禁止破坏既有用例）
- `frontend/**`（M002 页面与复用组件）
- `docs/modules/M002/**`、`docs/DATA_MODEL.md`（仅 DATA-003 区段）

### 3.3 Forbidden-Files / 边界

- **禁止改动 M001 业务代码/表结构/既有 API 语义**（如需 M001 侧配合 → 以 Request 向 PM 提，不得直改）
- 禁止实现无契约接口 / 自行分配 API/DATA/Task ID（ID 治理 `ID_GOVERNANCE.md`）
- 禁止实现 AI 建议生成 / Provider 选型逻辑（归横切 `app/core/ai/`，Task-006）；Mock Provider 仅作测试桩
- 禁止修改其他模块九件套文档（M001 等）与治理层文档

## 4. Dependencies（已就绪，无需等待）

- M001 内部接口：`TaskQueryService.get_task_groups/get_task_group/can_accept_photo`（学科作业段归属校验）、`TaskStateService.mark_in_progress`（幂等，双主体 scope 已支持）
  - **注（2026-09-10，随 CR-003）**：上述查询接口基于 **v0.3.0「学科作业段」口径**；M002 契约改 v0.4.0（聚合子任务 N:N）后由**聚合层接口**取代 → 属「归属/挂接段」冻结范围，待改接时一并切换
- 认证：`shared/auth.py` `AuthContext`（family/student）、`api/v1/deps.py current_context`、登录爆破命名空间隔离
- 配置/存储：`core/config.py`（图片根目录、质检阈值、批次/数量上限 D5）、单机 SQLite + 本地图片目录（ASM-010）

## 5. Expected Deliverables（完成即提交 PM 复核）

- 代码按 §3.1 落地，lint 无错误；`.venv` 下 `pytest` 全绿（既有 89 + M002 新增）
- API-M002-001~006 契约断言（成功/失败/越权语义 400/401/403/404/409/413/415/422）
- 手工冒烟记录（含伪造不合格图 → 质检拒绝原因逐图、归属流转 assigned 后任务 in_progress）
- 前端基础 UI 冒烟记录（新栈实现，Task-003 验收后接轨）：复用 M001 双主体会话完成「上传 → 逐图质检报告 → 兜底归属（assign/reject）」的最小可用页面演示（Mock 模式；O-2/O-6 完整体验打磨留后续 UI 任务）
- M002 九件套回填 + MODULE_CHANGELOG + DATA_MODEL(DATA-003) 同步
- 完成后：提交 PM 按 **M002 模块 DoD 复核**（域 M-A 全量验收——布置登记解析 + 真实三方 AI 模式——随 **链路 T/H 与 `app/core/ai/`** 到位后统一执行）

## 6. Acceptance Criteria（DoD，AGENT_GUIDE §6）

- [ ] M002 契约 v0.3.0 条款全部在代码与文档落实（交叉核对）
- [ ] 不合格图片不入库（不留文件/行/状态）+ 逐图报告；轻量归一与受控存储符合 D2/D4
- [ ] 照片归属状态机 `unassigned→suggested→assigned/rejected` 全路径 + 撤销（未消费）；首次 assigned 同事务幂等推进 M001 `mark_in_progress`
- [ ] 两级主体：student 仅本人照片/上传；family 本家代传；越权对外 404/403 语义正确
- [ ] AI 挂接建议写入口（`suggestion_json`/`consumed_at`）与消费后不可变保障已实现（建议生成由 `app/core/ai/`（Task-006）提供；**归属/挂接段按上方处置决议冻结待 v0.4.0 改接**）
- [ ] 既有 89 项测试全绿 + M002 新增用例通过（backend/.venv 跑 pytest）
- [ ] M002 九件套回填（含 MODULE_CHANGELOG）并同步 DATA_MODEL/Registry 状态
- [ ] 前端基础 UI（新栈实现，Task-003 验收后接轨）最小可用页面演示通过（上传 → 逐图质检报告 → 兜底归属；完整体验 O-2/O-6 留后续，不属本 DoD）
- [ ] PM 按 **M002 模块 DoD** 复核 APPROVED → Task-002 关闭 → **M002 定稿 v0.3.0 Stable（维护态，循 M001 前例；复核发现缺陷 → 修复回路后再 APPROVED）**；域 **M-A 全量验收随链路 T/H + `app/core/ai/` 到位后执行**（原 M003 职责已并入 M001/M002，见 `ADR-014`）

> 注：M002 契约 v0.3.0 曾 Frozen；**2026-09-10 随 `CR-003` 打开冻结面**（改 v0.4.0，Task-005）→ 本任务 DoD 第 1 项以 **v0.3.0 条款**为准，但**归属/挂接段已冻结**（见上方处置决议），其 DoD 项按 v0.4.0 改接后复核。编码中出现契约未覆盖问题 → 先记 TD/以 Request 提交 PM，禁止自行扩大契约。

> **PM 审计批注（2026-09-08 grill 定稿，用户逐项确认）**：原 DoD「按 M-A 验收 → M002 转 Testing」修订为 **M002 模块级复核 → 直定稿 v0.3.0 Stable**——因域 M-A 全量（场景 1/2 布置单解析 + 真实三方 AI 模式）依赖当时未契约的 M003（**该职责 2026-09-10 起归 M001 链路 T + 横切 `app/core/ai/`，M003 → Deferred（`ADR-014`）**），Task-002 以 M002 模块 DoD + 前端基础 UI 冒烟独立收口；M002 依赖侧接口（`get_task_group`/`can_accept_photo`/`mark_in_progress`/`AuthContext`）经 PM 核查**全部已落地**。
