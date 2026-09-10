# M002 模块变更记录 —— 作业图片采集与归属

- **模块**：M002 ｜ 变更管理遵循 `docs/CHANGELOG.md` 与 `ID_GOVERNANCE.md`

## v0.4.1（2026-09-10，**Frozen —— 用户批准**）—— `API-M002-007` 响应体修订（`CR-004` Applied）

- **依据**：`CR-004`（Proposed → **用户批准 2026-09-10**）；**非破坏性** —— 不新增/不删除端点，不改 Method/Path/错误语义，仅收敛为**已实现且信息更完整**的响应字段集
- **变更**：`API-M002-007` 响应体由 v0.4.0 的 `{photo_id, links:[LinkDTO], suggested_at}` 修订为**运行实现现状** `{photo_id, status, suggestions:[LinkSuggestionItem]}`，`LinkSuggestionItem = {link_id, group_subject_id, subject|null, confidence|null, source, suggested_at}`；`MODULE_API.md` DTO 约定补登两类型
- **理由**：① `links` 与 `API-M002-003`/`005` 的「已建立挂接关系」语义冲突，**建议态**用 `suggestions` 表达更准确；② 实现逐条返回 `confidence`/`suggested_at`，前端「采纳 / 驳回 / 重试建议」界面需要这些字段；③ 前端 `Task-009` 已按实现取用，**前后端运行一致**，本 CR 属「文档追平实现」
- **影响面**：前端**零返工**；后端**零代码改动**（仅文档）；测试无需新增；`API-M002-007` 无其他消费方
- **落地**：`MODULE_API.md`（§API-M002-007 + DTO 约定）、`API_REGISTRY.md`（版本列 → v0.4.1，状态保持 Active）、`MODULE_REGISTRY.md`（M002 契约版本 → v0.4.1）、`MODULE_CONTRACT.md`（版本 + 签署区）、`PROJECT_STATUS.md`/`CHANGELOG.md`/`INDEX.md`/`AGENT_REGISTRY.md`（顶层 v0.20.0）
- **契约准确性核实（PM 读码）**：`backend/app/modules/m002/schemas.py`（`LinkSuggestionItemOut`/`LinkSuggestionOut`）+ `api/link_routes.py:31-65`（`retry` 查询参数、`rejected_at IS NULL` 过滤、`subject` 解析失败 → `null`、`suggested_at = link.created_at`）→ 契约文本已逐字对齐
- **契约版本**：v0.4.0 → **v0.4.1**（Frozen 面内非破坏性修订；**不涉及**数据模型 / 分层设计 / 文件面 / 测试基线，四者仍以 v0.4.0 描述为准）

## v0.4.0（2026-09-10，**Frozen —— 用户批准**）—— 链路 H 挂接重构（Task-005 交付）

- **状态**：草案 → PM 复核 APPROVED（2026-09-10，Task-005 关闭）→ **用户批准并冻结（Frozen，2026-09-10）**；③ 实施 = **`Task-008`**（已签发）；后续修改一律走 CR/ACR；依据 `CR-003`（Approved）/`ADR-013`（Accepted）/`ADR-014`（Accepted）/`REQ-002`（已精校）
- **PM 复核结论（2026-09-10）**：B1~B10 逐项落实、九件套与 `CLARIFICATION`/`REQ-002`/`REQ-010`/`ADR-013`/`ADR-014`/`DATA_MODEL` 一致、无残留「段级 1:N 归属」旧语义、零写越界；**API ID 分配登记** = `API-M002-007~011`（Draft）；**`DATA_MODEL.md` DATA-003 字段级已由 PM 同步**；③ 实施（含 `Task-006`）可启动（Contract First：② 已 APPROVED）
- 变更摘要（对应 `CHANGE-003` §2.2 B1~B10）：
  - **B1/B2 入口 `kind`**：上传批次新增 `kind`（菜单「任务」→ `task_spec`、「作业」→ `homework`，**权威在 `upload_batches.kind`**）；`photos.kind` 冗余；「作业」上传**不填任何内容**
  - **B3 挂接 N:N**：`photos.subject`/`group_no`/`suggestion_json` **Deprecated**；归属放开为 **照片 ↔ 聚合学科子任务 N:N**，新增 `photo_subject_links`（DATA-016，建议/确认/驳回）；`photos.task_id` 降为**窗口级归属**
  - **B4 门控 + 分析**：新增 `completion_analyses`（DATA-017）+ **窗口级门控**（全部挂接确认才可分析；未满足提示「待复核 N 张」）
  - **B5 链路**：异步挂接建议 → 逐张复核（accept/reject/改挂）→ 门控 → 完成分析草稿 → 家长确认 → 经 M001 `commit_conclusion` 回写 + `consumed_at` 锁定
  - **B6 降级兜底**：AI 建议失败 → 照片留 `unassigned` + **手工挂接必须保留**
  - **B7 漂移清理**：删除「M003 建议/识别」「M004 判定」前向引用（改链路 T/H + `app/core/ai/`）
  - **B8 端点**：新增 5 端点（**`API-M002-007~011`**，PM 已分配登记）；既有 001/002/003/005 修订（不新增 ID）
  - **B9 测试**：基线 112 + 新增用例设计（门控 / N:N 唯一 / 分析事务 / 消费锁定 / `migrate_links` / AI 降级）
  - **B10 回填**：九件套全部更新（含 `MODULE_FILES.md` 目标态）；`DATA_MODEL.md` DATA-003 字段级由 PM 同步
- **破坏性变更**：挂接目标段级 → N:N；完成分析上收 M002（原 M004 后置）；`photos` 三列 Deprecated；新增两表
- **兼容性**：V1 无历史生产数据，开发库直接演进（`CHANGE-003` §5）；Task-002 已交付的质检/归一/受控存储/双主体面**保持**，仅**归属段**增量改接（`ADR-014` 决议 5）

### Task-005 交付说明（供 PM 复核）

**1. B1~B10 落实对照**

| # | 修订点 | 落实位置 |
| --- | --- | --- |
| B1 | 入口 `kind`（`upload_batches.kind` 权威、`photos.kind` 冗余）+ `photos.task_id` 降窗口级 | `MODULE_DATA.md`（两表）、`MODULE_API.md`（001/002） |
| B2 | 「作业」上传不填内容 | `MODULE_CONTRACT.md` §上传入口、`MODULE_API.md` 002 注 |
| B3 | N:N 挂接 + `photos.subject`/`group_no`/`suggestion_json` Deprecated | `MODULE_DATA.md`（`photo_subject_links` + Deprecated 列）、`MODULE_API.md`（005/003） |
| B4 | `completion_analyses` + 窗口级门控 | `MODULE_DATA.md`（新表）、`MODULE_CONTRACT.md` §门控、`MODULE_API.md`（门控/分析端点） |
| B5 | 挂接与复核链路 | `MODULE_CONTRACT.md` §挂接 / §门控与分析、`MODULE_DESIGN.md`（link/gate/analysis service） |
| B6 | 降级兜底（手工挂接必须保留） | `MODULE_CONTRACT.md` §挂接、`MODULE_TEST.md`（AI 降级用例） |
| B7 | M003/M004 前向引用清理 | `MODULE_DESIGN.md`（`ai_client.py`）、`MODULE_DATA.md`（关系节）、`MODULE.md`/`MODULE_SUMMARY.md` |
| B8 | 端点 + API ID | `MODULE_API.md`（新增 5 端点 + «API ID 申请清单» M002-B1~B5，交付时 ID 留空）；**PM 已分配 = `API-M002-007~011`（2026-09-10）** |
| B9 | 测试基线 112 + 新增 | `MODULE_TEST.md`（§新增用例设计） |
| B10 | 回填九件套 + CHANGELOG + `DATA_MODEL.md` DATA-003 字段级 | 九件套全部更新；**`DATA_MODEL.md` 由 PM 同步**（本任务禁写治理文档） |

**2. 破坏性变更清单（v0.3.0 → v0.4.0）**：① 挂接目标段级 `(task_id, subject, group_no)` → N:N 聚合子任务；② `photos.subject`/`group_no`/`suggestion_json` Deprecated；③ `photos.task_id` 降窗口级；④ 新增 `upload_batches.kind`/`photos.kind`；⑤ 新增 `photo_subject_links`/`completion_analyses`；⑥ 完成分析上收 M002（原 M004，Deferred）；⑦ API-M002-005 归属操作 → 挂接复核（路径 `/associate` → `/links`）

**3. 开放项清单**

| # | 开放项 | 状态 |
| --- | --- | --- |
| 1 | 新增端点 API ID（M002-B1~B5） | **已分配（2026-09-10）** = `API-M002-007`（挂接建议查询/重试）/`008`（门控状态）/`009`（完成分析生成）/`010`（完成分析确认）/`011`（完成分析重跑），登记 `API_REGISTRY.md`（Draft） |
| 2 | `DATA_MODEL.md` DATA-003 字段级同步 | **已由 PM 同步（2026-09-10）** |
| 3 | 契约签署（用户/PM） | **已关闭（2026-09-10）**：PM 复核 APPROVED + **用户批准 → Frozen**（`MODULE_CONTRACT.md` §签署区已落款） |
| 4 | ~~M003/M004 接口边界~~ | **已闭合**（`ADR-014`：职责并入链路 T/H + `app/core/ai/`） |



## Task-008 后端实现（2026-09-10，契约版本不变仍 v0.4.0 Frozen）

- **产出**：`backend/app/modules/m002/` 全量改接至 v0.4.0（入口 `kind` → N:N 挂接 → 逐张复核 → 窗口级门控 → 完成分析 → 降级兜底）
  - **领域**：`domain/models.py`（新增 `photo_subject_links`（DATA-016）/`completion_analyses`（DATA-017）；`upload_batches.kind`、`photos.kind`；`photos.task_id` 降窗口级；`photos.subject`/`group_no`/`suggestion_json` 停写保留）；`domain/enums.py`（`BatchKind`/`LinkSource`/`LinkAction`/`AnalysisStatus`/`Conclusion`/`PhotoStatus`）；`domain/errors.py`（`LinkStateError`/`LinkTargetMissingError`/`TaskNotAcceptableError`/`SubjectPhotoLimitError`/`GateNotSatisfiedError`/`AnalysisStateError`/`AnalysisConfirmedError`/`InvalidConclusionError`/`KindMismatchError`/`M001UnavailableError`/`AiUnavailableError` 等）
  - **仓储**：新增 `repository/link_repository.py`、`repository/analysis_repository.py`；`photo_repository.py`（N:N 有效挂接过滤 / 消费锁定 / 窗口任务）、`batch_repository.py`（`kind`）
  - **客户端**：`clients/task_client.py`（M001 网关 + 可注入 port + `migrate_photo_links` 回调）、`clients/ai_client.py`（AI port：`DefaultAiClient` 委托 `app/core/ai/` + `MockAiClient`）；**删除 `clients/recognition_client.py`**（B7 前向引用清理）
  - **服务**：新增 `services/link_service.py`/`gate_service.py`/`analysis_service.py`/`suggestion_scheduler.py`；改造 `upload_service.py`（`kind` + commit 后异步建议触发，幂等、失败不影响上传）/`photo_query_service.py`/`dto_builders.py`/`undo_service.py`（删照片先清挂接行）；**删除 `services/association_service.py`/`suggestion_service.py`**（段级归属旧实现）
  - **API**：`upload_routes.py`/`photo_routes.py`（入口 `kind`；列表支持 `kind`/`group_subject_id` 过滤）；`association_routes.py`（`/photos/{id}/associate` → `/photos/{id}/links`，`accept`/`reject`/`relink`）；`link_routes.py`（**API-M002-007/008**）；`analysis_routes.py`（**API-M002-009/010/011**）
- **消费 M001 内部接口的实际方式**：仅按 `MODULE_API.md` 内部服务段签名调用（`get_student`/`get_task`/`list_groups`/`get_group`/`ensure_group`/`commit_conclusion`/`mark_in_progress`/`migrate_links_hook`），统一收敛在 `clients/task_client.py` 的**可注入 port** 后（`set_gateway`/`get_gateway`）；测试注入契约桩 `tests/m002_support.py::FakeGateway`，**不复制 M001 业务逻辑**
- **`migrate_links_hook` 对接**：M002 **模块导入期**容错调用 `register_links_migration_hook(migrate_photo_links)`（M001 未就绪时静默跳过，M001 侧仍有约定路径发现兜底）；回调 `migrate_photo_links(session, family_id, task_id, old_group_key, new_group_key)` 在 M001 事务内迁移 `photo_subject_links` 目标
- **降级兜底**：AI 建议失败/超时 → 照片保持 `unassigned`、不产生脏数据、**手工挂接路径保留**；AI 分析失败/超时/零照片 → 结论落「无法判断」
- **测试**：`tests/api/test_m002_api.py`（归属段用例改造为 N:N 复核语义）、`tests/api/test_m002_links_api.py`（新增 12：手工兜底/改挂/上限/状态门控/建议幂等与重试/窗口门控/分析 draft→确认→重跑/AI 双降级/`migrate_links`/入口 `kind`）、`tests/m002_support.py`（契约桩 + fixtures）；M002 相关 **36 passed**，全量 **204 passed**
- **待 PM 联调项**：① `app/core/ai/` 真实 Provider 端到端（当前 Mock 为最低验收线）；② M001 聚合层 `ensure_group`/`commit_conclusion`/`migrate_links_hook` 真库联调；③ 前端「照片」→「作业」改名（独立后续任务）

## Task-010 缺陷修复（2026-09-10，契约版本不变仍 v0.4.0 Frozen）—— BUG-002

- **触发**：`Task-009` 交付时由 `AGENT-M002` 以 Request-2 上报；PM 独立核实成立 → 登记 `BUG-002`（严重级别：高）→ 签发 `Task-010`
- **缺陷**：`GET /photo-gates` 无法按窗口分组（`group_key` 恒空串、跨窗口塌缩单桶）+ `POST /completion-analyses` 门控前置失效（`409 gate_not_satisfied` 不可达，仅剩前端禁用提示，可绕过）
- **根因**：`DefaultM001Gateway.get_group_subject` 消费 M001 **契约外**内部方法 `TaskGroupService.get_group_subject`，其 `TaskGroupSubjectDTO` 不含 `group_key`/`window_type`/`student_id` → `_to_subject_ref(raw, raw)` 得空串 → 门控单桶聚合；`GateService.get_gate` 按真实 key 过滤恒不匹配 → 恒 `satisfied(total=0)`。**与本文档 Task-008 条目「仅按 `MODULE_API.md` 内部服务段签名调用」的自述不符——该契约外调用即为缺口**
- **修复**（`clients/task_client.py::DefaultM001Gateway.get_group_subject`）：默认路径改走**契约内** `list_groups(session, family_id)`，经 `_to_group_ref` 回填 group 上下文；**移除**契约外 `get_group_subject` 消费（其 DTO 无法补齐 group 上下文，故不保留为加速路径）。**M001 零改动、无契约变更**；`gate_service.py` 未改（无需放宽门控）
- **测试**：新增 `tests/integration/test_m002_gate_real_m001.py`（**真机 M001 网关，不使用 `FakeGateway` 桩**，4 例：多窗口分组 / 未复核完 → 409 / 全确认 → 201 draft / 空窗口 `total=0`）；红→绿已取证（临时回退修复后 ①② 失败于 `gate=None` 与 `group_key=''`）
- **回归**：全量 `pytest -q` = **211 passed / 0 failed**（基线 207 + 新增 4）；`read_lints` = 0
- **验证证据**：见 `docs/changes/BUG-002.md` §5（含 3 类实测响应体）

## v0.3.0（2026-09-08）—— 内容级判定口径升级（Frozen 基线，当前）

- **批准冻结（2026-09-08）**：用户批准 v0.3.0 草案（MODULE_CONTRACT 签署区）→ **Frozen**；Task-002 签发（AGENT-M002 Active）进入编码。
- 依据：v0.9.0 用户批准包（`CR-001`/`ACR-001`/`CR-002`/`ACR-002` 均 Approved；ADR-010/011 Accepted，ADR-006/007 Superseded 生效）；PD-017~024（布置登记拍照识别、内容级主客观全判、真实三方默认、报告复核定稿）
- 变更摘要：
  - **完成程度口径升级**：移除 v0.2.0"完成程度 = 学科作业段照片覆盖二值化"——完成程度与对错改由**内容级判定链**（M003 内容识别 + M004 逐题对齐判定，ADR-010）回写；M002 职责边界收敛为 采集/质检/归一/归属/证据供给（R4）
  - **AI 执行策略**：归属建议 Provider 按 ADR-011（真实三方默认，Mock 测试桩/离线降级，`mock-*` 标注）；M002 本地质检/归一仍纯本地（R5）
  - **证据消费**：M002 供给"已 assigned 学科作业段照片证据集 + 归属/批次元数据"，识别消费 `mark_consumed` 保留（证据锁定）；完成度/判定结果字段归 DATA-004/005（M003/M004）（R6）
- 保持不变：先采后认归属状态机、质检规格 D1/D4、预处理 D2、采集补全 D5~D8、两级主体授权、数量上限、图片存储布局
- 前置批准：`CR-001`/`ACR-001`/`CR-002`/`ACR-002` 均已批准（本版不再依赖 Open 项）
- 数据：表结构不变（无判定结果字段写入 M002；归属三元组/建议/质检快照原样）
- API：API-M002-001~006 契约语义不变（消费方接口注释更新：`count_assigned` 用途注明判定链证据）
- 副作用：M002 未编码（九件套同步 v0.3.0）；相关顶层文档状态同步见 `PROJECT_STATUS.md`/`MODULE_REGISTRY.md`

## Task-002 后端实现（2026-09-09，契约版本不变仍 v0.3.0 Frozen）

- **产出**：`backend/app/modules/m002/` 全量后端编码完成（domain/repository/services/api/clients/config/schemas），路由已注册（API-M002-001~006 对齐契约语义）
- **实现要点**：上传两阶段（先文件后行，失败清理）；归属状态机 `unassigned→assigned`/`suggested`/`rejected`；首张 assigned 幂等触发任务 in_progress（经 `clients/task_client.py` 只读桥接 M001，越权转 404）；`services/locks.py` 键控互斥（D8）
- **质检 v1.0 落地**：模糊 = 浮点 4-邻域拉普拉斯方差（新增 `quality_blur_probe_side=320`，规避字节裁剪）；过暗/过亮/倾斜/遮挡/页角裁切 = 确定性本地规则；阈值全部配置化
- **测试**：新增 `tests/unit/test_m002_image_processing.py`（11）与 `tests/api/test_m002_api.py`（12，含双主体越权矩阵/归属状态机/失败无残留）；含 M001 既有回归共 **112 tests 通过**
- **文档回填**：`MODULE_FILES.md`（实况）、`MODULE_SUMMARY.md`（状态 + D8 锁语义 + 自检记录）
- 备注：属"九件套同步 v0.3.0"后补；不构成契约变更

## v0.2.0（2026-09-08）—— 先采后认重构（Draft，被 v0.3.0 承接，历史）

- 依据：M002 契约完整性审查（用户逐项确认 PD-014/PD-015/PD-016 + D5~D8）
- 变更摘要：
  - 任务语义：task = 多学科作业登记单容器 + 学科作业段（`task_items.group_no`）→ 依赖 `CR-001`（M001，Open）
  - 采集模型：**先采后认** —— 上传按"上传批次"不预选任务/学科 → 照片 `unassigned` → AI（M003）建议 `suggested` → 家长/学生确认 `assigned(到学科作业段)` 或 `rejected`；首次 assigned 触发任务 `in_progress`（幂等）；完成程度 = 学科作业段照片覆盖二值化
  - 身份主体：两级主体（家庭账号家长 + 学生子账号）→ 依赖 `ACR-001`/ADR-009（Open）
  - 采集补全：D5 数量上限（批次 50 / 任务 assigned 200）；D6 页序服务端自增；D7 未消费照片可撤销；D8 并发串行化 + 409
- 数据：`upload_batches` + `photos`（归属状态机）取代 v0.1.0 的 `submissions`/`submission_images` 模型
- API：API-M002-001~006 重构（原 v0.1.0 四接口语义废弃）
- 行为：`mark_in_progress` 触发点由"首张质检通过入库"（D3v0.1）改为"首次照片 assigned"（新语义）
- 副作用：未产生代码变更（M002 未编码）；同步登记：REQUIREMENTS/REQ-001~003 精校、RISK-006/007、ADR-009、CR-001、ACR-001

## v0.1.0（2026-09-08）—— 初版草案（**废弃**，语义被 v0.2.0 取代）

- 初版九件套（submission 直绑任务单学科模型：POST `/submission-images` 等 API-M002-001~004、D1~D4 决策）。因完整性审查确认真实产品闭环（多学科登记单 + 先采后认 + 学生自主/家长兜底）而整体重构，v0.1.0 不进入 Frozen
- 保留到 v0.2.0 的既有结论：D1（本地规则质检）、D2（轻量归一）、D4（不合格不入库 + 逐图报告）
