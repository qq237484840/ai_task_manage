# AGENT_REGISTRY —— Agent 登记表

> 维护：Project Master。新增/调整 Agent 职责、权限、任务时必须更新。
> 每个 Agent 遵守：**Read Scope / Write Scope / Review Scope**（读写审查三权限），禁止越权（见 `AGENT_GUIDE.md`）。
>
> 状态：**已启用**（2026-09-08 登记 V1 模块 Agent）。**M001 Stable v0.1.2**（Task-001 APPROVED + **CHANGE-001 Applied**：CR-001/CR-002/ACR-001/ACR-002 PM 复核 APPROVED，2026-09-08）；**M002 契约 v0.3.0 Frozen**（用户批准，Task-002 已签发）；**AGENT-M002 Active（Task-002）编码 M002 v0.3.0**（前端 UI 段待 Task-003 后按新栈接轨）；**AGENT-M001 Active（Task-003）执行前端技术栈切换（ADR-012/CHANGE-002）**；AGENT-M003~007 保持 Planned，按 ROADMAP 里程碑 M-A~M-D 依序推进。

## Agent 登记表

| Agent ID | 名称 | 职责 | 关联模块 | Read Scope | Write Scope | 状态 | 当前任务 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `AGENT-001` | Project Master（总控） | 需求/架构/模块/接口/数据治理、Agent 分工、变更治理、知识体系、最终审核 | 全部 | 全部文档 | 治理层文档（docs 根、Registry、ADR、变更记录）；不直接代写模块业务代码 | Active | **CHANGE-001 复核 APPROVED（2026-09-08）→ 收口 v0.11.0**（API-M001-013~017 登记、M001 定稿 v0.1.2）；**Task-002 签发**（AGENT-M002 编码 M002 v0.3.0）；**v0.12.0：ADR-012 前端技术栈切换确认（用户 Q1~Q3）+ CHANGE-002 立项 + Task-003 签发**（AGENT-M001）；监督 Task-003（前端切换 DoD）与 M002 编码（模块级 DoD），域 M-A 全量验收随 M003 统一执行 |
| `AGENT-M001` | 作业任务管理 Agent | 模块内设计/编码/测试/文档；创建任务域 | M001 | PROJECT/ARCHITECTURE/M001/上游与依赖方 API | M001 | Active | **Task-003（前端技术栈切换，ADR-012/CHANGE-002，2026-09-08 签发，任务书 `docs/agents/Task-003.md`）**：Vite+Vue3+TS+Vant 4 工程 + M001 页面等价迁移 + FastAPI 托管 `dist/`；任务期 `frontend/**` 独占写权；M002 后端联调支持不中断（Task-001/Task-CHG 已完成：M001 v0.1.2 Stable，89 测试全绿） |
| `AGENT-M002` | 作业图片采集与归属 Agent | 上传/质检/归一/受控存储/照片归属状态机（AI 建议 + 家长/学生兜底） | M002 | +M001 API（M001 v0.1.2 已就绪）、M003 建议写接口（契约轮） | M002 | **Active**（Task-002，2026-09-08 签发） | **Task-002（任务书 `docs/agents/Task-002.md`）**：实现 M002 v0.3.0（backend `modules/m002` + 图片存储链路 + tests + 九件套回填）；**前端基础 UI 段按新栈（Vue3+TS+Vant 4，ADR-012）在 Task-003 验收后接轨实现**（Task-003 期间不触碰 `frontend/`）；M001 依赖侧已就绪（`get_task_group`/`can_accept_photo`/双主体认证/`mark_in_progress`） |
| `AGENT-M003` | AI 作业识别 Agent | OCR/Vision 识别与置信度；**布置单识别（布置页→作业清单草稿）**；照片归属建议 | M003 | +M002 API、AI Provider 契约（ADR-011 真实三方） | M003 | Planned | 同 ROADMAP M-A/M-C 里程碑 |
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
| 模块任务单 | **Task-001/Task-CHG 已完成**（M001 Stable v0.1.2）；**Task-002 Active**（AGENT-M002 编码 M002 v0.3.0，前端段待 Task-003 后接轨）；**Task-003 Active**（AGENT-M001 前端技术栈切换，`docs/agents/Task-003.md`）；M003 起按 ROADMAP 里程碑 M-A~M-D 依序签发（Task ID/范围/验收见任务书） |

## 模块开发顺序（需求 §三）

`M001 → M002 → M003 → M004 → M005 → M006 → M007 → 全系统回归`
前一个模块未通过验收（PM `APPROVED`），不进入下一核心模块。
