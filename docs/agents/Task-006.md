# Task-006 任务书 —— 横切 AI 接入层 `app/core/ai/`（实现）

- **Task ID**：Task-006 ｜ **Agent**：`AGENT-AI` ｜ **Module**：**横切基础设施**（不设业务 Module ID；代码面 `backend/app/core/ai/`）
- **签发**：Project Master，2026-09-10 ｜ **状态**：**已交付 → PM 复核 APPROVED（2026-09-10）**（专属 39 例；`AT_AI_*` 与 `ai_call_records` 已由 PM 回填 `CONFIGURATION.md` §五 / `DATA_MODEL.md` DATA-009）
- **启动前置（Contract First，硬约束）**：`CHANGE-003` **② 契约修订评审（Task-004 / Task-005）经 PM 复核 APPROVED 之后**方可开始编码 —— **前置已于 2026-09-10 满足**（Task-004/Task-005 均 **PM 复核 APPROVED**，任务关闭；契约 v0.2.0/v0.4.0 草案同步交付，结果 schema 边界可依据）。② 未 APPROVED 前本任务**不得落地任何代码**（边界与结果 schema 由 M001/M002 契约定稿提供）
- **前置依据**：`docs/adr/ADR-014.md`（执行方决议 Accepted）、`docs/adr/ADR-011.md`（真实三方默认 / Mock 降级）、`docs/requirements/CLARIFICATION-2026-09-10.md` §2.D4 + §4.1 第 10 项、`docs/changes/CHANGE-003.md` §2.3 C1、`docs/requirements/REQ-010.md` R7
- **任务书登记**：`docs/AGENT_REGISTRY.md`（`AGENT-AI` 行）｜ **验收**：横切层 DoD（本任务自含）+ M001/M002 契约侧的消费断言

## 1. Objective（目标）

按 `CHANGE-003` §2.3 C1 落地项目**唯一的 LLM 接入层** `app/core/ai/`：Provider 抽象（Vision / OCR / LLM）+ prompt 版本管理 + 结果 **schema 校验** + 超时/重试/**降级**，并统一写入 AI 调用记录（`DATA-009`）；供 M001（链路 T 任务解析）与 M002（链路 H 挂接建议 / 完成分析）经内部接口调用。

> 本任务是**共享基础设施**交付：不承载业务语义（建不建任务、挂不挂照片由 M001/M002 决定），只负责"可靠地调用 AI 并保证输出可校验、可追溯、可降级"。

## 2. Requirements（依据权威源，只读，禁止复制改写）

- `docs/adr/ADR-014.md`（执行方 = `AGENT-AI`；写区仅 `app/core/ai/`）
- `docs/adr/ADR-011.md`（真实三方默认、Mock 为测试桩 / 离线降级，`mock-*` 显式标注；`DATA-009` 调用记录）、`docs/adr/ADR-003.md`（可观察依据 / 不武断：**本层不产出评语，仅保证输出结构与置信度**）
- `docs/CHANGE-003.md` §2.3 C1、`docs/REQUIREMENTS.md` REQ-008（横切 AI 治理约束）
- M001 契约 v0.2.0 / M002 契约 v0.4.0（Task-004 / Task-005 定稿版）中定义的结果结构（学科子任务 + 内容项草稿；照片 ↔ 聚合子任务挂接建议；聚合子任务级完成结论）
- `docs/CONFIGURATION.md`（配置项登记为 PM 职责，本任务只提 Request）
- 现有基座：`backend/app/core/config.py`（pydantic-settings，前缀 `AT_`）、`backend/app/shared/`（日志/异常）、`backend/tests/`

## 3. Scope（范围）

### 3.1 本任务交付

| 交付 | 说明 |
| --- | --- |
| Provider 抽象 | `VisionProvider` / `OCRProvider` / `LLMProvider` 三类协议 + Provider 注册与选择（真实三方实现 + `mock-*` 测试桩/离线降级）；业务代码不感知具体厂商 |
| prompt 版本管理 | prompt 资产集中存放（禁止散落业务代码）+ 版本标识；每次调用记录 `prompt_version` |
| 结果 schema 校验 | 以 pydantic schema 校验 AI 返回；不合规 → 丢弃 + 重试/降级，**不得将未经校验的输出交给业务层** |
| 超时 / 重试 / 降级 | 超时、错误映射（网络/限额/内容拒绝等）、重试策略；降级路径返回明确的"不可用/不合规"信号供 M001/M002 走**手工兜底**（`CLARIFICATION` §2.C6） |
| 能力接口 | 供上游调用的三个能力入口（签名以 Task-004/Task-005 定稿为准）：**① 任务输入源解析**（图片/文本 → 学科子任务 + 内容项草稿 + 置信度）；**② 作业照片挂接建议**（照片 → 聚合子任务 N:N + 置信度）；**③ 聚合子任务级完成结论**（完成 / 部分完成 / 未完成 / 无法判断 + 依据照片 + 置信度） |
| 调用记录 | 每次调用写 `DATA-009`：`model` / `prompt_version` / `request_id` / `latency` / `token_usage` / `result` / `confidence` / `error`（可追溯链） |
| 测试 | 新增横切层用例（schema 合规/不合规、超时、降级、Mock Provider、调用记录字段完整性）+ **既有 112 项不回归** |
| Request（非本任务直接落库） | Provider 配置项（模型 / 密钥 / 限额 / 超时重试）登记 `docs/CONFIGURATION.md`；真实三方接入登记 `docs/EXTERNAL_SYSTEMS.md`；架构口径同步 `docs/ARCHITECTURE.md` —— **均由 PM 落库** |

### 3.2 Allowed-Files（可写）

- `backend/app/core/ai/**`（本任务唯一代码写区）
- `backend/tests/**`（新增 AI 接入层用例，禁止破坏既有用例）
- `backend/app/core/config.py`（仅当需要读取 Provider 配置项字段；**新增配置项须先以 Request 报 PM 登记**）

### 3.3 Forbidden-Files / 边界

- **禁止改动任何业务模块代码**：`backend/app/modules/m001/**`、`backend/app/modules/m002/**`、`backend/app/api/v1/**` 业务路由
- **禁止改动任何模块契约文档**（`docs/modules/**`）与治理层文档（Registry/ADR/CHANGE/REQUIREMENTS/ROADMAP/PROJECT_STATUS/CHANGELOG/INDEX/CONFIGURATION）
- 禁止在 `app/core/ai/` 内实现业务规则（任务归属、挂接状态机、完成结论的"业务正确性"判定、评分/评语——后两者属 V2）
- 禁止实现 V2 功能（M005/M006/M007 相关：六维评分 / 评语 / 报告；ADR-002 + ADR-014）
- 禁止硬编码模型名/密钥；禁止绕过 schema 校验直接把原始 AI 输出交给上游
- 禁止自行分配 API / DATA / Task ID

## 4. Dependencies（前置就绪条件）

- **硬前置**：`CHANGE-003` ② 契约评审 **APPROVED**（Task-004 M001 v0.2.0 / Task-005 M002 v0.4.0 定稿 → 提供结果结构边界）
- 上游调用方：M001（链路 T 解析，Task-004 后的实施任务）、M002（链路 H 挂接与分析，Task-005 后的实施任务）——本层先交付，**以 Mock 模式即可解阻上游开发**
- 真实三方 Provider：密钥/模型/限额由部署侧提供（未就绪时 Mock 降级路径必须可用，`RISK-008`）

## 5. Expected Deliverables（完成即提交 PM 复核）

- 代码按 §3.1 落地，lint 无错误；`backend/.venv` 下 `pytest` **全绿（既有 112 + 新增）**
- 降级路径实证：Mock 模式与"三方不可用/返回不合规"两种情形均可复现，且**上游收到明确不可用信号**（不产生脏数据）
- 调用记录实证：一条完整调用的 `DATA-009` 字段齐全、可按 `request_id` 追溯
- 提交 PM 的 Request 清单（Provider 配置项 / `EXTERNAL_SYSTEMS.md` / `ARCHITECTURE.md` 口径）
- 完成后：提交 PM 按本任务 §6 DoD 复核

## 6. Acceptance Criteria（DoD，AGENT_GUIDE §6）

- [ ] Provider 抽象齐备（Vision / OCR / LLM）+ 真实三方实现与 `mock-*` 测试桩可切换（切换不改业务代码）
- [ ] prompt 资产集中管理并带版本标识，`prompt_version` 写入调用记录
- [ ] **所有** AI 输出经 schema 校验；不合规输出被拦截并降级（有测试证明）
- [ ] 超时/重试/错误映射/降级路径实现并有测试覆盖；降级时上游可识别并走手工兜底
- [ ] `DATA-009` 调用记录字段完整可追溯
- [ ] 三个能力接口（任务解析 / 挂接建议 / 完成结论）均可按契约结构返回，含置信度与 `无法判断` 出口
- [ ] 既有 112 项测试不回归；新增用例通过
- [ ] 未越权改动业务模块代码 / 契约文档 / 治理文档；配置项经 Request 由 PM 落库
- [ ] PM 复核 APPROVED → Task-006 关闭 → `app/core/ai/` 进入稳定维护态

> 注：本任务**不含**真实三方密钥联调验收（密钥未就绪）——Mock 模式全链路可用为**最低验收线**；真实三方接入随部署侧密钥就绪后按 `ADR-011` 补充验证并登记 `EXTERNAL_SYSTEMS.md`。
