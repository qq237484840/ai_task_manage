# CHANGELOG —— 项目变更历史

> 维护：Project Master。语义化版本（主.次.修订）。
> 模块级变更进入各模块 `MODULE_CHANGELOG.md`；重大变更（CHANGE-nnn）另存 `docs/changes/`。

## v0.5.0 —— 2026-09-08

### 变更 / 决策

- **用户批准 M001 契约草案 v0.1.1**（签署区 `docs/modules/M001/MODULE_CONTRACT.md`）→ Contract/API/Data 基线 **Frozen**；M001 模块状态 Designing → Developing；API-M001-001~012 状态 Draft → Frozen（修改须走 CR）
- 向 **AGENT-M001** 签发 **Task-001**（实现 M001：backend/frontend 工程骨架 + 功能实现 + 测试 + 回填九件套实现版）→ Active；AGENT-M002~007 保持 Planned（前序验收后按序签发）

### 更新

- `docs/modules/M001/` 九件套状态/签署区同步（Frozen / Developing）；`MODULE_REGISTRY.md`、`API_REGISTRY.md`、`AGENT_REGISTRY.md`、`PROJECT_STATUS.md`（→ v0.5.0）

## v0.4.1 —— 2026-09-08

### 变更 / 决策

- M001 开发输入增补**学校基础资料**（用户确认四项：全局共享字典 + 数据库 seed 预置 + 后台维护暂缓；学生档案必填关联；字段 = 名称+学段；消费限 M001）→ 新增 **REQ-009**（Approved）、**ADR-008**（Accepted）、**DATA-011**（`schools` 全局只读字典）
- M001 契约草案 v0.1.0 → **v0.1.1**：`students.school` 自由文本 → `school_id` 必填（FK→schools）；新增 API-M001-012（GET /schools 只读列表）；schools 初始化 seed 幂等，运行期无维护 API

### 更新

- 新增：`docs/adr/ADR-008.md`、`docs/requirements/REQ-009.md`
- `docs/modules/M001/` 九件套同步 v0.1.1；`DATA_MODEL.md`（DATA-011 + ownership 例外）；`REQUIREMENTS.md`（REQ-009 登记、REQ 状态列修正 Draft→Approved）；`MODULE_REGISTRY.md`、`API_REGISTRY.md`（API-M001-012）
- `PROJECT_STATUS.md` → v0.4.1（PD-009 登记）；`PROJECT.md` / `ADR-005.md` 措辞澄清：学校管理域禁止不变，"学校基础字典"（ADR-008）为限定例外

## v0.4.0 —— 2026-09-08

### 决策

- PD-007/008 经用户复核确认：**ASM-010/011 → Confirmed**（单机/局域网 + SQLite + 本地图片目录；小学语数英书面作业起步 + "无法判断"→ 标记 + 家长复核/重拍）
- **REQ-001~008 → Approved**：V1 需求基线冻结
- 进入 **Phase 2 模块契约设计**：M001（作业任务管理）九件套契约草案产出

### 更新

- `PROJECT_STATUS.md` → v0.4.0（PD 表全部 Confirmed；M001 → Designing）；`ASSUMPTIONS.md`（ASM-010/011 Confirmed）；`MODULE_REGISTRY.md`（M001 Designing）；`REQUIREMENTS.md` + REQ-001~008（Approved）
- 新增：`docs/modules/M001/`（模块文档九件套，契约草案）

## v0.3.0 —— 2026-09-08

### 决策

- 用户确认关键设计决策（PD）并落库 ADR：
  - PD-003 → **ADR-004**：移动优先 H5 + Python FastAPI + SQLite 单体
  - PD-004 → **ADR-005**：纯家庭模式身份模型（家庭账号 + 学生档案，家庭级数据隔离）
  - PD-005 → **ADR-006**：正确度分科混合判定（客观题对照参考答案 / 主观题不判对错并注明）
  - PD-006 → **ADR-007**：AI Provider 抽象 + Mock 先行（本地无 key 跑通全链路）
- 新增默认假设 **ASM-010**（PD-007：单机部署 + SQLite + 本地图片目录）、**ASM-011**（PD-008：小学语数英书面作业起步、无法判断→标记+复核/重拍），状态 Open 待用户复核

### 更新

- `ARCHITECTURE.md` / `SYSTEM_SUMMARY.md`：技术架构、部署、数据、身份、业务流用语按 ADR-004~007 同步
- `DATA_MODEL.md`：存储选型定为 SQLite + 本地图片目录；DATA-002 收敛为家庭账号 + 学生档案（Owner M001）
- `ASSUMPTIONS.md`：ASM-007/008 转 Confirmed，新增 ASM-010/011
- `PROJECT_STATUS.md`：PD-003~006 → Confirmed；版本推进至 v0.3.0

## v0.2.0 —— 2026-09-08

### 新增

- 纳入 V1 MVP 需求（用户「V1 MVP 总控 Agent 指令」，AI 每日作业智能评定系统）：
  - `docs/REQUIREMENTS.md` 登记 REQ-001~008（Draft）；新增 `docs/requirements/REQ-001~008.md` 需求单
  - `docs/MODULE_REGISTRY.md` 登记 M001~M007（需求 M01~M07 别名映射）
  - `docs/AGENT_REGISTRY.md` 登记 AGENT-M001~M007
  - `docs/DATA_MODEL.md` 登记 DATA-001~010 核心实体草案
  - `docs/API_REGISTRY.md` 状态更新（契约阶段逐模块登记）
  - `docs/RISK_REGISTER.md` 创建（RISK-001~004）
  - `docs/PROJECT.md` / `docs/SYSTEM_SUMMARY.md` / `docs/ARCHITECTURE.md` 由骨架填充为 V1 内容

### 决策

- ADR-002：V1 范围控制（仅 7 模块闭环，禁止提前开发未来功能）
- ADR-003：AI 评价边界与原则（可观察行为/配置化权重/分级重写/允许"无法判断"）
- 模块 ID 映射：需求 `M01~M07` ↔ 正式 `M001~M007`
- 待决决策 PD-003~008 等用户确认（见 `PROJECT_STATUS.md`）

## v0.1.0 —— 2026-09-08

### 新增

- 建立文档治理骨架（文档驱动 + 总控 Agent 多 Agent 协作模式），并沉淀治理模板包 `ai-governance-template/`
