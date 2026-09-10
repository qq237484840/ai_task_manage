# Task-008 任务书 —— M002 实施（入口 `kind` + N:N 挂接 + 逐张复核 + 窗口级门控 + 完成分析）

- **Task ID**：Task-008 ｜ **Agent**：`AGENT-M002` ｜ **Module**：M002（作业图片采集与挂接）
- **签发**：Project Master，2026-09-10 ｜ **状态**：**已交付 → PM 复核 APPROVED（2026-09-10）** ｜ **Kind**：**实施（编码；Task-002 冻结段增量改接）**（后续缺陷修复见 `BUG-002` / `Task-010`）
- **启动前置（Contract First，硬约束）**：M002 契约 **v0.4.0 Frozen（用户批准 2026-09-10）** + 上游 M001 契约 **v0.2.0 Frozen** —— **前置已于 2026-09-10 满足**。契约未定稿前本任务**不得落地任何代码**。
- **与 Task-002 的关系（PD-029 / `ADR-014` 决议 5）**：Task-002 采用「**部分冻结 + 定稿后增量改接**」—— 已交付的**质检 / 归一 / 受控存储 / 受控取图 / 双主体 API** 保持；**「归属/挂接」段自本任务起按契约 v0.4.0 增量改接**（返工面限归属段）。Task-002 未收尾部分随本任务合并推进。
- **前置依据**：`docs/modules/M002/MODULE_CONTRACT.md`（v0.4.0 Frozen，权威）、`MODULE_DATA.md` / `MODULE_API.md` / `MODULE_DESIGN.md` / `MODULE_TEST.md`（同版本）、`docs/modules/M001/MODULE_API.md`（聚合层内部接口）、`docs/adr/ADR-013.md`、`docs/adr/ADR-014.md`、`docs/requirements/CLARIFICATION-2026-09-10.md`、`docs/requirements/REQ-002.md`、`docs/DATA_MODEL.md`（DATA-003 修订 + DATA-016/017）、`docs/changes/CHANGE-003.md` §2.2 B1~B10
- **任务书登记**：`docs/AGENT_REGISTRY.md`（`AGENT-M002` 行）｜ **验收**：`CHANGE-003` ③ 里程碑（域 B/C）+ `MODULE_TEST.md` 用例设计 + 本任务 §6 DoD

## 1. Objective（目标）

按 `CHANGE-003` §3 推进 **M002 归属段重构（链路 H）**：上传入口按**菜单**分「任务 / 作业」（`kind` 权威落在 `upload_batches.kind`），归属由**段级 1:N** 放开为 **照片 ↔ 聚合学科子任务 N:N**，并落地 **异步挂接建议 → 逐张复核 → 窗口级门控 → 完成分析（草稿）→ 家长确认** 全链路与**降级兜底**。

## 2. Requirements（权威源，只读，禁止复制改写）

- `docs/modules/M002/**`（九件套 v0.4.0 Frozen）—— **本任务的唯一契约来源**
- `docs/modules/M001/MODULE_API.md`（消费的聚合层接口：`get_student` / `get_task` / `list_groups` / `get_group` / `ensure_group` / `commit_conclusion`（DATA-013 唯一写入口）/ `mark_in_progress`）
- `docs/adr/ADR-011.md`（真实三方默认 / Mock 降级）、`docs/adr/ADR-003.md`（可观察依据 / 不武断 / `无法判断` 出口）
- `docs/DATA_MODEL.md`（DATA-003 修订；DATA-016 `photo_subject_links`；DATA-017 `completion_analyses`）
- 现有基座：`backend/app/modules/m002/**`（v0.3.0 实况）、`backend/app/core/config.py`、`backend/tests/`（112 基线）

## 3. Scope（范围）

### 3.1 本任务交付

| # | 交付 | 说明 |
| --- | --- | --- |
| 1 | **入口 `kind`（B1/B2）** | `upload_batches` 新增 `kind`（`task_spec\|homework`）并冗余至 `photos.kind`；**由入口（菜单）决定，不由家长选**；「作业」上传**不填任何内容**；上传接口与表**公用** |
| 2 | **N:N 挂接（B3）** | 新增 `photo_subject_links`（DATA-016，`UNIQUE(photo_id, group_subject_id)`，`source(ai\|manual)` / `confidence` / `confirmed_at` / `rejected_at`）；**归属目标 = `task_group_subjects`（聚合学科子任务）**；`photos.task_id` 降为**窗口级归属**；`photos.subject` / `group_no` / `suggestion_json` **Deprecated（不写）** |
| 3 | **挂接建议（异步）** | 上传成功即**异步触发**（经 `app/core/ai/`，**Mock 可解阻**）；**幂等**（只处理未挂接照片）；建议态由 `links` 承载，不再写 `suggestion_json` |
| 4 | **逐张复核（B5）** | 逐张照片 `accept / reject / 改挂`（`API-M002-005` 归属操作改挂接复核，路径 `/associate` → `/links`）；子任务汇总视图；**手工挂接兜底必须保留** |
| 5 | **窗口级门控（B4）** | 新增 `completion_analyses`（DATA-017，`UNIQUE(group_subject_id, run_no)`）；门控 = **该窗口全部照片挂接确认后才分析**，未确认完提示「待复核 N 张」 |
| 6 | **完成分析（B4/B5）** | 生成（draft）→ 家长**确认**（confirmed）→ **重跑**（版本递增）；结论 = 完成 / 部分完成 / 未完成 / **无法判断** + 依据照片 + 置信度；**上收为 M002 职责**（原 M004，Deferred） |
| 7 | **降级兜底（B6）** | LLM 超时 / 返回不合规 → 照片保持 `unassigned`，**保留手工挂接**；不得产生脏数据 |
| 8 | **前向引用清理（B7）** | 契约/代码中 `M003`/`M004` 引用改为**链路 T / 链路 H + `app/core/ai/`**（`clients/recognition_client.py` → `ai_client.py` 等） |
| 9 | **API 面** | 修订 `API-M002-001`（加 `kind`）/`002`（异步建议）/`003`（`links` 替代 `assignment`/`suggestion`）/`005`（挂接复核）；**新增 `API-M002-007~011`**（挂接建议查询/重试 / 门控状态 / 完成分析生成 / 确认 / 重跑）—— ID 已由 PM 分配登记（Draft → 本任务实施后转 Active） |
| 10 | **测试** | 既有 **112 项不回归**；新增用例按 `MODULE_TEST.md` §新增用例设计（`kind` 分入口 / N:N 挂接 / 逐张复核 / 门控 / 完成分析确认与重跑 / AI 降级兜底 / 双主体鉴权） |

### 3.2 Allowed-Files（可写）

- `backend/app/modules/m002/**`（唯一业务写区）
- `backend/app/api/v1/**`（**仅 M002 相关路由**：photos / upload_batches / links / gates / completion-analyses 等）
- `backend/tests/**`（新增 M002 用例，禁止破坏既有用例）
- `docs/modules/M002/MODULE_CHANGELOG.md`（实施完成后回填版本历史）

### 3.3 Forbidden-Files / 边界

- **禁止改动 M001 业务代码/契约**（`backend/app/modules/m001/**`、`docs/modules/M001/**`）—— M001 侧由 `Task-007` 负责；接口需求以 **Request** 报 PM
- **禁止越界修改治理层文档**（Registry / ADR / CHANGE / REQUIREMENTS / ROADMAP / PROJECT_STATUS / CHANGELOG / INDEX / DATA_MODEL / CONFIGURATION / API_REGISTRY）
- 禁止在 `app/core/ai/` 内写代码（`AGENT-AI`/`Task-006` 写区）；本模块经内部接口调用
- 禁止实现 V2 功能（六维评分 / 评语 / 报告 / 假期计划与评估）；**禁止内容项级判定**（V1 判定粒度 = 聚合子任务(学科)级）
- 禁止自行分配 API / DATA / Task ID；禁止跳过契约新增字段/端点
- **禁止前端改动**：本任务**不含**前端「照片」改名「作业」与周次/周末分组展示（属后续独立任务，PM 另签发）

## 4. Dependencies（前置就绪条件）

- **硬前置**：M002 契约 **v0.4.0 Frozen**（✅）+ M001 契约 **v0.2.0 Frozen**（✅，提供聚合层内部接口）
- **并行**：`Task-006`（`app/core/ai/`）—— **Mock 模式即可解阻**挂接建议与完成分析
- **上游**：`Task-007`（M001 聚合层 `ensure_group` / `commit_conclusion` / `migrate_links_hook`）—— 若尚未就绪，先按契约签名以 **Mock/契约桩** 联调，禁止自行定义 M001 侧契约

## 5. Expected Deliverables（完成即提交 PM 复核）

- 代码按 §3.1 落地，lint 无错误；`backend/.venv` 下 `pytest` **全绿（既有 112 + 新增）**
- **归属演进实证**：`photos.subject`/`group_no`/`suggestion_json` 停止写入后无回归；`photo_subject_links` 唯一键约束生效（有测试）
- **全链路实证**（Mock Provider）：上传作业（`kind=homework`）→ 异步建议 → 逐张复核 → 门控满足 → 完成分析 draft → 家长确认 → 重跑
- **降级实证**：三方不可用 / 返回不合规两种情形下照片保持 `unassigned` 且手工挂接可用
- 提交 PM 的 Request 清单（如需配置项 / M001 内部接口变更）
- 完成后：提交 PM 按本任务 §6 DoD 复核；**回填 `MODULE_CHANGELOG.md` 版本历史**

## 6. Acceptance Criteria（DoD，AGENT_GUIDE §6）

- [ ] `kind` 由入口决定并权威落 `upload_batches.kind`；「任务」/「作业」两入口用例通过；**作业上传无内容字段**
- [ ] `photo_subject_links` 支持 **1 照片 → 多子任务 / 1 子任务 → 多照片**（N:N 用例通过）；`photos.task_id` 仅作窗口级归属
- [ ] 异步挂接建议**幂等**（重复触发不重复建链）+ 无建议时照片 `unassigned` 且可手工挂接
- [ ] 逐张复核 `accept` / `reject` / 改挂 三条路径均正确写入 `links`（含 `source=manual`）
- [ ] 窗口级门控：未确认完时分析被拒并返回「待复核 N 张」；门控满足后分析可生成
- [ ] `completion_analyses`：draft → confirmed 流程 + **重跑版本递增**（`run_no` 唯一）正确；结论含依据照片与置信度，`无法判断` 出口可用
- [ ] **降级兜底**：LLM 超时/不合规不产生脏数据（有测试）
- [ ] `API-M002-001/002/003/005` 修订与 `API-M002-007~011` 新增实现与契约一致（含双主体鉴权 404/403 语义）
- [ ] `M003`/`M004` 前向引用 = 0（代码 + 本模块文档）；未越权改动 M001 / 治理文档 / `app/core/ai/`
- [ ] 既有 **112 项不回归**；`MODULE_TEST.md` §新增用例设计全部落地通过
- [ ] PM 复核 APPROVED → Task-008 关闭 → M002 进入**可验收态**（域 B/C 里程碑）

> 注：本任务**不含**前端改名与周次/周末分组展示、跨模块端到端验收（`CHANGE-003` ④ 验收剧本 7 条，含第 7 条浏览器级）、真实三方密钥联调（Mock 为最低验收线，`ADR-011`）。
