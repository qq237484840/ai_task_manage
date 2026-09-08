# ID_GOVERNANCE —— ID 分配规则与唯一性约束（权威源）

> 目的：让所有文档可被稳定引用、可追踪、无歧义。
> 本文件是「ID 前缀 / 格式 / 分配权 / 状态机」的唯一权威来源；其他文档引用本规则，不重复定义。
>
> 状态：已启用（规范先行）。暂不引入自动校验脚本；当 ID 数量增长后，由 Project Master 评估是否增加校验工具（可在 `TECH_DEBT.md` 预留建议）。

## 总则

1. **分配权**：所有 ID（REQ / M / API / DATA / ADR / CR / ACR / CHANGE / BUG / TD / RISK / ASM / AGENT）均由 **Project Master 分配**，Agent 不得自行编号。
2. **唯一性**：同一命名空间内 ID 全局唯一，永不重复使用（被废弃的 ID 保留并标记状态）。
3. **稳定性**：ID 一经分配，不随意修改/复用。
4. **引用语法**：文档内引用一律写全 ID（如 `API-M001-003`），并给出目标链接；**禁止复制定义内容**（引用指向权威源，避免漂移）。
5. **一致性**：`代码 ≠ 文档` 或 `引用断裂 / ID 重复` 属于优先级最高的待处理问题（见 `DEVELOPMENT_GUIDE.md`）。

## ID 命名空间

| 命名空间 | 格式 | 连续编号域 | 分配时机 | 状态机 | 登记位置 |
| --- | --- | --- | --- | --- | --- |
| 需求 | `REQ-nnn` | 全局 | 需求录入 | Draft/Approved/In Progress/Done/Deprecated | `REQUIREMENTS.md` + `requirements/REQ-nnn.md` |
| 模块 | `Mnnn` | 全局 | 模块划分 | Planned/…/Stable/Deprecated/Archived | `MODULE_REGISTRY.md` |
| API | `API-Mnnn-nnn` | 模块内 | 接口设计 | Draft/Active/Frozen/Deprecated/Removed | `API_REGISTRY.md` + 模块 `MODULE_API.md` |
| 数据实体 | `DATA-nnn` | 全局 | 数据设计 | 草案/定稿 | `DATA_MODEL.md` |
| 架构决策 | `ADR-nnn` | 全局 | 决策定稿 | Proposed/Accepted/Superseded | `adr/ADR-nnn.md` |
| 变更请求 | `CR-nnn` | 全局 | 变更提出 | Open/Approved/Rejected/Done | `changes/CR-nnn.md` |
| 架构变更请求 | `ACR-nnn` | 全局 | 架构问题 | Open/Approved/Rejected/Done | `changes/ACR-nnn.md` |
| 重大变更 | `CHANGE-nnn` | 全局 | 重大变更执行 | 规划/执行中/已完成/已回滚 | `changes/CHANGE-nnn.md` |
| Bug | `BUG-nnn` | 全局 | Bug 发现 | 待修/修复中/已验证 | `changes/BUG-nnn.md` |
| 技术债务 | `TD-nnn` | 全局 | 债务识别 | Open/In Progress/Resolved | `TECH_DEBT.md` |
| 风险 | `RISK-nnn` | 全局 | 风险识别 | Open/Mitigating/Closed | `RISK_REGISTER.md` |
| 假设 | `ASM-nnn` | 全局 | 假设产生 | Open/Confirmed/Rejected | `ASSUMPTIONS.md` |
| Agent | `AGENT-nnn` | 全局 | 角色建立 | Active/Inactive | `AGENT_REGISTRY.md` |

> 注：`CHANGE-xxx` 用于「重大变更」执行记录；普通增量改动直接在 `CHANGELOG.md` 中按版本记录即可。

## 各 ID 的分配约束

- `Mnnn`：Module ID 分配后**不随意修改**；模块可更名、可废弃（状态 Deprecated/Archived），但 ID 不交给新模块复用。
- `API-Mnnn-nnn`：进入 **Frozen** 后，改动必须走 CR 变更流程；Removed 仅允许在无消费者或已完成通知/迁移后。
- `ADR-nnn`：一旦 Accepted 即视为决策事实；被新决策推翻时新开 ADR 并标记旧 ADR 为 Superseded（引用新 ADR）。
- `REQ-nnn` / `Mnnn` / `API-…` 编号顺序按登记先后，跳跃编号需在文档中注明原因。

## 引用完整性要求（登记即检查）

每登记一个 ID，同时确认：

- [ ] 命名空间唯一（对照对应 Registry）
- [ ] 已在对应 Registry/索引登记
- [ ] 依赖方文档已引用（若为被依赖项，通知消费者）
- [ ] 状态机字段已填写

## 规则维护

本规则变化属治理级变更：由 Project Master 提出，可在 `CHANGELOG.md` 记录，必要时写入 ADR。Agent 如需新 ID 类型，走 CR 流程。
