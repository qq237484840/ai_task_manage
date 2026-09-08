# AGENT_GUIDE —— Agent 操作规范

> 适用对象：所有参与本项目的 Agent（总控 Agent、未来的模块 Agent）。
> 目的：让每个 Agent 在 **不扫描全项目** 的前提下，按统一规范理解任务、开发、交付。
> 阅读顺序建议：`AGENT_REGISTRY.md` → 本文件 → `ID_GOVERNANCE.md` → `DEVELOPMENT_GUIDE.md`。

## 1. 角色与权限模型

每个 Agent 必须遵守：**Read Scope / Write Scope / Review Scope**。

| Scope | 含义 | 示例 |
| --- | --- | --- |
| Read | 允许读取的范围 | PROJECT / ARCHITECTURE / 本模块 / 依赖模块 API |
| Write | 允许写入的范围 | 本模块代码与文档 |
| Request | 无权直接改但可发起申请 | 依赖模块 API 变更 |
| Forbidden | 禁止（无论是否有理由） | 直接修改其他模块 / 总体架构 / 核心数据模型 |

### 禁止清单（越权行为）

- 顺便修改其他模块 / 顺便优化架构 / 顺便重构公共代码 / 顺便修改数据库 / 顺便修改接口
- 发现问题时的正确动作：提出 **CR / ACR / Additional Finding**，由 Project Master 决定，**不得自行扩大任务范围**。

## 2. 通用开发流程（10 步）

```text
1 Read → 2 Analyze → 3 Design → 4 Confirm Contract →
5 Implement → 6 Test → 7 Review → 8 Document →
9 Update Knowledge → 10 Submit
```

禁止跳过设计阶段直接编码。

### 各阶段要点

| 阶段 | 产出/要求 |
| --- | --- |
| 1 Read | 只读必要知识：Task、PROJECT、ARCHITECTURE、MODULE_REGISTRY、本模块、依赖模块 API/Contract、相关 ADR。禁止无目的扫描全项目。 |
| 2 Analyze | 输出：需求分析 / 影响模块 / 影响 API / 影响数据 / 依赖 / 风险 / 潜在冲突 / 所需变更。 |
| 3 Design | 先输出设计（模块级写 `MODULE_DESIGN.md`）：架构、类、服务、仓储、DTO、接口、数据、API、事件、配置、异常、日志、安全、测试。 |
| 4 Confirm Contract | 与 Project Master / 依赖方确认模块契约，冻结前不得擅自实现未确认接口。 |
| 5 Implement | 遵守架构、边界、契约、命名规范；避免重复代码、隐藏依赖、硬编码；职责单一。 |
| 6 Test | 依据模块类型选择测试，并**说明为什么需要/为什么不需要**（Unit/Integration/API/Contract/Boundary/Exception/Concurrency/Performance）。 |
| 7 Review | 自检：架构、边界、依赖、API、数据、安全、性能、异常、日志、测试、文档。 |
| 8 Document | 更新模块文档集（见第 4 节），并同步受影响的总表。 |
| 9 Update Knowledge | 更新 Registry / INDEX / 相关摘要；确保索引与实际一致。 |
| 10 Submit | 提交交付物清单（见第 5 节），等待 Project Master 验收。 |

## 3. 上下文加载策略（Context Budget）

> 最小必要上下文原则。禁止因"可能有用"加载大量无关文件。

```text
任务 → SYSTEM_SUMMARY → 目标模块 MODULE_SUMMARY
     → Contract → API → Data → 必要 Code
```

读取优先级：`索引 → 摘要 → 契约 → 必要代码`。禁止无目的扫描整个项目（最高级原则之一）。

## 4. 模块文档集（九件套，模块划分后按真实模块生成）

每个模块拥有独立目录 `docs/modules/Mxxx/`，包含：

| 文件 | 一句话职责 |
| --- | --- |
| `MODULE.md` | 模块总览：Purpose、Responsibilities、Non-Responsibilities、Dependencies、Consumers、Owned Data、Exposed Services、Forbidden Access。 |
| `MODULE_SUMMARY.md` | **30 秒摘要**：Purpose/Responsibilities/Inputs/Outputs/Dependencies/APIs/Data/Main Files/Risks/Status。进入模块的第一入口。 |
| `MODULE_CONTRACT.md` | 契约（黑盒）：Module ID/Name/Purpose/Responsibilities/Non-Responsibilities/Inputs/Outputs/Dependencies/Exposed APIs/Events/Data Ownership/Configuration/Security/Performance/Failure Behavior/Version/Compatibility。 |
| `MODULE_DESIGN.md` | 设计：架构/类/服务/仓储/DTO/接口/数据/API/事件/配置/异常/日志/安全/测试。 |
| `MODULE_API.md` | 模块 API 权威源（每 API 要素见 `API_REGISTRY.md` 契约要素清单）。 |
| `MODULE_DATA.md` | 模块数据/实体（跨模块核心实体须同步 `DATA_MODEL.md`）。 |
| `MODULE_FILES.md` | 文件级知识（L6）：File/Purpose/Module/Dependencies/Exports/Classes/Methods/Important Notes/Modification Risk。 |
| `MODULE_TEST.md` | 测试策略与清单（含"为何需要/为何不需要"说明）。 |
| `MODULE_CHANGELOG.md` | 模块变更历史。 |

**模块黑盒原则**：模块间只能依赖 API/Interface/DTO/Event/Message/Contract；禁止跨模块依赖内部 Class/Repository/数据库。

**方法级知识（L7）**：核心方法（核心业务逻辑/跨模块接口/算法/状态机/事务/并发/权限等）在文档中描述「为什么这么做 + 做什么 + 数据如何流动 + 关键判断」，不做逐行翻译。方法描述要素：Responsibility/Input/Output/Exceptions/Side Effects/Dependencies/Internal Logic/Performance/Concurrency/Transaction/Security。

## 5. 模块 Agent 提交的交付物

1. Source Code；2. Tests；3-10. 模块文档九件套；11. Change Request（如需）；12. Architecture Request（如需）。

## 6. Definition of Done（模块/功能完成标准）

以下全部满足才可标记 Completed：

- [ ] Requirement / Design / Code / Unit Test / Integration Test 完成
- [ ] API Test（适用时）/ Contract verified
- [ ] Architecture / Dependency / Security verified
- [ ] Documentation complete（含 File、Method 级）
- [ ] API_REGISTRY / MODULE_REGISTRY / 数据文档 / Changelog 已更新
- [ ] 无越权修改 / 无循环依赖 / 无未契约接口

## 7. 与 Project Master 协作

- 分配的任务单（Task ID / Agent ID / Module / Objective / Requirements / Allowed-Files / Forbidden-Files / Dependencies / 预期 API / 预期数据变更 / 预期测试 / 预期文档 / Acceptance Criteria）由 Project Master 签发。
- 发现问题不得擅自扩大范围；记录 Additional Finding 交给 Project Master。
- 交付后由 Project Master 验收：通过 → `APPROVED`；否则 → `CHANGES_REQUIRED`（优先退回原 Agent 修复，保持责任与知识清晰）。

## 8. 通用底线

- 不猜：需求不明确时按 `DEVELOPMENT_GUIDE.md` 歧义处理流程，或记录 Safe Default 假设（`ASSUMPTIONS.md`）。
- 不扫全项目：按层读取、局部加载、接口协作。
- 不留知识断链：每次改动同步文档与索引。
