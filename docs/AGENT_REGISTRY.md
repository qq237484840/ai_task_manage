# AGENT_REGISTRY —— Agent 登记表

> 维护：Project Master。新增/调整 Agent 职责、权限、任务时必须更新。
> 每个 Agent 遵守：**Read Scope / Write Scope / Review Scope**（读写审查三权限），禁止越权（见 `AGENT_GUIDE.md`）。
>
> 状态：**已启用**（2026-09-08 登记 V1 模块 Agent）。AGENT-M001 已签发 Task-001（契约 v0.1.1 Frozen）→ **Active**；AGENT-M002~007 保持 Planned，待前序模块验收后按序签发。

## Agent 登记表

| Agent ID | 名称 | 职责 | 关联模块 | Read Scope | Write Scope | 状态 | 当前任务 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `AGENT-001` | Project Master（总控） | 需求/架构/模块/接口/数据治理、Agent 分工、变更治理、知识体系、最终审核 | 全部 | 全部文档 | 治理层文档（docs 根、Registry、ADR、变更记录）；不直接代写模块业务代码 | Active | Phase 2：监督 M001 开发（Task-001）与 DoD 验收 |
| `AGENT-M001` | 作业任务管理 Agent | 模块内设计/编码/测试/文档；创建任务域 | M001 | PROJECT/ARCHITECTURE/M001/上游与依赖方 API | M001 | Active | Task-001：实现 M001（契约 v0.1.1 Frozen，按 `AGENT_GUIDE.md` §4/§6） |
| `AGENT-M002` | 作业图片采集 Agent | 上传/质检/预处理 | M002 | +M001 API | M002 | Planned | 同上 |
| `AGENT-M003` | AI 作业识别 Agent | OCR/Vision 识别与置信度 | M003 | +M002 API、AI Provider 契约 | M003 | Planned | 同上 |
| `AGENT-M004` | 作业任务匹配 Agent | 识别↔任务匹配 | M004 | +M001/M003 API | M004 | Planned | 同上 |
| `AGENT-M005` | AI 作业质量评价 Agent | 六维度评分/规则引擎 | M005 | +M001/M003/M004 API、评分权重配置 | M005 | Planned | 同上 |
| `AGENT-M006` | AI 教师评价 Agent | 评语与分级重写建议 | M006 | +M005 API、Prompt 资产 | M006 | Planned | 同上 |
| `AGENT-M007` | 今日报告 Agent | 聚合展示 | M007 | +M001/M002/M005/M006 API | M007 | Planned | 同上 |

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
| 模块任务单 | V1 需求确认后，PM 按开发顺序（M001→…→M007）签发任务单（Task ID/范围/验收） |

## 模块开发顺序（需求 §三）

`M001 → M002 → M003 → M004 → M005 → M006 → M007 → 全系统回归`
前一个模块未通过验收（PM `APPROVED`），不进入下一核心模块。
