# AI.TaskManage —— 中小学生 AI 作业与学习成长综合评定系统

> 当前阶段：**V1 MVP（AI 每日作业智能评定系统）需求已文档化，待需求确认后进入开发**。
> 采用 **文档驱动 + 多 Agent 协作** 的软件工程治理模式：人负责决策，Project Master 负责治理，模块 Agent 负责实现，Contract 负责协作，Documentation 负责记忆，Registry 负责导航，Tests 负责验证，Git 负责版本。

## V1 核心闭环

```text
创建作业任务 → 上传作业照片 → AI 识别 → 任务匹配 → 质量评价 → AI 教师评价 → 今日综合报告
```

## 文档入口

| 目的 | 位置 |
| --- | --- |
| 知识地图（一切从这里开始） | `docs/INDEX.md` |
| 项目全貌（L0） | `docs/PROJECT.md` |
| 需求登记（REQ-001~008） | `docs/REQUIREMENTS.md` |
| 模块登记（M001~M007） | `docs/MODULE_REGISTRY.md` |
| 当前状态与待决决策 | `docs/PROJECT_STATUS.md` |
| 架构（L1） | `docs/ARCHITECTURE.md` |
| 数据模型（L5） | `docs/DATA_MODEL.md` |
| Agent 分工与权限 | `docs/AGENT_REGISTRY.md`、`docs/AGENT_GUIDE.md` |
| 开发流程与变更治理 | `docs/DEVELOPMENT_GUIDE.md` |
| 风险登记 | `docs/RISK_REGISTER.md` |

## 治理原则（摘要）

架构、模块、接口、数据、方法等知识一律进入 `docs/` 分层文档维护，本 README 仅作入口，不承载业务知识，避免知识重复。V1 范围控制与 AI 评价原则见 ADR-002/003。

## 治理模板包（复用资产）

本仓库同时维护 **可复用治理模板** `ai-governance-template/`：由本仓库 `docs/` 体系通用化而来，新项目可直接铺装（复制 `docs/` + 按 `INSTALL.md` 替换占位符）。模板是复用资产，不参与本项目知识分层，勿混入业务内容。
