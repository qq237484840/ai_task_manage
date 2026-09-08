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
| `ROADMAP.md` | L2 计划 | **V1 功能域主线（A~D 里程碑 + 验收 + 横切能力）** | **v0.9.0（2026-09-08，功能域主线重排）** |
| `SYSTEM_SUMMARY.md` | 系统摘要 | 几分钟理解整个系统 | V1 已填充 |
| `ARCHITECTURE.md` | L1 系统 | 总体/技术/部署/数据/安全架构 | V1 高层草案 |
| `REQUIREMENTS.md` | 需求 | 需求登记总表（权威源） | Approved（REQ-001~009，基线冻结 2026-09-08） |
| `MODULE_REGISTRY.md` | L3 模块 | 模块导航总表 | V1 已登记（M001~M007） |
| `API_REGISTRY.md` | L4 接口 | API 导航总表 | 启用（契约阶段登记） |
| `DATA_MODEL.md` | L5 数据 | 核心数据/所有权 | V1 实体草案 |
| `AGENT_REGISTRY.md` | Agent | Agent 分工与权限 | V1 已登记（含 AGENT-M001~M007） |
| `AGENT_GUIDE.md` | Agent | 模块 Agent 操作规范/交付物 | 已启用 |
| `DEVELOPMENT_GUIDE.md` | 治理 | 开发流程/变更治理/评审 | 已启用 |
| `ID_GOVERNANCE.md` | 治理 | ID 分配规则与唯一性约束 | 已启用 |
| `PROJECT_STATUS.md` | 状态 | 当前阶段/风险/待决 | **v0.10.0**（M002 v0.3.0 Frozen + Task-002；M001 合并 CHANGE 执行中） |
| `CHANGELOG.md` | 记录 | 变更历史 | **v0.10.0** |
| `ASSUMPTIONS.md` | 记录 | 假设登记 | ASM-001~011 |
| `RISK_REGISTER.md` | 记录 | 风险登记 | 已启用（RISK-001~009） |
| `requirements/REQ-001~009.md` | 需求 | 单条需求详情 | Approved（2026-09-08） |
| `adr/ADR-001.md` | ADR | 架构决策记录 | 已启用 |
| `adr/ADR-002.md` | ADR | V1 范围控制 | Accepted |
| `adr/ADR-003.md` | ADR | AI 评价边界与原则 | Accepted |
| `adr/ADR-004.md` | ADR | 技术栈：H5 + FastAPI + SQLite 单体（PD-003） | Accepted |
| `adr/ADR-005.md` | ADR | 纯家庭模式身份模型（PD-004） | Accepted |
| `adr/ADR-006.md` | ADR | 正确度分科混合判定（PD-005） | **Superseded（→ ADR-010，v0.9.0）** |
| `adr/ADR-007.md` | ADR | AI Provider 抽象 + Mock 先行（PD-006） | **Superseded（→ ADR-011，v0.9.0）** |
| `adr/ADR-008.md` | ADR | 学校基础字典=全局共享只读（REQ-009/DATA-011，ADR-005 限定例外） | Accepted |
| `adr/ADR-009.md` | ADR | 两级主体身份：家庭账号家长 + 学生子账号（PD-016） | Accepted（落地随 ACR-001） |
| `adr/ADR-010.md` | ADR | 内容级主客观全判 + 端到端直判（PD-018/021/022，取代 ADR-006） | **Accepted**（2026-09-08 随 ACR-002） |
| `adr/ADR-011.md` | ADR | AI Provider 真实三方默认，Mock 降级（PD-019，取代 ADR-007） | **Accepted**（2026-09-08 随 ACR-002） |
| `modules/M001/` | 模块九件套 | M001 作业任务管理 | **Stable**（契约 v0.1.1 Frozen + DoD 验收 APPROVED；合并 CHANGE 执行中——CR-001/CR-002/ACR-001/ACR-002） |
| `modules/M002/` | 模块九件套 | M002 作业图片采集 | **Developing**（契约 **v0.3.0 Frozen**，2026-09-08 用户批准；Task-002 编码中） |
| `changes/CR-001.md` | 变更 | 任务=多学科作业登记单容器 + `group_no`（PD-014/015） | **Approved**（2026-09-08） |
| `changes/ACR-001.md` | 变更 | 两级主体认证（家长 + 学生子账号，ADR-009/PD-016） | **Approved**（2026-09-08） |
| `changes/CR-002.md` | 变更 | 内容级判定链数据面重构（布置登记识别/逐题判定/报告复核定稿） | **Approved**（2026-09-08，v0.9.0） |
| `changes/ACR-002.md` | 变更 | 判定与 Provider 架构重构（ADR-006/007 Superseded） | **Approved**（2026-09-08，v0.9.0） |

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
| `docs/requirements/REQ-*.md` | 单个需求详情 | 已启用（REQ-001~008，新增需求时继续建） |
| `docs/domains/D0xx/` | 领域文档 | 系统规模扩大需要 Domain 层时 |
| `docs/modules/Mxxx/` | 模块九件套 | 已启用（M001 Stable + 变更执行中；M002 Developing/Frozen v0.3.0；M003 起按顺序创建，前序验收后） |
| `docs/changes/` | CR/ACR/CHANGE/BUG 记录 | 已启用（CR-001/002、ACR-001/002 均 Approved） |
| `docs/agents/` | Agent 任务单/过程记录 | 首个模块 Agent 任务 |
| `docs/TECH_DEBT.md` | 技术债务 | 首个债务记录 |
| `docs/CONFIGURATION.md` | 配置项登记 | 首个配置项（含评分权重、Provider 配置） |
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
