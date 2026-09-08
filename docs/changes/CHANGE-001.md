# CHANGE-001 —— M001 合并变更执行（CR-001/CR-002/ACR-001/ACR-002）

- **CHANGE ID**：CHANGE-001 ｜ **状态**：**Executing**（2026-09-08 启动，AGENT-M001） ｜ **日期**：2026-09-08
- **提出者**：Project Master ｜ **执行 Agent**：AGENT-M001（Task-CHG）
- **依据**：`docs/changes/CR-001.md`（Approved）、`CR-002.md`（Approved）、`ACR-001.md`（Approved）、`ACR-002.md`（Approved）——四项 2026-09-08 用户批准，合并为一个 CHANGE 执行
- **前置**：M002 契约草案 v0.3.0 已批准 Frozen（2026-09-08）→ 本变更执行启动（提供 M002 编码所需的 group_no/两级主体接口）
- **关联文档**：`MODULE_REGISTRY.md`（M001 行）、`DATA_MODEL.md`（DATA-001/002/004/005）、M001 九件套（冻结基线 v0.1.1 之上按批准条款修订）

## 变更范围（四条批准项合并执行，Single Source of Truth = 各自 CR/ACR 文件）

| 变更 | 内容摘要 | 代码影响面（M001） |
| --- | --- | --- |
| CR-001 | 任务 = **多学科作业登记单容器**；`task_items` 增加 `group_no`（学科作业段序号，段内 subject 一致、组号连续、默认组 0 收敛）；`reference_answer` 保留为**非判定基准**辅助字段（ADR-010 端到端直判口径，原"逐题对照"语义作废）；`item_type` 保留（题型标注） | `tasks`/`task_items` 建模、分组校验、查询（`get_task_group` 等） |
| ACR-001 | **两级主体**（ADR-009）：家庭账号家长 + **学生子账号**（完整登录绑定 student_id，仅本人数据；家长全家 + 兜底） | 认证/会话/授权中间件、主体上下文（student/family 两型 token）、越权矩阵 |
| CR-002 | **内容级判定链数据面**（布置登记拍照识别草稿、逐题对齐判定结果、报告草稿→复核定稿归档）——M001 面仅接口预留/字段语义（判定结果归 DATA-004/005，不落 M001） | M001 提供按日/按 `(student,subject,group_no)` 检索与冻结语义（"存在 assigned 照片起题目冻结"） |
| ACR-002 | 判定基准 = **端到端直判（不维护参考答案基准语义）**；AI Provider = **真实三方默认**（Mock 测试桩/离线） | M001 仅语义调整（`reference_answer` 非基准）+ Provider 配置面若涉及统一调用记录不落 M001 |

## 执行清单

1. 阅读四份 CR/ACR 全文 + 现有 M001 代码（`backend/app/modules/m001/`、`backend/tests/`）确认精确改动面
2. 数据面（CR-001/CR-002）：`task_items.group_no` + 容器语义 + 分组约束/查询/冻结语义调整 + 迁移策略（M001 未上线生产，直接演进 schema，`backend` 开发库重建）
3. 认证面（ACR-001）：学生子账号注册/登录与会话建模、主体两型 token、family 级隔离校验不变、student 主体限本人
4. 语义面（ACR-002/ADR-010）：`reference_answer` 接口入参保留可选但契约注释改为"非判定基准辅助字段"；任务/题目返回 DTO 相应注释
5. 测试：54 项既有回归全绿 + 新增（group_no 分组约束、容器多学科、student 子账号越权矩阵、family 兼容旧单学科任务）+ 双主体认证用例
6. 回填：M001 九件套（MODULE.md/SUMMARY/CONTRACT/API/DATA/DESIGN/FILES/TEST/CHANGELOG）按变更后实况修订；同步 `DATA_MODEL.md`（DATA-001/002 字段级）、`REQUIREMENTS`（REQ-001/002 措辞）、开放项 O-1/O-3/O-4 若涉及关闭
7. 联调预告：M002（Task-002）依赖 `get_task_group`/`can_accept_photo`/`mark_in_progress` 两主体化——本变更交付即用接口

## 验收标准（DoD）

- [ ] CR-001/ACR-001/CR-002/ACR-002 条款全部在 M001 代码与文档落实（交叉核对）
- [ ] `reference_answer` 不作为任何判定路径基准；`item_type` 仅标注
- [ ] 两级主体：student token 仅本人数据可读/写；family token 全家 + 兜底；跨家庭一律 404/403（对外 404）
- [ ] 单学科旧任务与多学科容器任务在 API/DTO 语义下均可表达（向后兼容）
- [ ] 既有 54 测试全绿 + 新增用例通过（backend/.venv 跑 pytest）
- [ ] M001 九件套回填（含 MODULE_CHANGELOG 记录本 CHANGE）并同步 DATA_MODEL/顶层状态

## 处理路径

Executing（AGENT-M001）→ 代码落地 + 测试 + 回填 → PM 复核 → 变更记录关闭（状态 Applied/Closed，随 M001 变更后版本 v0.1.2 或经 CR 审定的契约版）→ M002 Task-002 编码联调。
