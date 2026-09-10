# CHANGE-003 —— CR-003 执行：作业任务语义重构 + 归属与判定双层模型

- **CHANGE ID**：CHANGE-003 ｜ **状态**：**已完成（Closed，2026-09-10，PM 复核 APPROVED）** ｜ **日期**：2026-09-10
- **提出者**：Project Master ｜ **执行 Agent**：**Task-004 = AGENT-M001**（M001 契约修订）、**Task-005 = AGENT-M002**（M002 契约修订）、**Task-006 = AGENT-AI**（横切 `app/core/ai/` 实现，③ 阶段）、**Task-007 = AGENT-M001**（M001 实施，③）、**Task-008 = AGENT-M002**（M002 实施，③）、**Task-009 = AGENT-M002**（前端「作业」域迁移，③）、**Task-010 = AGENT-M002**（门控链路缺陷修复 `BUG-002`，③ 补）
- **依据**：`docs/changes/CR-003.md`（**Approved**，2026-09-10 用户逐条确认）+ `docs/adr/ADR-013.md`（**Accepted**，双层模型）+ `docs/adr/ADR-014.md`（**Accepted**，V1 范围收窄与横切层执行方）+ `docs/requirements/REQ-010.md`（**Approved**）
- **权威源**：`docs/requirements/CLARIFICATION-2026-09-10.md`（本 CHANGE 不复制其内容，逐条引用）
- **前置**：M001 **Stable v0.1.2**（冻结面被打开，须走本变更）；M002 **Developing / 契约 v0.3.0 Frozen**（契约被修订）；CHANGE-002（前端栈切换）Executing
- **关联**：`docs/DATA_MODEL.md`（DATA-001/003 修订 + DATA-012~018 新增）、`docs/CONFIGURATION.md`（4 个 `AT_*` 配置）、`docs/adr/ADR-010.md`（判定粒度 Superseded）、`REQ-001`~`REQ-007`（措辞已精校）、`docs/changes/BUG-001.md`（验收阻塞缺陷，已修）

## 1. 变更范围（按 CR-003 条款）

| # | 面 | 内容 |
| --- | --- | --- |
| 1 | 事实层 | `tasks` 唯一键改 **`(student_id, category, belong_date)`**；新增 `category`/`belong_date`/`week_index`/`window_type`/`spec_status`；`task_items` **废弃**；新增 `task_contents`/`task_spec_sources` |
| 2 | 聚合层 | 新建 `task_groups`（含 `policy_version`）+ `task_group_subjects`（**★判定单元**）+ `photo_subject_links`（**N:N**）+ `completion_analyses`；配置 `window_policies` |
| 3 | 归属引擎 | `WindowResolver`：`belong_date`（`AT_DAY_CUTOFF` 默认 04:00 / `AT_TIMEZONE`）+ `week_index`（`AT_TERM_START`/`AT_TERM_END`）+ 周末聚合（周五 04:00 ~ 周一 04:00）+ 假期自然周 |
| 4 | 链路 T | 「任务」入口上传（图片 / **粘贴文本**）→ AI 解析「今日任务」草稿 → 家长确认 / **隐式确认** |
| 5 | 链路 H | 「作业」入口上传（**不填任何内容**）→ AI 挂接建议 → 家长**逐张**复核 → **窗口级门控** → 完成分析草稿 → 确认 |
| 6 | 判定 | 粒度 = **聚合子任务（学科）级**（`完成/部分完成/未完成/无法判断` + 依据 + 置信度）；ADR-010 逐题判定作废，其余原则继承 |
| 7 | 兜底 | LLM 失败 → 照片 `unassigned` + **手工挂接**（手工路径必须保留）；手工改归属日连锁规则（含挂接目标迁移） |
| 8 | 横切 | 新增 **`app/core/ai/`**（provider 抽象 + prompt 管理 + 结果 schema 校验 + 降级），不塞进业务模块 |
| 9 | 前端 | 菜单「照片」→「**作业**」；列表按周次分组 + 周末聚合展示；任务列表页 422 缺陷修复（**已完成**，见 `BUG-001`） |
| 10 | 配置 | `AT_TIMEZONE` / `AT_TERM_START` / `AT_TERM_END` / `AT_DAY_CUTOFF`（登记 `docs/CONFIGURATION.md`，**已完成**） |

## 2. 契约修订要点清单（Task-004 / Task-005 执行依据）

> 本清单是**评审基线**；执行 Agent 如发现清单与 `CLARIFICATION` 权威源冲突，**以权威源为准并以 Request 报 PM**，禁止自行扩大或缩小范围。

### 2.1 M001 九件套（Task-004，AGENT-M001）

| # | 修订点 | 涉及文档 |
| --- | --- | --- |
| A1 | `tasks` 字段与唯一键：新增 `category`（v1 仅 `school`）/`belong_date`/`week_index`/`window_type`/`spec_status`；唯一键 = `(student_id, category, belong_date)`；`title` 支持解析器自动生成（如「09-09 周三」） | `MODULE_DATA.md`、`MODULE_DESIGN.md` |
| A2 | `task_items` 标注 **Deprecated**（V1 不再写入，表保留兼容旧数据）；原「多学科登记单容器 + 学科作业段 `group_no`」条款**作废** | `MODULE_DATA.md`、`MODULE_CONTRACT.md`、`MODULE_API.md` |
| A3 | 新增 `task_contents`（DATA-014，只读展示、不参与挂接与判定）与 `task_spec_sources`（DATA-015，多段输入源：`seq`/`kind(text\|image)`/`text_content`/`photo_id`） | `MODULE_DATA.md` |
| A4 | 任务创建流程改：**输入源上传 → AI 解析草稿 → 家长确认**（含**隐式确认**路径）；**上传无需填写任何内容**；`spec_status` 状态机 | `MODULE_CONTRACT.md`、`MODULE_API.md`、`MODULE_DESIGN.md` |
| A5 | 新增**归属引擎** `WindowResolver.resolve(ts) → {belong_date, week_index, window_type, group_key}`（策略接口，便于替换规则）；读 4 个 `AT_*` 配置 | `MODULE_DESIGN.md`、`MODULE_DATA.md` |
| A6 | 新增聚合层 `task_groups`（含 `policy_version`）+ `task_group_subjects`（**★判定单元**）及查询契约 | `MODULE_DATA.md`、`MODULE_API.md` |
| A7 | **配置锁定语义**写入契约：变更只影响未聚合对象；已聚合按生成时配置；锁定粒度 = 每个 `(学生, 聚合对象)`；锁定触发 = 数据写入（**纯浏览不锁**）；`belong_date` 上传即固化、不回算历史 | `MODULE_CONTRACT.md`、`MODULE_DESIGN.md` |
| A8 | **手工改归属日连锁规则**契约化：重算快照 / 迁移 FK / 源聚合变空则删 / 已被完成分析消费则拒绝 / 审计留痕 / **跨聚合迁移同步挂接目标** | `MODULE_CONTRACT.md`、`MODULE_API.md` |
| A9 | 端点与 API ID：新增解析/确认/聚合查询端点 → **API ID 由 PM 分配**（禁止自行编号） | `MODULE_API.md`（草案）+ PM 登记 `API_REGISTRY.md` |
| A10 | 测试基线：既有 **89 passed** 全绿 + 新增（归属边界 4 点、周次起算、周末聚合、唯一键冲突、配置锁定按学生隔离） | `MODULE_TEST.md` |
| A11 | 回填：九件套 + `MODULE_CHANGELOG.md`（记录本 CHANGE）+ `DATA_MODEL.md` DATA-001 字段级 | 全部九件套 |

### 2.2 M002 九件套（Task-005，AGENT-M002）

| # | 修订点 | 涉及文档 |
| --- | --- | --- |
| B1 | `photos` 增加 `kind`（`task_spec` \| `homework`，**由上传入口决定**，权威在 `upload_batches.kind`）；`subject` / `group_no` 标 **Deprecated**；`task_id` 降级为**窗口级归属** | `MODULE_DATA.md`、`MODULE_DESIGN.md` |
| B2 | 上传入口分「任务」/「作业」；**「作业」上传不填任何内容**（移除预选任务/学科要求） | `MODULE_CONTRACT.md`、`MODULE_API.md` |
| B3 | 归属约束由**段级 1:N** 放开为 **照片 ↔ 聚合子任务（学科）N:N**（新增 `photo_subject_links`，DATA-016）；建议态/确认态的承载结构随之修订 | `MODULE_DATA.md`、`MODULE_CONTRACT.md` |
| B4 | 新增 `completion_analyses`（DATA-017，草稿 / 确认 / 重跑版本）+ **窗口级门控**规则（全部照片挂接确认后才触发分析，否则提示「待复核 N 张」） | `MODULE_DATA.md`、`MODULE_CONTRACT.md`、`MODULE_API.md` |
| B5 | 挂接与复核链路：上传成功**异步触发**挂接建议（幂等，只处理未挂接）→ 逐张 accept / reject / 改挂 → 门控 → 完成分析草稿 → 家长确认 | `MODULE_DESIGN.md`、`MODULE_API.md` |
| B6 | 降级兜底：LLM 超时 / 返回不合规 → 照片保持 `unassigned` + 提示手工挂接（**手工路径必须保留**） | `MODULE_CONTRACT.md`、`MODULE_DESIGN.md` |
| B7 | 清理 `photos.suggestion_json` 注释中的「**M003 建议快照**」文档漂移（现状仅 `m001` / `m002`） | 代码注释 + `MODULE_DATA.md` |
| B8 | 端点与 API ID：新增挂接 / 复核 / 分析端点 → **API ID 由 PM 分配**（禁止自行编号） | `MODULE_API.md`（草案）+ PM 登记 `API_REGISTRY.md` |
| B9 | 测试基线：既有 **112**（M001 89 + M002 11 + API 12）全绿 + 新增（N:N 挂接、门控、降级手工路径、跨聚合迁移） | `MODULE_TEST.md` |
| B10 | 回填：九件套 + `MODULE_CHANGELOG.md` + `DATA_MODEL.md` DATA-003 字段级 | 全部九件套 |

### 2.3 横切（**已随 ADR-014 定稿**）

| # | 修订点 |
| --- | --- |
| C1 | 新增 `app/core/ai/`：Provider 抽象（Vision/OCR/LLM）+ prompt 版本管理 + 结果 **schema 校验** + 降级；承接 ADR-011（真实三方默认、Mock 降级）与 DATA-009（调用记录） |
| C2 | 归属为**共享 / 基础设施**，**不设业务模块**（`MODULE_REGISTRY.md` §共享基础设施）；**执行方 = 新增 `AGENT-AI`**（`ADR-014` 决议 3，任务书 `docs/agents/Task-006.md`，写区仅 `backend/app/core/ai/**`）；**启动前置 = ② 契约评审 APPROVED**（Contract First） |

## 3. 执行分解与顺序

| 阶段 | 任务 | Agent | 状态 |
| --- | --- | --- | --- |
| ① 需求落库 | REQ-010 分配 + REQ-001~007 精校 | Project Master | **已完成**（2026-09-10） |
| ① 配置登记 | `docs/CONFIGURATION.md` | Project Master | **已完成**（2026-09-10） |
| ① 缺陷修复 | 任务列表页 422 + 同类隐患 | AGENT-M001 面 | **已完成**（`BUG-001`） |
| ① 横切清理 | `backend/app/modules/m002/` 中「M003」前向引用注释漂移（14 处，**仅注释**） | Project Master | **已完成**（2026-09-10；pytest 112 全绿） |
| ① 边界决议 | `ADR-014`（V1 范围收窄 + 横切层执行方）+ PD-026~029 | Project Master | **已完成**（2026-09-10，用户逐项拍板 §6 Q1~Q4） |
| ② **契约修订评审** | M001 九件套 → **Task-004**（v0.2.0 草案）；M002 九件套 → **Task-005**（v0.4.0 草案）（边界已由 `ADR-014` 闭合） | AGENT-M001 / AGENT-M002 | **已完成**（2026-09-10 **PM 复核 APPROVED**，两任务关闭；API ID 已分配登记、`DATA_MODEL` 字段级已同步） |
| ③ 横切实施 | `app/core/ai/` → **Task-006** | AGENT-AI | **已完成**（2026-09-10 交付，PM 复核 APPROVED；专属 39 例全绿） |
| ③ 实施（M001） | 事实层按天重构 → 归属引擎 `WindowResolver` → 聚合层 → 链路 T | **Task-007**（AGENT-M001） | **已完成**（2026-09-10 交付，PM 复核 APPROVED；含前端任务域） |
| ③ 实施（M002） | 入口 `kind` → **N:N 挂接** → 逐张复核 → 窗口级门控 → 完成分析 | **Task-008**（AGENT-M002） | **已完成**（2026-09-10 交付，PM 复核 APPROVED；Task-002 冻结段增量改接收口） |
| ③ 前端 | 「照片」改名「作业」+ 周次 / 周末分组展示 + M002 v0.4.0 前端调用面（挂接复核改 `group_subject_id` / 门控 / 完成分析） | **`Task-009`（AGENT-M002）** | **已完成（PM 复核 APPROVED，2026-09-10）**（交付与复验证据见 `docs/agents/Task-009.md` §7） |
| ③ 后端修复（门控） | `GET /photo-gates` 按窗口分组 + 完成分析门控前置生效（`409 gate_not_satisfied` 可达）+ 真机集成用例 | **`Task-010`（AGENT-M002）** | **已完成（PM 复核 APPROVED，2026-09-10）**（缺陷 `BUG-002` → **Verified**；真机集成 4 例；全量 `pytest` **211 passed / 0 failed**；**M001 零改动**） |
| ④ 验收 | `CLARIFICATION` §5 验收剧本 **7 条** 逐项验收（含浏览器级） | Project Master | **已完成（2026-09-10 收口）**：`Task-011`（AGENT-M002）取证 → PM 复核 = 条件达成（3 项缺口）→ `Task-012`/`Task-013` 并行修复（`BUG-004`/`BUG-003`）→ **`Task-014`（AGENT-M002）去替身复审经 PM 亲手判别力复现 + 全量 237/0 + 浏览器级 18/18 PASS 成立** → 双 BUG 置 **Verified** → ④ **判达成** |

> **前置约束**：③ 不得在 ② 评审 APPROVED 前启动（Contract First，`DEVELOPMENT_GUIDE.md`）；**③ 已于 2026-09-10 解禁**（契约 v0.2.0 / v0.4.0 经用户批准 **Frozen**）。

## 4. DoD（本 CHANGE 关闭条件）

- [x] **§6 四项阻塞（Q1~Q4）已决议并落库**：`ADR-014`（Accepted）+ PD-026~029 + `MODULE_REGISTRY` / `AGENT_REGISTRY` / `REQUIREMENTS` / `ROADMAP` 同步（2026-09-10）
- [x] Task-004 / Task-005 契约修订经 PM 复核 **APPROVED**（2026-09-10；九件套齐备、与 `CLARIFICATION`/`REQ-010`/`ADR-013`/`ADR-014`/`DATA_MODEL` 一致、无越权改治理文档）
- [x] API ID 由 PM 分配并登记 `API_REGISTRY.md`（`API-M001-018~021`、`API-M002-007~011`，Draft）；`DATA_MODEL.md` 字段级同步（DATA-001/003 修订 + DATA-012~017）
- [x] 横切层 `app/core/ai/` 按 Task-006 交付并通过 PM 复核（schema 校验 + 降级 + `DATA-009` 调用记录）—— **已完成（2026-09-10，PM 复核 APPROVED；`Task-013` 修复 `BUG-003` 后经 `Task-014` 复审在真实装配路径下成立）**
- [x] 实施完成：事实层按天唯一、聚合层落库且 `policy_version` 正确锁定、归属引擎通过边界用例 —— **已完成（`Task-007`/`Task-008` PM 复核 APPROVED；`Task-012` 修复 `BUG-004` 使链路 T 核心 AI 解析真跑并经 `Task-014` 复审确认）**
- [x] `CLARIFICATION` §5 **验收剧本 7 条**全部通过（含第 7 条浏览器级复验）—— **已达成（2026-09-10）**：`Task-011` 取证 7 条 → `Task-012`/`Task-013` 修复剧本 4 的 AI 解析语义（`BUG-004`）与剧本 5/6 的 AI 建议环节（`BUG-003`）→ **`Task-014` 去替身复审**：剧本 4/5 + 边界 2 例走 `app/core/ai` 真实装配路径、浏览器级剧本 5 **18/18 PASS**（`model: "mock-vision"`）、PM 亲手判别力复现（关 Mock 兜底 → `unassigned`/`[]` 断言立败；还原 → 全绿）→ 双 BUG 置 **Verified**
- [x] M001 契约 **v0.2.0 Frozen**（用户批准 2026-09-10）并同步 `MODULE_REGISTRY.md`；M002 契约 **v0.4.0 Frozen**（同）
- [x] `REQUIREMENTS.md` / `PROJECT_STATUS.md` / `CHANGELOG.md` / `ROADMAP.md` 收口一致 —— **已完成（2026-09-10，均随 v0.22.0 同步）**：`PROJECT_STATUS.md` → **v0.22.0**（M001/M002 均 Stable）；`CHANGELOG.md` → **v0.22.0** 条目；`ROADMAP.md` → 「里程碑收口（v0.22.0）」注；`REQUIREMENTS.md` 需求状态不变（REQ-001/009 随 M001 已 Done；REQ-005~007 Deferred 不变）；`INDEX.md` / `TECH_DEBT.md`（`TD-003` → Closed）/ `AGENT_REGISTRY.md` 同步

## 5. 风险

| 风险 | 说明 | 缓解 |
| --- | --- | --- |
| 聚合层一致性与追加维护成本 | 跨天聚合、配置锁定、跨聚合迁移 | `policy_version` 显式锁定 + 迁移连锁规则契约化 + 专项测试（A10/B9） |
| AI 解析 / 挂接可靠性 | 解析错误污染事实层 | 草稿必经确认（`spec_status`）+ 隐式确认展示摘要 + `无法判断` 出口 + 手工兜底 |
| **M001 Stable 冻结面被打开** | 破坏性变更（唯一键 / 废弃实体） | 走本 CHANGE 显式授权；V1 无生产数据，开发库直接演进 |
| ~~模块边界（M003~M007 / 横切层归属）~~ | ~~见 §6 待确认项，未定则契约评审无完整边界~~ | **已解除（2026-09-10，`ADR-014`）**：M003/M004 职责吸收、M005~M007 后置 V2、横切层 = `AGENT-AI`（Task-006） |
| V1 收窄后 V2 回归成本 | M005~M007 与 `REQ-005`~`REQ-007` 后置，回归时需重评估 | 见 `RISK_REGISTER.md` **RISK-012** |

## 6. 待确认项（**已全部决议关闭**，2026-09-10）

> 用户于 2026-09-10 就下列四项逐项拍板；决议已固化为 **`docs/adr/ADR-014.md`（Accepted）** 并登记 **PD-026~PD-029**。本表由"阻塞项"转为**决议记录**，后续仅作追溯用。

| # | 事项 | 决议（用户 2026-09-10） | 落库 |
| --- | --- | --- | --- |
| **Q1** | M003~M007 的 V1 职责是否被 M001 / M002 + `app/core/ai/` 吸收？ | **M003/M004 职责吸收**（链路 T → M001；链路 H 挂接/复核/分析 → M002），**Module ID 保留不撤销**，状态 → **Deferred**；M005~M007 状态随 Q2 → **Deferred（V2）** | `ADR-014` 决议 1；`MODULE_REGISTRY.md`；`AGENT_REGISTRY.md`（AGENT-M003~M007 → Inactive） |
| **Q2** | `REQ-005`（六维评分）/ `REQ-006`（评语）/ `REQ-007`（报告）是否 V1 必做？ | **全部后置 V2**（需求单保留不作废，状态 → **Deferred**）；V1 范围 = `CLARIFICATION` §4.1 **必做 10 项**，验收 = §5 **剧本 7 条** | `ADR-014` 决议 2；`REQUIREMENTS.md` + `REQ-005/006/007.md`；`ROADMAP.md`（域 D / 里程碑 M-D 后置） |
| **Q3** | 横切层 `app/core/ai/` 的执行方 | **新增 `AGENT-AI`（Task-006）**，写区仅 `backend/app/core/ai/**`；不设业务 Module ID；启动前置 = ② 评审 APPROVED | `ADR-014` 决议 3；`AGENT_REGISTRY.md`；`docs/agents/Task-006.md`；`CHANGE-003` §2.3 / §3 |
| **Q4** | Task-002 的去留（v0.3.0 编码 vs 契约 v0.4.0 改接） | **部分冻结 + 定稿后增量改接**：保留已交付成果，冻结「归属/挂接」段，允许收尾与 CR-003 无关段（质检 / 归一 / 受控存储 / 受控取图 / 双主体 API）；Task-005 定稿后按 v0.4.0 增量改接，**返工面限于归属段** | `ADR-014` 决议 5；`docs/agents/Task-002.md` 处置节；`AGENT_REGISTRY.md`；`PROJECT_STATUS.md` PD-029 |

> **处理路径（已执行）**：模块边界变更经 **ADR-014** 明确（满足 ADR-002 范围控制要求：走变更流程、不新增业务模块、仍登记 M001~M007 七个 Module ID）；Registry / REQUIREMENTS / ROADMAP / PROJECT_STATUS / CHANGELOG / INDEX 已同步；`§2.3` 横切清单与 M003~M007 相关表述随之定稿。
