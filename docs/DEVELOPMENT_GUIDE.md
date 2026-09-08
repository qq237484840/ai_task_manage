# DEVELOPMENT_GUIDE —— 开发流程与变更治理

> 适用对象：所有参与开发的 Agent 与人。
> 本文定义跨模块的工程流程与治理规则；模块级操作细节见 `AGENT_GUIDE.md`，ID 规则见 `ID_GOVERNANCE.md`。

## 1. 总体开发模型

```text
需求 → 需求分析 → 系统架构 → 领域划分 → 模块划分 → 模块契约 →
接口设计 → 数据设计 → Agent 分工 → 模块设计 → 编码 → 测试 →
代码审查 → 文档整理 → 知识库更新 → 总控 Agent 验收 → 合并
```

**禁止**：想到功能直接写代码、遇问题再改、最后补文档。

核心工程原则：`Architecture First · Contract First · Module First · Documentation First · Test First where appropriate · Knowledge Indexed · Changes Tracked · Dependencies Explicit · Ownership Clear · Context Minimal`。

## 2. 设计优先级（默认）

```text
Correctness > Security > Maintainability > Reliability >
Extensibility > Performance > Development Speed
```

项目有特殊要求可调整，但必须记录 ADR。

## 3. 需求处理流程

用户提出需求时，Project Master 首先输出：

1. Requirement Classification（新功能/Bug/重构/架构/API/数据变更）
2. Requirement ID → 3. Affected Domain → 4. Affected Module → 5. New Module Required?
6. API Impact → 7. Data Impact → 8. Architecture Impact → 9. Dependencies
10. Agent Assignment → 11. Development Sequence → 12. Acceptance Criteria
13. Documentation Impact → 14. Risks

流程：`REQ-xxx → Impact Analysis → 定模块/API/数据 → 定 Agent → 建 Task → 设计 → 批准 → 实现 → 测试 → 文档 → 审查 → 合并`。

## 4. 影响分析（Impact Analysis）

重大变更必须输出：Affected Module / Affected API / Affected Data / Affected Consumers / Risk / Compatibility / Required Migration / Rollback。

## 5. 变更管理

任何需求变化先分类：Is New Feature? / Bug Fix? / Refactoring? / Architecture Change? / API Change? / Data Change? 再判断影响范围。

### 变更通道

| 通道 | 编号 | 用途 |
| --- | --- | --- |
| Change Request | `CR-nnn` | 普通变更申请（接口/数据/行为改动请求） |
| Architecture Change Request | `ACR-nnn` | 架构层问题与替代方案申请 |
| Bug | `BUG-nnn` | Bug 记录与根因说明 |
| 重大变更记录 | `CHANGE-nnn` | 已批准的重大变更执行与迁移记录 |

Agent 之间不允许通过互相修改代码"沟通"；统一走 Contract / Change Request / Issue / Decision / Event。

### CR 统一格式

CR-nnn：Title / Requester / Reason / Current Behavior / Requested Behavior / Affected Module / Affected API / Affected Data / Breaking Change / Risk / Recommendation。

### ACR 统一格式

ACR-nnn：Current Architecture / Problem / Why Current Design Is Insufficient / Proposed Architecture / Alternatives / Impact / Migration / Risk。由 Project Master 决定是否批准。

## 6. 接口（API）治理

- **禁止无记录修改其他模块已使用的 API**；进入 Frozen 后必须走变更流程。
- Breaking Change 禁止直接改，必须考虑：Versioning / Compatibility / Migration / Deprecation / Consumer Notification。
- 接口状态机与契约要素见 `API_REGISTRY.md` 与 `ID_GOVERNANCE.md`。

## 7. 数据治理

- 数据 Ownership：一个核心数据只有明确 Owner；他模块经接口读取，禁止直接改库（见 `DATA_MODEL.md`）。
- **数据库 Breaking Change**：禁止直接改生产结构而无迁移方案；必须分析现有数据/迁移/回滚/索引/性能/消费者/备份/兼容性。
- 敏感数据（用户/权限/Token/API Key/密码/外部服务凭据）：明确 Authentication / Authorization / Encryption / Secret Management / Audit / Logging / Data Exposure；**禁止硬编码密钥**。
- 日志规范：明确 What to Log / What Not to Log / Log Level / Correlation ID / Error ID / Audit；敏感信息禁止进普通日志。

## 8. Bug 修复规范

Bug 修复必须记录：Bug / Root Cause / Fix / Affected Area / Regression Test / Documentation Impact。不能只改代码不解释根因。

## 9. 重构规则

重构必须证明：为什么重构 / 解决什么问题 / 是否改变行为 / 影响哪些模块 / 是否影响 API / 是否影响性能 / 是否需要测试。禁止以"感觉更优雅"作为唯一理由。

## 10. 需求不明确时的处理（90 号规则）

识别歧义 → 列出选项 → 说明影响 → 请求决策。若不影响开发可先采用 Safe Default，但必须记录到 `ASSUMPTIONS.md`；关键业务规则禁止擅自假设。

## 11. 架构决策（ADR）

重要技术决策必须记录 ADR（Context / Problem / Options / Decision / Reason / Consequences），存放 `docs/adr/`。禁止出现"当初为什么这么设计"却找不到答案。

## 12. 代码-文档一致性（强制）

- 发现 `代码 ≠ 文档` 必须优先处理；文档承担 Agent Knowledge 职责，**不能默认"代码才是真的、文档以后再更新"**。
- 文档治理规则：Single Source of Truth、引用而非复制、避免大段重复、唯一 ID + 明确引用、可检索（详见 `ID_GOVERNANCE.md` 与 `INDEX.md`）。
- 简单 Getter/Setter 不要求详尽文档；重点覆盖核心业务逻辑、公共/跨模块接口、算法、数据转换、状态机、事务、并发、权限、安全、复杂逻辑。

## 13. 共享代码治理

公共区（Shared / Infrastructure / Common）只放真正跨模块通用内容；**公共代码不是垃圾桶**，禁止把业务逻辑塞进 Common。维护模块依赖图，**禁止循环依赖**；发现即停并重新设计。

## 14. 验收与合并

总控 Agent 验收 = Architecture + Boundary + API + Data + Code + Test + Documentation Review，全部通过 → `APPROVED`，否则 → `CHANGES_REQUIRED`（优先退回原 Agent）。
模块质量差时，优先提修改要求让原 Agent 修复，总控不盲目代改（保持责任清晰、变更可追踪）。

## 15. 文档-模块数量增长策略

随项目扩大，保证：快速定位、快速理解、局部开发/测试/修改。禁止让"每次改功能必须读全部项目"成为常态。所有知识遵循 `INDEX → Summary → Contract → Module → Code` 恢复路径。模块拆分/合并判断标准见 `MODULE_REGISTRY.md`。

## 16. 额外发现（Additional Finding）

Agent 发现"顺便改一下会更好"时：停止扩大范围，记录 Additional Finding 交由 Project Master 决定是否立项。

## 17. 待补充的登记表

以下登记表出现首条记录时创建：`TECH_DEBT.md`、`RISK_REGISTER.md`、`CONFIGURATION.md`、`EXTERNAL_SYSTEMS.md`、`DEPENDENCIES.md`、`FEATURE_MATRIX.md`。触发时机见 `INDEX.md`；重大第三方依赖升级必须分析兼容/安全/API 变更/性能/测试/影响模块/回滚。
