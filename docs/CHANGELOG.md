# CHANGELOG —— 项目变更历史

> 维护：Project Master。语义化版本（主.次.修订）。
> 模块级变更进入各模块 `MODULE_CHANGELOG.md`；重大变更（CHANGE-nnn）另存 `docs/changes/`。

## v0.22.0 —— 2026-09-10

### ④ 验收收口：`Task-014` 去替身复审经 **PM 独立复核成立** → `BUG-003`/`BUG-004` **Verified** → `CHANGE-003` **关闭（Closed）**

- **`Task-014`（AGENT-M002，④ 去替身复审）交付**：
  - **去替身**：移除 `backend/tests/e2e/test_acceptance_scenarios.py::m002_ai_port` fixture（含 `MockAiClient` + `set_ai_client` 注入；全文引用 = 0），两例边界用例（`test_boundary_gate_not_satisfied_409_api_level` / `test_boundary_analysis_confirmed_is_terminal_api_level`）改走 **`app/core/ai` 真实装配路径**，新增判别力断言（`status == "suggested"` + `suggestions` 非空 + `group_subject_id == [gs]`）。
  - **`TD-003` 清理**：`modules/m002/clients/task_client.py::list_groups` 的 `except TypeError` 签名兼容垫片**删除**，改按 `M001 v0.2.0 Frozen` 契约直调；死代码证明 = 真机门控集成 10 例 + 上层 40+ 例 0 触发。
  - **剧本 4/5 + 浏览器级**：剧本 4 图片源 `placeholder`/`contents==[]` 边界**未放宽**；剧本 5 手工挂接未受影响；`.e2e/acceptance.mjs` 重写为「3 张照片经真实 AI 通路 → UI 建议 + 采纳入口 → 逐张采纳 → 门控满足 → 生成草稿 → 家长确认」，**18/18 PASS**（`model: "mock-vision"`）。
  - **去替身审计**：10 条清单（`m002_ai_port` 删除；`MockAiClient` 协议面保留未注入；`FakeGateway` 残留 0；`DefaultAiClient` Mock 兜底属 `ADR-011` 真实装配路径）；证据分域（浏览器级 / API 级 / 服务级）标注。
- **PM 独立复核（未采信自述，全部亲手复现）**：

| 复验项 | 命令 | 原文结论 |
| --- | --- | --- |
| 判别力（红） | `AT_AI_PROVIDER_MODE=real` + `AT_AI_ALLOW_MOCK_FALLBACK=false` → 两例边界 | **`FF`**；`assert 'unassigned' == 'suggested'`（`suggestions=[]`）→ **`RED_EXIT=1`** |
| 判别力（绿） | 还原 `auto/true` → 边界 2 例 + 剧本 4/5 | **`....` 4 passed** → **`GREEN_EXIT=0`** = 真红真绿（非无脑通过） |
| 全量回归 | `pytest --tb=no -q --junitxml` | **`tests=237 failures=0 errors=0 skipped=0`**、`EXIT=0`（与 `Task-013` 收口基线一致，**未删减用例**） |
| 浏览器级 | `.e2e/browser_evidence.json` | **18 项全 `true` / 0 项 `false`**；含 `mock-vision` 显著标注与「采纳 6 次全 200 → `assigned×3` → 门控满足 → 草稿 `draft`」链 |
| 写区双证 | `git status --porcelain` + mtime 审计 | 两处改动均 `??`（未跟踪写区）；Forbidden 区 mtime **全部早于写区起点**（`mock.py` 20:15:47 / `task_parser.py` 20:11:26 / `BUG-004.md` 20:24:44 等） |

- **PM 裁决**：① `BUG-003` / `BUG-004` → **`Verified`**；② **④ 判达成 → `CHANGE-003` 收口（Closed）**；③ **同文件 `getattr(..., None) + raise M001UnavailableError` 存在性探针不立 `TD-004`**（与「签名兼容垫片」语义不同，不掩盖契约缺口）。
- **已知边界（不阻断）**：真实三方 AI Provider **无密钥**，全部 AI 通路证据为 **Mock Provider（`mock=True`，显著标注）**，非三方联调。
- 修订：`docs/changes/BUG-003.md` / `BUG-004.md`（→ **Verified**）、`docs/changes/CHANGE-003.md`（→ **Closed** + DoD 勾选）、`docs/agents/Task-014.md`（§5 PM 复核）、`docs/TECH_DEBT.md`（`TD-003` → Closed）、`docs/PROJECT_STATUS.md`（→ **v0.22.0**；M002 → Stable）、`docs/CHANGELOG.md`、`docs/INDEX.md`

## v0.21.0 —— 2026-09-10

### ④ 验收已执行（`Task-011`）+ PM 独立复核 = **条件达成（不通过收口）**；签发 `Task-012`/`Task-013` 修复 AI 通路缺陷

- **`Task-011`（AGENT-M002，阶段 ④ 验收）交付**：`CLARIFICATION` §5 **剧本 7 条**逐条取证（剧本 7 **浏览器级**：任务列表页 `GET /api/v1/tasks?...` → **200**，不再 422）+ 全系统回归 + 边界抽查（跨家庭/越权 `404`、`409 gate_not_satisfied`、已确认终态 `409`）+ 只读边界自证。
  - 新增验收资产：`backend/tests/e2e/`（`test_acceptance_scenarios.py` 11 例 + `test_acceptance_ai_wiring.py` 5 例）+ `.e2e/`（`seed.py`/`acceptance.mjs`/`browser_evidence.json`/`shots/*.png`）+ 任务书 §7 过程记录。
- **PM 独立复核（未采信自述，全部复现）**：

| 复验项 | 命令 | 原文结论 |
| --- | --- | --- |
| 全量回归 | `pytest -q -rxX` | `exit 0`；**227** 点（72+72+72+11）；**2 xfail**（= `BUG-003`/`BUG-004`） |
| 前端类型检查 | `npx vue-tsc --noEmit -p tsconfig.app.json` | **TSC_EXIT=0** |
| 前端构建 | `npm run build` | **BUILD_EXIT=0**（`389 modules transformed`、`✓ built in 3.23s`） |
| 只读边界（diff） | `git diff --name-only -- backend/app frontend/src` | 8 文件，**全属 `Task-006~010` 既有未提交基线** |
| 只读边界（mtime，决定性） | `Where LastWriteTime -gt "2026-09-10 19:20"` | **COUNT=0**（最新 18:02:38 / 17:55:15） |
| 缺陷根因 | PM 读码 | `BUG-003`/`BUG-004` **均属实 → Confirmed** |

- **PM 裁决 = ④ 条件达成（不通过收口）**，3 项缺口：
  1. **`BUG-004`（高，Confirmed）**：M001 `default_parser` 以位置参数调用 `app.core.ai.parse_task_spec`（`sources` 为 keyword-only）→ `TypeError` 被 `except Exception: pass` **静默吞掉** → **链路 T 核心 AI 解析通路不可达**（剧本 4 的 `spec_status="parsed"` 实为**本地启发式兜底**产出，**AI 语义未达成**）；PM 另确认异常**无日志**、降级**不可观测**。
  2. **`BUG-003`（中，Confirmed）**：`MockVisionProvider` 读 `context["candidate_subjects"]`，而 `AIService` 注入 `context["candidates"]`（prompt 亦为 `$candidates`）→ **Mock 挂接建议恒空**（剧本 5/6 的「AI 给出挂接建议」未发生，浏览器级实际走**手工挂接**；`409 gate_not_satisfied` 边界仅能经 M002 **AI 端口替身**触达）。
  3. **真实三方无密钥 → 未覆盖**（已知边界；`ADR-011` Mock 为最低验收线，不阻断 ④，但须在收口结论标注）。
- **采信部分**：`.e2e/acceptance.mjs` 为**真实浏览器级**（Edge + `playwright-core` 驱动真实 uvicorn 托管的 `frontend/dist`，Network + 4 截图 + `browser_evidence.json` 66.6 KB）；剧本 1/2/3 的日界 4 点规则由**生产 `DefaultWindowResolver`** 对真实时间戳证明（`FixedResolver` 注入口径已在 docstring 声明）。
- **签发修复任务（并行，写区不重叠）**：
  - **`Task-012`**（`AGENT-M001`）：`BUG-004` 修复 —— 关键字调用 + `SourceInput` 转换 + 降级**可观测**（`logger.warning`）+ 以 `ai_call_records` 证明 AI 真跑；写区 = `modules/m001/services/task_parser.py` + M001 侧用例。
  - **`Task-013`**（`AGENT-AI`）：`BUG-003` 修复 —— Mock 读 key 对齐 `candidates` + 新增**经 `AIService` 装配路径**的防漂移用例 + 整改「直调 Mock + 手写 context」既有用例（本次漏检根因）；写区 = `app/core/ai/**` + AI 层用例。
- **收口路径**：修复经 PM 复核 APPROVED → 签发 **`Task-014`**（`AGENT-M002`）**去替身复审**（剧本 4/5 AI 真机 + `409` 边界去替身 + 浏览器级复跑）→ `BUG-003`/`BUG-004` → **Verified** → ④ 判**达成** → `CHANGE-003` 收口。
- 修订：`docs/agents/Task-011.md`（§8 PM 复核结论）、`docs/agents/Task-012.md`（**新建**）、`docs/agents/Task-013.md`（**新建**）、`docs/changes/BUG-003.md` / `BUG-004.md`（→ **Confirmed** + §7 PM 复核 + 派单）、`docs/changes/CHANGE-003.md`（④ 行 + DoD 注）、`docs/PROJECT_STATUS.md`（→ **v0.21.0**）、`docs/CHANGELOG.md`、`docs/INDEX.md`、`docs/AGENT_REGISTRY.md`

## v0.20.0 —— 2026-09-10

### `CR-004` 经用户批准 → **Applied**（M002 契约 v0.4.0 → v0.4.1）；签发 `Task-011`（阶段 ④ 验收）

- **CR-004 Applied（用户批准 2026-09-10）**：`API-M002-007` 响应体以**运行实现为准**修订 —— **v0.4.0** `{photo_id, links:[LinkDTO], suggested_at}` → **v0.4.1** `{photo_id, status, suggestions:[LinkSuggestionItem]}`，其中 `LinkSuggestionItem = {link_id, group_subject_id, subject|null, confidence|null, source(ai|manual), suggested_at}`。
  - **性质 = 非破坏性**：不新增/不删除端点，不改 Method/Path/错误语义（`401`/`404`/`500` 不变）；`API-M002-007` 状态保持 **Active**，端点在册不变。
  - **理由**：① `links` 与 `API-M002-003`/`005` 的「已建立挂接关系」语义冲突，**建议态**用 `suggestions` 更准确；② 实现逐条返回 `confidence`/`suggested_at`，「采纳 / 驳回 / 重试建议」界面需要；③ 前端 `Task-009` 已按实现取用、**前后端运行一致**，本 CR 属「文档追平实现」。
  - **影响面**：**前端零返工、后端零代码改动**（仅文档）；测试无需新增；无其他消费方。
  - **PM 读码核实（未采信 CR 描述）**：`backend/app/modules/m002/schemas.py`（`LinkSuggestionItemOut`/`LinkSuggestionOut`）+ `api/link_routes.py:31-65` —— `retry` 查询参数缺省 `false`；返回 `rejected_at IS NULL` 的挂接项（含 AI 未确认建议、手工挂接、已确认项）；`subject` 经 M001 契约内接口解析、失败为 `null`；`suggested_at = link.created_at`。契约文本已逐字对齐，并补登 `LinkSuggestionItem`/`LinkSuggestionResult` DTO 约定。
  - **落地（9 处文档）**：`modules/M002/MODULE_API.md`（版本行 → v0.4.1 + §API-M002-007 + DTO 约定）、`MODULE_CHANGELOG.md`（新增 v0.4.1 条目）、`MODULE_CONTRACT.md`（版本 + 签署区 v0.4.1 说明）、`MODULE.md`/`MODULE_SUMMARY.md`（状态与版本）、`API_REGISTRY.md`（`API-M002-007` 版本列 → v0.4.1 + 头部变更记录）、`MODULE_REGISTRY.md`（M002 契约版本 → v0.4.1 Frozen；③ 实施状态收口）、顶层 `PROJECT_STATUS.md`/`CHANGELOG.md`/`INDEX.md`/`AGENT_REGISTRY.md`。
  - **范围声明**：`MODULE_DATA`/`MODULE_DESIGN`/`MODULE_FILES`/`MODULE_TEST` 仍以模块基线 **v0.4.0** 描述 —— 本 CR **不涉**数据模型 / 分层设计 / 文件面 / 测试基线。
- **签发 `Task-011`（AGENT-M002，`Kind` = 验收）**：**阶段 ④** = `CLARIFICATION` §5 **验收剧本 7 条逐项验收**（含**浏览器级**）+ **全系统回归**（域 A/B/C；Mock 必跑 / 真实三方双跑；`vue-tsc` 0 error + `npm run build` EXIT=0 + 生产产物经 FastAPI 托管可访问）。
  - **只读边界（硬约束）**：`backend/app/**` 与 `frontend/src/**` **零改动** —— 发现偏差 → 登记 `BUG-00x` 上报 PM，**不得自行修复**；允许新增验收脚本/证据（建议 `backend/tests/e2e/`）。
  - `TD-001`/`TD-002` **不属**本任务：观察记录即可，不影响 ④ 判定。
- 修订：`docs/modules/M002/*`（5 件）、`docs/API_REGISTRY.md`、`docs/MODULE_REGISTRY.md`、`docs/changes/CR-004.md`（→ **Applied** + §落地记录）、`docs/agents/Task-011.md`（**新建**）、`docs/AGENT_REGISTRY.md`、`docs/PROJECT_STATUS.md`、`docs/CHANGELOG.md`、`docs/INDEX.md`

## v0.19.0 —— 2026-09-10

### BUG-002（门控链路）修复交付 + PM 复核 APPROVED → Verified；Task-010 关闭；CHANGE-003 ③ 收口（④ 可启动）

- **修复点（单点最小改动；M001 零改动 / 无契约变更）**：`DefaultM001Gateway.get_group_subject` 默认路径改走**契约内** `list_groups(session, family_id)`，经 `_to_group_ref` 由 `TaskGroupDTO` 回填 `group_key`/`window_type`/`student_id`/`group_id`/`category`；**移除**对 M001 契约外内部方法 `TaskGroupService.get_group_subject` 的消费（其 `TaskGroupSubjectDTO` 物理上不含 group 上下文，无法补齐，故不保留为加速路径）。`gate_service.py` **未改**（未放宽门控）。
- **门控恢复后端强制**：`GET /photo-gates` 按真实 `group_key` 分桶（多窗口 ≥2 条、`?group_key=` 精确命中、计数正确）；`POST /completion-analyses` 存在未确认挂接 → **`409 gate_not_satisfied` 实测可达**；`API-M002-005` 响应 `gate` 由 `null` → 真实窗口 key 与计数；无挂接窗口保持 `satisfied(total=0)` 契约语义。
- **测试补强（消除 `FakeGateway` 桩盲区 —— 本次缺陷直接成因）**：新增 `backend/tests/integration/test_m002_gate_real_m001.py`（**真机 M001 网关**，4 例：多窗口分组 / 未复核完 → 409 / 全确认 → 201 draft / 空窗口语义）；**红→绿取证**（临时回退修复后 ①② 失败于 `gate=None` 与 `group_key=''`，还原后 4/4 绿）。
- **PM 独立复验（未采信自述）**：新增用例 **4 passed**；全量 `pytest` = **211 passed / 0 failed**（基线 207 + 4，exit 0）；`git diff --name-only -- backend` 与 Task-009 开工前完全一致，且 **mtime 审计**证明 `m001/**` 无 Task-010 期间写入、`frontend/src/**` 最新写入 17:55（早于起始 18:02）；检索 `TEMP-`/`CAP_` 残留 **0**；`read_lints` = **0**；测试代码审读确认全程真实网关无桩。
- **执行方两条决策说明均获认可**：① 不保留契约外加速路径（无法补齐 group 上下文，符合 `BUG-002` §3.2）；② 不适用 `get_group` 直取（M002 侧无 `group_id`）。
- **新增技术债并启用 `docs/TECH_DEBT.md`**：**`TD-001`**（`get_group_subject` 由直取退化为按 family 全量 `list_groups` 扫描，展示链路 N+1 放大；`gate_service` 已有 `ref_cache`，V1 规模可接受，规模化前建议批量建映射）、**`TD-002`**（契约未暴露 `window_task_id`/`task_status` → `API-M002-005` 的 `task_id` 恒 `null`、M001 窗口任务 `mark_in_progress` 不触发）。
- **状态流转**：`BUG-002` → **Verified**；`Task-010` 关闭；`CHANGE-003` ③ **前端 + 后端修复项全部关闭 → ④ 验收剧本 7 条解除前置阻塞、可启动**；`CR-004` 仍为 **Proposed（待用户批准）**，与本修复无耦合。
- 修订：`docs/agents/Task-010.md`（关闭 + §7 复核结论）、`docs/changes/BUG-002.md`（→ Verified）、`docs/TECH_DEBT.md`（**新建**）、`docs/modules/M002/MODULE_CHANGELOG.md`（执行方追加 Task-010 条目）、`docs/AGENT_REGISTRY.md`、`docs/changes/CHANGE-003.md`、`docs/PROJECT_STATUS.md`、`docs/CHANGELOG.md`、`docs/INDEX.md`

## v0.18.0 —— 2026-09-10

### Task-009（前端「作业」域迁移）交付并 PM 复核 APPROVED + 门控链路缺陷（BUG-002）确认与修复签发（Task-010）+ CR-004 提案

- **`Task-009` 交付 → PM 复核 APPROVED（2026-09-10）**：前端照片域迁移为**作业域**，交付 8 文件（7 改 + 新增 `frontend/src/components/PhotoCard.vue`）——
  - 菜单「照片」→「**作业**」（`BottomNav.vue` + 页面标题）；**路由 `path` 保留 `/photos`**（`name` 改 `homework`/`homework-upload`，深链不破坏）
  - `api/index.ts` + `api/types.ts` 补齐 M002 v0.4.0 六个调用面（`POST /photos/{id}/links`、`GET …/link-suggestions`、`GET /photo-gates`、`POST /completion-analyses` + `/confirmation` + `/rerun`；`GET /photos` 参数补 `kind`/`group_subject_id`），**删除死代码 `associatePhoto` 及段级类型（运行期 404 根因）**
  - `PhotoListView.vue` 重做：**按周次/窗口分组**（显示名取 `task-groups.display_name`：「第 N 周」/「周末作业」）+ **逐张复核三路径**（accept/reject/relink，目标改 `group_subject_id`，**彻底停读已废弃 `task_items`**）+ 手工挂接兜底保留（B6）+ **门控**（待复核 N 张）+ **完成分析**（draft → 确认可校正 → 重跑仅 draft）
- **PM 独立复验（未采信自述）**：`vue-tsc --noEmit -p tsconfig.app.json` = **0 error**；`npm run build` = **EXIT=0**；全前端 `associate` / `task_items` 命中 = **0**；`git diff --name-only -- backend` **与开工前完全一致**（本任务未新增/修改任何后端文件）
- **`BUG-002` 确认（严重级别：高）**：`GET /photo-gates` **无法按窗口分组**（`group_key` 恒空 → 全部照片落单桶）+ `POST /completion-analyses` **门控前置失效**（`409 gate_not_satisfied` 不可达）+ `LinkReviewOut.gate` 错误。**根因（PM 独立核实）**：M002 网关 `task_client.py:290` 消费 M001 **契约外**接口 `get_group_subject`（M001 v0.2.0 内部服务接口表未登记该接口），其 `TaskGroupSubjectDTO` **不含** `group_key`/`window_type`/`student_id`（这些仅在 `TaskGroupDTO` 上）→ `_to_subject_ref(raw, raw)` 得空串 → `gate_service` 单桶聚合、`get_gate(真实 key)` 恒不匹配。既有单测用 `FakeGateway` 桩（完整 `GroupSubjectRef`）**未覆盖真机 M001**，故盲区长期存在。**前端 `localGate` 仅展示层兜底，不构成强制**
- **签发 `Task-010`（AGENT-M002）**：门控链路修复 + 测试补强 —— 默认路径改走**契约内接口**（`list_groups` / `get_group -> TaskGroupDTO`）回填 group 上下文；补 **真机 M001↔M002 集成用例 ≥3**（弃 `FakeGateway` 桩）；回归 **≥210 passed / 0 failed**（基线 207 不退化）；**`backend/app/modules/m001/**` 与 `frontend/**` 只读、契约文本禁改**。**该任务为 ④ 验收必要前置**
- **`CR-004` 登记（Proposed，待用户批准）**：`API-M002-007` 响应体以**运行实现**为准修订为 `{photo_id, status, suggestions:[{link_id, group_subject_id, subject, confidence, source, suggested_at}]}`（契约原写 `{photo_id, links, suggested_at}`）。理由：`links` 与 `API-M002-003/005` 的「已建立挂接关系」语义冲突，且实现信息更完整；**前端零返工、后端零代码改动**（仅文档追平实现）
- **状态流转**：`CHANGE-003` ③ **前端项关闭**；③ 新增「后端修复（门控）= `Task-010`」进行中；④ 验收剧本 7 条**待 `Task-010` 关闭后启动**
- 修订：`docs/agents/Task-009.md`（关闭 + §7 复核结论）、`docs/agents/Task-010.md`（新建）、`docs/changes/BUG-002.md`（新建）、`docs/changes/CR-004.md`（新建）、`docs/agents/Task-006/007/008.md`（状态行漂移修正）、`docs/AGENT_REGISTRY.md`、`docs/changes/CHANGE-003.md`、`docs/PROJECT_STATUS.md`、`docs/INDEX.md`

## v0.17.0 —— 2026-09-10

### CR-003 ③ 实施收口（Task-006 / Task-007 / Task-008 交付） + 前端作业域任务签发（Task-009）

- **三线交付 + PM 复核 APPROVED（2026-09-10）**：
  - **`Task-007`（AGENT-M001 / M001 v0.2.0 实施）**：事实层按天（唯一键 `(student_id, category, belong_date)`）+ 归属引擎 `WindowResolver`（4 点日界 / 周次 / 周五~周日合并 / 假期自然周）+ 聚合层（`task_groups` / `task_group_subjects`，`ensure_group` 惰性幂等 + `policy_version` 锁定）+ 链路 T（输入源 → AI 解析草稿 → 显式 / 隐式确认）+ 改归属日连锁（幂等 / 跨聚合迁移 / 已消费 409）+ `API-M001-007/009/010` 修订与 `018~021` 新增 + **前端任务域**（列表 / 详情 / 编辑）
  - **`Task-008`（AGENT-M002 / M002 v0.4.0 实施）**：入口 `kind`（权威落 `upload_batches.kind`）+ `photo_subject_links` **N:N** + 逐张复核（accept / reject / relink）+ 窗口级门控 + `completion_analyses`（draft → confirmed → rerun）+ AI 降级兜底（`unassigned` + 手工挂接保留）+ `API-M002-001/003/005` 修订与 `007~011` 新增；**`Task-002` 冻结段增量改接收口**（PD-029）
  - **`Task-006`（AGENT-AI / 横切 `app/core/ai/`）**：Provider 三协议（Vision / OCR / LLM）+ Mock / 真实三方配置化 + prompt 版本化 + 结果 schema 校验拦截 + 超时 / 重试 / 降级 + 三能力接口（`parse_task_spec` / `suggest_photo_links` / `analyze_completion`）+ DATA-009 `ai_call_records` 落库（专属 39 例）
- **PM 独立复验（未采信自述）**：全量 `pytest` = **207 passed / 0 failed**（JUnit XML 精确计数，多次复现）；`read_lints` 0；**`main.py` 启动期幂等自愈已接线**（`ensure_links_migration_hook_registered()` 于 `create_app()` 的 `include_router` 之后调用；实测「清空槽位 → `create_app()` 自愈」通过），与 M002 导入期注册构成「**导入期 + 启动期**」双保险
- **分层违规闭合**：M001 `_discover_links_migration_hook` 反向 import 已删除（`grep "modules.m002" backend/app/modules/m001` = 0 真实 import）；跨模块唯一通道 = **回调注册**，未注册时审计 `links_migration_skipped` + 跳过不阻断
- **治理回填（PM）**：`API_REGISTRY.md` → **`API-M001-018~021` / `API-M002-007~011` Draft → Active**（PM 实测 9 条路由存在），`API-M002-005` 路径更正为 `POST /api/v1/photos/{photo_id}/links`（`/associate` 已移除）；`CONFIGURATION.md` 新增**第五节「AI 接入层配置」**（`AT_AI_*` 全表，独立 `AISettings`，密钥不入库不入日志）；`DATA_MODEL.md` DATA-009 字段按物理表 `ai_call_records` **实施回填**
- **签发 `Task-009`（AGENT-M002，前端「作业」域迁移，`docs/agents/Task-009.md`）**：菜单「照片」→「**作业**」+ 周次 / 周末分组展示 + M002 v0.4.0 前端调用面（`/photos/{id}/links`、`/link-suggestions`、`/photo-gates`、`/completion-analyses*`）+ 挂接复核目标改 `group_subject_id`（清除 `/associate` 死代码，修运行期 404）+ 门控 / 完成分析 UI。**PM 裁决归属 `AGENT-M002`**（写区 = 前端作业域 + M002 后端，**规避 `frontend/src/api/index.ts` 跨 Agent 写冲突**）；**`backend/**` 对本任务只读**
- **状态流转**：`CHANGE-003` ③ 后端 + 横切**完成**；③ 前端 = **`Task-009` 进行中**；④ 验收剧本 7 条（含浏览器级）**待 `Task-009` 关闭后启动**
- 修订：`docs/agents/Task-009.md`（新建）、`docs/API_REGISTRY.md`、`docs/CONFIGURATION.md`、`docs/DATA_MODEL.md`、`docs/AGENT_REGISTRY.md`、`docs/changes/CHANGE-003.md`、`docs/PROJECT_STATUS.md`、`backend/app/main.py`（**PM 独占接线**）

## v0.16.0 —— 2026-09-10

### CR-003 ③ 实施阶段启动（契约定稿 Frozen + Task-007 / Task-008 签发）

- **契约定稿（Frozen，用户批准 2026-09-10）**：**M001 v0.2.0**（事实层按天 + 聚合层 + 链路 T）与 **M002 v0.4.0**（入口 `kind` + N:N 挂接 + 窗口级门控 + 完成分析）经 PM 复核 APPROVED 后由**用户批准冻结**；`MODULE_CONTRACT.md` §签署区落款，九件套状态头由「草案」→「Frozen」，`MODULE_CHANGELOG.md` 补 Frozen 行、开放项全部关闭
- **③ 实施签发**：**`Task-007`**（AGENT-M001，M001 实施：事实层按天重构 → 归属引擎 `WindowResolver` → 聚合层 → 链路 T；API 修订 007/009/010 + 新增 `API-M001-018~021`）与 **`Task-008`**（AGENT-M002，M002 实施：入口 `kind` → **N:N 挂接** → 逐张复核 → **窗口级门控** → 完成分析；API 修订 001/002/003/005 + 新增 `API-M002-007~011`；**Task-002 冻结段增量改接**，PD-029）；两任务**前置已满足、可启动**
- **`Task-006`**（AGENT-AI，横切 `app/core/ai/`）**并行可启动**；M001/M002 实施期以 **Mock** 解阻（`ADR-011`）
- **状态流转**：`CHANGE-003` §3 执行分解 → ③ 实施拆为 Task-007（M001）/ Task-008（M002）+ 前端行（待另行签发）；§4 DoD「契约 Frozen」项勾选；**④ 验收剧本 7 条未启动**
- **遗留（待签发）**：前端「照片」改名「作业」+ 周次 / 周末分组展示（PM 另行签发任务）
- 修订：`docs/modules/M001/**`、`docs/modules/M002/**`（九件套状态头 + CHANGELOG）、`docs/API_REGISTRY.md`、`docs/MODULE_REGISTRY.md`、`docs/AGENT_REGISTRY.md`、`docs/ROADMAP.md`、`docs/INDEX.md`、`docs/PROJECT_STATUS.md`、`docs/changes/CHANGE-003.md`、`docs/agents/Task-007.md`（新建）、`docs/agents/Task-008.md`（新建）

## v0.15.0 —— 2026-09-10

### CR-003 ② 契约修订评审完成（Task-004 / Task-005 交付并经 PM 复核 APPROVED）

- **M001 九件套 → v0.2.0 草案（Task-004，AGENT-M001）**：事实层按天（`tasks` 唯一键 `(student_id, category, belong_date)`；新增 `category`/`belong_date`/`week_index`/`window_type`/`spec_status`；`task_items` **Deprecated**）；新增聚合层 `task_groups`（`policy_version` 锁定）/ `task_group_subjects`（**★判定单元**）/ `task_contents` / `task_spec_sources`；链路 T（输入源 → AI 解析草稿 → 确认 / 隐式确认）+ 归属引擎 `WindowResolver` + 配置锁定语义 + 手工改归属日连锁规则
- **M002 九件套 → v0.4.0 草案（Task-005，AGENT-M002）**：入口 `kind`（任务/作业，**作业上传不填内容**）；归属放开为 **N:N**（`photo_subject_links`）+ **窗口级门控** + `completion_analyses`；`photos.subject`/`group_no`/`suggestion_json` **Deprecated**、`task_id` 降窗口级；手工挂接兜底保留；`M003`/`M004` 前向引用清理
- **PM 复核 APPROVED（2026-09-10）**：A1~A11 / B1~B10 逐项落实、九件套语义与 `CLARIFICATION` / `REQ-010` / `ADR-013` / `ADR-014` / `DATA_MODEL` 一致、零写越界（写区 = `docs/modules/M00x/**`）；**两任务关闭**
- **API ID 分配登记**（PM → `API_REGISTRY.md`，状态 **Draft**）：`API-M001-018`（解析结果确认）/`019`（聚合任务列表）/`020`（聚合任务详情）/`021`（手工改归属日）；`API-M002-007`（挂接建议查询/重试）/`008`（门控状态）/`009`（完成分析生成）/`010`（完成分析确认）/`011`（完成分析重跑）。既有 `API-M001-007/009/010`、`API-M002-001/002/003/005` 为**语义修订**，不新增 ID
- **`DATA_MODEL.md` 字段级同步（PM）**：DATA-001（`tasks` 新增列 / 唯一键 / `task_items` Deprecated）、DATA-003（`kind` / `task_id` 降窗口级 / Deprecated 列）
- **状态流转**：`CHANGE-003` ② 契约修订评审 → **完成**（DoD 两项勾选）；③ 实施 **可启动**（Contract First 前置已满足）；**`Task-006`（AGENT-AI）可启动**
- **遗留**：契约正式 **Frozen 待用户签署**（M001/M002 `MODULE_CONTRACT.md` 签署区）
- 修订：`docs/API_REGISTRY.md`、`docs/DATA_MODEL.md`、`docs/MODULE_REGISTRY.md`、`docs/AGENT_REGISTRY.md`、`docs/INDEX.md`、`docs/PROJECT_STATUS.md`、`docs/ROADMAP.md`、`docs/changes/CHANGE-003.md`、`docs/agents/Task-004.md`、`docs/agents/Task-005.md`、`docs/modules/M001/**`（九件套）、`docs/modules/M002/**`（九件套）

## v0.14.0 —— 2026-09-10

### V1 范围收窄与横切 AI 接入层执行方定案（ADR-014 / PD-026~029）

- **背景**：`CHANGE-003` §6 四项待确认项（Q1 M003~M007 的 V1 边界 / Q2 `REQ-005`~`REQ-007` 是否 V1 必做 / Q3 `app/core/ai/` 执行方 / Q4 Task-002 去留）**阻塞契约修订评审闭合**；用户就四项**逐项拍板**（均采纳 PM 建议）
- **ADR-014 Accepted（V1 范围收窄 + 横切层执行方）**：
  - **Q1 → M003/M004 职责吸收**：M003（AI 作业识别）→ 链路 T 归 **M001**、链路 H 归 **M002** + 横切 `app/core/ai/`；M004（作业任务匹配）→ 聚合子任务级完成结论归 **M002**；**Module ID 保留不撤销，状态 → Deferred**
  - **Q2 → `REQ-005`/`REQ-006`/`REQ-007` 全部后置 V2**（状态 Approved → **Deferred**，需求单保留不作废；输入口径修正保留作 V2 基线）；**V1 范围唯一清单 = `CLARIFICATION` §4.1 必做 10 项；验收 = §5 剧本 7 条**；M005~M007 → Deferred（V2）
  - **Q3 → 横切 `app/core/ai/` 执行方 = 新增 `AGENT-AI`**（任务书 `docs/agents/Task-006.md`；写区仅 `backend/app/core/ai/**`；不设业务 Module ID；**启动前置 = ② 契约评审 APPROVED**）
  - **Q4 → Task-002 = 部分冻结 + 定稿后增量改接**（PD-029）：冻结「归属/挂接」段，允许收尾与 CR-003 无关段（质检/归一/受控存储/受控取图/双主体 API）；Task-005 定稿后按 v0.4.0 增量改接，**返工面限于归属段**
- **ADR-002 关系**：本次为**经用户批准的显式范围收窄**（非豁免）——仍登记 **M001~M007 七个 Module ID、不新增业务模块**，「禁止提前实现 V2+」继续适用
- **PD 登记**：PD-026（模块边界）/ PD-027（需求范围）/ PD-028（AI 层执行方）/ PD-029（Task-002 处置）**Confirmed**
- **治理总表同步（10 份）**：`MODULE_REGISTRY`（M003/M004 职责并入 + M005~M007 Deferred + `Deferred` 状态机说明）/ `AGENT_REGISTRY`（新增 `AGENT-AI`；AGENT-M003~M007 → Inactive；开发顺序收窄为 M001 → M002）/ `REQUIREMENTS` + `REQ-003`~`REQ-007` + `REQ-010`（承载模块改判 + Deferred + 待确认项转决议）/ `ROADMAP`（域 D 与里程碑 M-D 后置 V2；M-END 回归范围 = A/B/C）/ `PROJECT_STATUS`（v0.14.0 + PD-026~029）/ `CHANGE-003`（§2.3 定稿、§3 增 Task-006、§4 DoD、§5 风险解除、**§6 转决议表并关闭**）/ `INDEX` / `API_REGISTRY`（V1 仅 M001/M002 端点）/ `ARCHITECTURE` + `SYSTEM_SUMMARY`（V1 = M001 + M002 + 横切）/ `RISK_REGISTER`（**新增 RISK-012**，RISK-002/005 口径更新）
- **新增**：`docs/adr/ADR-014.md`、`docs/agents/Task-006.md`
- **阻塞状态**：`CHANGE-003` §6 **Q1~Q4 全部关闭**，② 契约修订评审（Task-004 / Task-005）边界闭合，可提交 PM 复核

## v0.13.0 —— 2026-09-10

### 需求澄清定稿：作业任务语义重构 + 归属与判定双层模型（CR-003 / ADR-013）

- **用户提出三处需求偏差**（任务模块理解错误 / 「照片」菜单应改名「作业」 / 挂接-复核-分析顺序），经 14 轮 grill 逐条澄清定稿，完整结论（A~F 分支 + 差距分析 + V1 范围 + 验收剧本）见 `docs/requirements/CLARIFICATION-2026-09-10.md`
- **CR-003 Approved**：① 任务 = 上传照片 / 文本 / 聊天记录（**粘贴文本**，因小程序无接收聊天记录接口）→ AI 解析「今日任务」→ 子任务，**上传无需填写内容**；② 「照片」→「**作业**」菜单，按天归属 + 每周按周次分组 + **周五~周日合并为"周末作业"** + **凌晨 4 点为日界**（9/9 20:00 与 9/10 03:00 同归 9/9）；③ AI 自动挂接 → 家长复核 → **窗口级门控** → 完成情况分析
- **ADR-013 Accepted（双层模型）**：**事实层按天**（`tasks` 唯一键改为 `(student_id, category, belong_date)`；**`task_items` 逐题建模废弃**）+ **聚合层跨天**（`task_groups` → `task_group_subjects` **★判定单元** → `photo_subject_links` **N:N** → `completion_analyses`）；**判定落聚合层**（理由：周末跨 3 天、布置可能仅其中一天上传，天级判定逻辑矛盾）
- **ADR-010 → Superseded（判定粒度）**：内容级逐题判定作废 → 聚合子任务(学科)级；端到端直判 / 可观察依据 / 置信度 / `无法判断` 出口 / 家长复核 / 不武断底线（ADR-003）**由 ADR-013 继承**
- **配置锁定语义**：配置变更**只影响未聚合对象**；已聚合按生成时配置（`task_groups.policy_version`）；锁定**粒度** = 每个 `(学生, 聚合对象)`（同日不同学生可用不同版本）；锁定**触发** = 数据写入（**纯浏览不锁**）；`belong_date` 上传即固化、**不回算历史**
- **新增配置**：`AT_TIMEZONE`(Asia/Shanghai) / `AT_TERM_START` / `AT_TERM_END` / `AT_DAY_CUTOFF`(04:00，可配)
- **数据模型**：`DATA_MODEL.md` 新增 **DATA-012~018**（聚合任务 / 聚合学科子任务 / 内容项 / 任务输入源 / 照片挂接 / 完成情况分析 / 窗口策略配置），修订 DATA-001 / DATA-003 / DATA-004 / DATA-005
- **V1 范围**：必做 10 项；**不做（后置 V2）** = 假期完成计划、评估报告/汇总简报、多任务类型（`category` 仅 `school`）、内容项级判定、聊天记录转发、微信小程序
- **验收阻塞缺陷（已修复，2026-09-10）**：任务列表页空筛选传 `?status=&student_id=` → 后端严格枚举 → **422**。修复 = `frontend/src/api/http.ts` 请求拦截器**统一剔除空值 query**（`""` / `null` / `undefined`，一次覆盖所有列表页）+ `TaskListView.vue` 不再把空串当枚举回填并补 `catch` + `toastError`（消除未捕获 rejection）。验证：`npm run typecheck`（vue-tsc）通过；接口级对照 `?status=&student_id=` → **422**（复现根因）vs 清洗后 query → **200**
- **变更执行（2026-09-10 同日落库）**：需求 ID **REQ-010** 分配（承载 CR-003 新语义）+ `REQ-001`~`REQ-007` 按 CR-003 **精校** → 立项 **`CHANGE-003`（Executing）**（执行分解 ① 需求落库 / ② 契约修订评审 / ③ 实施 / ④ 验收）→ 签发 **Task-004**（AGENT-M001，M001 九件套 → v0.2.0 草案）与 **Task-005**（AGENT-M002，M002 九件套 → v0.4.0 草案）→ 治理总表同步（`MODULE_REGISTRY` / `ROADMAP` / `API_REGISTRY` / `RISK_REGISTER` / `AGENT_REGISTRY` / `ARCHITECTURE` / `SYSTEM_SUMMARY`）→ 清理 `backend/app/modules/m002/` 中「M003」前向引用注释漂移（**仅注释、零逻辑改动，pytest 112 全绿**）
- 新增：`docs/requirements/CLARIFICATION-2026-09-10.md`、`docs/requirements/REQ-010.md`、`docs/changes/CR-003.md`、`docs/changes/CHANGE-003.md`、`docs/changes/BUG-001.md`、`docs/adr/ADR-013.md`、`docs/CONFIGURATION.md`、`docs/agents/Task-004.md`、`docs/agents/Task-005.md`
- 修订：`docs/DATA_MODEL.md`、`docs/REQUIREMENTS.md`、`docs/requirements/REQ-001~007.md`、`docs/adr/ADR-010.md`（Superseded 标注）、`docs/MODULE_REGISTRY.md`、`docs/ROADMAP.md`、`docs/API_REGISTRY.md`、`docs/RISK_REGISTER.md`、`docs/AGENT_REGISTRY.md`、`docs/ARCHITECTURE.md`、`docs/SYSTEM_SUMMARY.md`、`docs/INDEX.md`、`docs/PROJECT_STATUS.md`
- **待办（需 Project Master / 用户拍板，阻塞契约评审闭合）**：`CHANGE-003` §6 待确认项 **Q1**（M003~M007 的 V1 边界）/ **Q2**（`REQ-005`~`REQ-007` 是否 V1 必做）/ **Q3**（`app/core/ai/` 执行方）/ **Q4**（Task-002 去留与返工风险）；Task-004/Task-005 契约修订交付 → PM 复核 → 实施（数据层 → 归属引擎 → 聚合层 → AI 接入层 → 前端「照片」改名「作业」）→ 验收剧本 7 条逐项验收 —— **上述待办已于 v0.14.0 全部决议关闭（见上）**

## v0.12.0 —— 2026-09-08

### 前端技术栈切换立项（ADR-012 / CHANGE-002 / Task-003）

- **用户技术方案变更**：前端采用 Vue3 生态 → PM 可行性评估（REST 契约零影响、M001 前端规模小（app.js 431 行/6 视图）、Task-002 前端 UI 未实现 = 唯一零浪费窗口、FastAPI 静态挂载点与框架解耦）→ 三决策点逐项确认：**Q1 组件库 = Vant 4 纯移动库**（用户原点名 Element Plus，PM 提示桌面密度与 ADR-004「移动优先」冲突后改选）/ **Q2 = TypeScript**（DTO 契约对齐）/ **Q3 = 独立前置任务 + Task-002 后段接轨**
- **ADR-012 Accepted（PD-025）**：Vue3 + Vite + TypeScript + Vant 4 + Vue Router(hash) + Pinia + axios 错误语义映射（400/401/403/404/409/413/415/422）；`frontend/src` 工程化，FastAPI 托管构建产物 `dist/`（单进程形态/ASM-010 不变）；零构建三文件退役；工作量基线 3.5~5.5 人日（含 TS +0.5~1 缓冲）
- **CHANGE-002 立项（Executing）+ Task-003 签发（AGENT-M001，任务书 `docs/agents/Task-003.md`）**：Vue 工程搭建 + M001 6 视图功能等价迁移 + 托管切换 + 退役清理 + 冒烟/pytest 89 回归 + M001 DESIGN/FILES/SUMMARY 与 ARCHITECTURE 回填；`frontend/**` 任务期 AGENT-M001 独占写权
- **Task-002 接轨注**：M002 前端基础 UI 段后移——Task-003 验收后按新栈（Vue 组件）实现；AGENT-M002 后端编码并行不受阻
- 同步：`PROJECT_STATUS.md` → **v0.12.0**（PD-025、O-6 关闭、下一步行动）、`AGENT_REGISTRY.md`（AGENT-M001 Task-003 Active）、`ROADMAP.md`（前端统一栈注）、`INDEX.md`
- 下一步：Task-003（前端切换）与 Task-002 后端并行执行 → Task-002 前端段新栈接轨 → M002 模块级 DoD 复核 → M-A 随 M003 全量验收

## v0.11.0 —— 2026-09-08

### CHANGE-001 完成（M001 定稿 v0.1.2）+ Task-002 正式签发（M002 编码启动）

- **CHANGE-001 PM 复核 APPROVED → Applied（AGENT-M001 完成）**：`CR-001`（任务=多学科作业登记单容器 + 学科作业段 `task_items.group_no`）/`ACR-001`（两级主体：`student_accounts` 学生子账号 + family/student 双型会话 + 命名空间隔离防爆破 + student 仅本人越权 404）/`CR-002`+`ACR-002`（`reference_answer`=非判定基准辅助字段，端到端直判 ADR-010）——代码落地 + 测试 54→**89 全绿** + M001 九件套回填定稿 + DATA_MODEL/REQ-001/Registry 同步
- **API-M001-013~017 收口登记（Active）**：开通/更新学生子账号、学生登录/登出/主体信息（ACR-001 新增端点，API ID 由 Project Master 分配）
- **M001 契约定稿 v0.1.2**（Stable + 维护态）：MODULE.md/CONTRACT/API/DATA/DESIGN/FILES/SUMMARY/TEST/CHANGELOG 状态头与 API 编号同步
- **Task-002 正式签发（AGENT-M002 → Active 编码中，任务书 `docs/agents/Task-002.md`）**：实现 M002 v0.3.0（backend `modules/m002` + 图片质检/归一/受控存储 + 先采后认归属 + tests + 回填九件套）；M001 依赖侧已就绪（`get_task_group`/`can_accept_photo`/双主体认证/`mark_in_progress`）
- 同步：`PROJECT_STATUS.md` → **v0.11.0**、`MODULE_REGISTRY.md`（M001 v0.1.2、M002 Task-002 编码中）、`API_REGISTRY.md`（API-M001-013~017 新增）、`AGENT_REGISTRY.md`（AGENT-M001 维护态、AGENT-M002 Task-002）、`ROADMAP.md`（采集链当前主线）
- 下一步：M002 编码（Task-002）→ ROADMAP M-A 里程碑 PM 验收（学生自主采集闭环）

## v0.10.0 —— 2026-09-08

### M002 契约批准冻结 + Task-002 签发 + M001 变更执行启动

- **M002 契约草案 v0.3.0 用户批准（签署区）→ Frozen**：先采后认归属保留；完成程度以内容级判定为准（M002 收敛为采集/质检/归一/归属/证据供给）；九件套状态头与 MODULE_CHANGELOG +批准冻结行
- **Task-002 签发（AGENT-M002 → Active）**：实现 M002 v0.3.0（backend `modules/m002` + tests + 回填九件套），依赖 M001 CHANGE 落地后联调
- **M001 合并 CHANGE 执行启动（AGENT-M001，Task-CHG）**：`CR-001`（登记单容器化 + `task_items.group_no`，reference_answer 降为非基准辅助字段）/`ACR-001`（两级主体：学生子账号 + 认证）/`CR-002` + `ACR-002`（内容级判定链数据面与 Provider 配置，ADR-010/011 口径）——代码落地 + 54 测试回归 + 新用例 + 回填 M001 契约
- 同步：`PROJECT_STATUS.md` → **v0.10.0**（M002 Developing、M001 变更执行中、下一步行动更新）、`MODULE_REGISTRY.md`（M002 Developing/Frozen v0.3.0、M001 变更执行中）、`API_REGISTRY.md`（API-M002-001~006 Draft → **Frozen**）、`AGENT_REGISTRY.md`（AGENT-M002 Active、AGENT-M001 Task-CHG）、`INDEX.md`
- 下一步：M001 合并 CHANGE 完成 → 回填 M001 九件套 → M002 编码（Task-002）→ ROADMAP M-A 里程碑验收（学生自主采集闭环）

## v0.9.0 —— 2026-09-08

### 主线重排 + 内容级判定重构（用户 grill 定稿 g1~g4 + 内容级四问 q2-1~q2-4，共 8 项决策 PD-017~024）

- **主线按功能域重排（PD-020/g4 → `ROADMAP.md` v0.9.0）**：保留 M001~M007 模块组织与契约治理、开发顺序不变；**主线计划与验收里程碑 = 4 功能域** A 学生自主采集闭环 → B 家长复核确认闭环 → C 大模型内容级匹配+家长兜底 → D 综合评判+每日报告定稿；每条对应用户核心需求逐条可演示验收（里程碑 M-A~M-D + M-END 回归）；横切能力=真实三方 AI/MVC/两级主体/学校字典
- **布置登记录入拍照识别为主（PD-017/g1）**：拍黑板/记事本/布置页 → 大模型识别"今日作业清单（学科+条目）"草稿 → 学生/家长确认补正后生效为登记单；**M003 增加"布置单识别"AI 环节**
- **内容级匹配与评判（PD-018/g2 + PD-021/q2-1 + PD-022/q2-2 → ADR-010）**：布置精确到题；匹配=照片内容↔布置题逐题对齐判完成/对错；**主客观全判**；判定基准=**模型端到端直接判（不维护参考答案字段）**，输出可观察依据+置信度，低置信/无法判断入家长复核；ADR-006（分科混合/参考答案对照）→ **Superseded**，ADR-003 不武断底线保留
- **真实三方 AI 为默认运行（PD-019/g3/需求⑤ → ADR-011）**：Provider 抽象保留，OCR/Vision/LLM 真实三方为默认实现，Mock 降级测试桩/离线降级（`mock-*` 标注）；ASM-010 修订=部署需联网前提；ADR-007 → **Superseded**；RISK-008（三方依赖）、RISK-009（照片出域合规）新增
- **M005 六维保留但 AI 评判为核（PD-023/q2-3）**：逐题完成/对错 + 大模型综合评判（六维质量+综合分）基于识别/匹配证据出具，权重仍配置化
- **报告草稿→家长复核定稿（PD-024/q2-4）**：大模型生草稿 → 家长复核（低置信/无法判断/对错异议逐项过）→ 确认定稿归档（保留草稿与复核记录）

### 更新 / 变更登记

- 新增：`docs/ROADMAP.md`（v0.9.0 功能域主线）、`docs/changes/CR-002.md`（内容级判定链数据面）、`docs/changes/ACR-002.md`（判定与 Provider 架构重构）、`docs/adr/ADR-010.md`（内容级主客观全判，取代 ADR-006）、`docs/adr/ADR-011.md`（真实三方默认，取代 ADR-007）——CR-002/ACR-002 均 **Open 待批准**，ADR-010/011 **Proposed**（同日已批准，见下方"批准包"）
- `ADR-006.md`/`ADR-007.md` → 状态 Superseded（附取代说明）；`ASSUMPTIONS.md`（ASM-008/010/011 修订，ASM-010 联网前提）；`RISK_REGISTER.md`（RISK-002~004/006 口径升级 + RISK-008/009）
- `DATA_MODEL.md`（DATA-001 判定基准语义 + DATA-004/005/006 内容级口径 + v0.9.0 变更预告）；`MODULE_REGISTRY.md`（M001~M007 行口径 + 状态注）
- `SYSTEM_SUMMARY.md` / `ARCHITECTURE.md`：关键技术决策/接入策略/部署架构/外部系统段加 v0.9.0 变更注记（ADR-006/007 Superseded、真实三方默认、联网前提、出域合规）
- `PROJECT_STATUS.md` → **v0.9.0**：阶段更新、PD-017~024 登记、开放项 O-1~O-4 精校 + O-9 新增、下一步行动更新
- `INDEX.md`（+ROADMAP/ADR-010/011 登记，状态同步）；`MODULE_REGISTRY.md` 状态注 v0.9.0

### 批准包（2026-09-08 用户审阅批准，四项全部批准）

- `CR-001`（登记单容器化 + `group_no` 学科作业段）→ **Approved**：批准附带条件落实——条款冲突按 ADR-010 定稿口径修订（`reference_answer` 保留为**非基准**辅助字段、"逐题对照能力"措辞作废）、组号默认语义实施时收敛回填
- `ACR-001`（两级主体认证）→ **Approved**：按验收标准纳入 M001 变更执行（54 测试回归 + 双主体越权矩阵 + family 向后兼容）
- `CR-002`（内容级判定链数据面）→ **Approved**：批准后立即起草 **M002 契约草案 v0.3.x**（下一批准点）
- `ACR-002`（判定 + Provider 架构重构）→ **Approved**：ADR-010/011 生效（**Accepted**，ADR-006/007 → Superseded 正式生效）；ADR-010 §Decision 评分消费引用勘误（依 q2-3/CR-002 语义）
- 同步：`PROJECT_STATUS.md`/`MODULE_REGISTRY.md`/`INDEX.md`/`REQUIREMENTS.md`/`AGENT_REGISTRY.md` 状态 → Approved/Accepted；开放项 O-8/O-9 转入执行前状态
- 下一步：**M002 契约草案 v0.3.x 起草 → 用户批准 → M001 合并 CHANGE 执行**（CR-001/CR-002/ACR-001/ACR-002）

## v0.8.0 —— 2026-09-08

### 变更 / 决策（M002 契约完整性审查 → 两项架构重构 + 采集补全）

- **重构一（任务语义，PD-014 → `CR-001` Open）**：task = **多学科作业登记单容器**；`task_items` 保留题目级并新增 `group_no`（学科作业段，同科多份可区隔）；学科卡 = `(subject, group_no)` 聚合；客观题参考答案逐题对照能力（ADR-006）保留；任务创建主体扩展（家长/学生本人）
- **重构二（采集与归属，PD-015 → M002 v0.2.0）**：**先采后认** —— 上传按"上传批次"不预选任务/学科；照片入库 `unassigned` → AI（M003）建议 `suggested` → 家长/学生确认 `assigned`（归属到登记单内学科作业段）或 `rejected`；首次 assigned 触发任务 `mark_in_progress`（幂等，取代 v0.1.0 D3"首张入库即触发"）；完成程度 = 学科作业段照片覆盖二值化（不猜原则）
- **重构三（身份主体，PD-016 → `ADR-009` Accepted + `ACR-001` Open）**：两级主体 = 家庭账号（家长：全家 + 兜底）+ **学生子账号**（可登录、仅本人）；学生自主登记/拍照、家长兜底；ADR-005 语义扩展（家庭级隔离不变）
- **采集补全（D5~D8）**：D5 数量上限（单批次 ≤50 / 单任务 assigned ≤200，配置化）；D6 页序服务端自增（前端不传页码）；D7 未消费（`consumed_at IS NULL`）照片可撤销（物理删 + 审计），已消费不可变；D8 服务层按 `(family_id, batch_id)` 串行化 + `409 concurrent_conflict`
- 数据：DATA-003 重构 = `upload_batches` + `photos`（归属状态机 + 归属三元组 + suggestion/quality 快照）；M001 冻结面受影响（CR-001/ACR-001 批准后执行变更）

### 更新

- 新增：`docs/adr/ADR-009.md`（Accepted）、`docs/changes/CR-001.md`、`docs/changes/ACR-001.md`（Open）；`RISK_REGISTER.md`（+RISK-006/007）
- `docs/modules/M002/` 九件套 **v0.1.0 → v0.2.0 全量重构**（总览/摘要/契约/API/数据/设计/测试/文件/变更日志；API-M002-001~006）
- `API_REGISTRY.md`（M002 v0.2.0 六接口）、`MODULE_REGISTRY.md`（M002 v0.2.0 + M001 变更预告）、`PROJECT_STATUS.md`（→ v0.8.0，+PD-014~016 与跨模块开放项）、`REQUIREMENTS.md` + REQ-001/002/003 精校、`ADR-005.md`（+ADR-009 扩展注）
- 说明：`INDEX.md`/`DATA_MODEL.md` 的字段级同步随 CR-001/ACR-001 批准后统一执行（避免二次漂移）

## v0.7.1 —— 2026-09-08

### 变更 / 决策

- **M002 四关键决策确认（用户采纳推荐项，PD-010~013）**：
  - D1/PD-010 质量检测策略 = **本地规则先行**（可解释启发式 + 阈值配置化 + 规则版本化，无外部 AI；`QualityChecker` 协议预留 Vision 接入位）
  - D2/PD-011 预处理边界 = **仅轻量归一**（EXIF 归一 + 统一 JPEG + 长边上限缩放；矫正/增强归 M003）
  - D3/PD-012 提交建模与状态触发 = **单图通过即触发**（懒创建/自动归属 open 提交 + 显式 complete；任务首张入库即 `mark_in_progress`，可继续上传至 close）
  - D4/PD-013 不合格处理 = **不入库 + 逐图报告**（失败不留文件/行/状态；`422 image_quality_rejected` 引导重拍）
- **M002 九件套契约草案 v0.1.0（Draft）产出**（`docs/modules/M002/`）：契约/API/数据/设计/文件/测试六件细化 + 总览/摘要/变更日志；API-M002-001~004（上传/提交列表/结束本组/受控取图）登记 **Draft**；DATA-003 字段级细化（submissions/submission_images + 图片存储布局）；**待用户批准（签署区）→ Frozen → 签发 Task-002**

### 更新

- 新增：`docs/modules/M002/`（九件套草案 v0.1.0）
- `MODULE_REGISTRY.md`（M002 Designing/Draft v0.1.0）、`API_REGISTRY.md`（+API-M002-001~004 Draft）、`AGENT_REGISTRY.md`、`PROJECT_STATUS.md`（→ v0.7.1，+PD-010~013）、`INDEX.md`、`MODULE_CHANGELOG.md`（M002 +v0.1.0 行）

## v0.7.0 —— 2026-09-08

### 变更 / 决策

- **M001 DoD 验收通过（用户：验收通过）**：PM 按 `AGENT_GUIDE.md` §6 对 Task-001 交付物逐项验收 → **APPROVED**；M001 Testing → **Stable**（契约 v0.1.1 Frozen 保持不变，API-M001-001~012 全程未越契约）
- 进入 **M002（作业图片采集）契约设计**（M002 → Designing）：关键决策点待用户确认，九件套草案 v0.1.0（Draft）产出后提交批准

### 更新

- `docs/modules/M001/` 九件套状态 → Stable（MODULE.md / MODULE_SUMMARY.md）
- `MODULE_REGISTRY.md`（M001 Stable、M002 Designing）、`AGENT_REGISTRY.md`（AGENT-M001 Task-001 APPROVED；AGENT-001 转入 M002 契约治理）、`PROJECT_STATUS.md`（→ v0.7.0）
- `INDEX.md`（状态同步，修复 v0.4.1~v0.6.0 期间的索引漂移）、`MODULE_CHANGELOG.md`（+验收行）

## v0.6.0 —— 2026-09-08

### 变更 / 决策

- **Task-001 完成（AGENT-M001）**：M001 全量实现落地，契约 v0.1.1（Frozen）无越契约实现
  - backend：FastAPI + SQLAlchemy 2.0 + SQLite 单体（`backend/app/`）；家庭认证（scrypt + 会话哈希 + 登录爆破退避）、学生档案、任务+题目集事务、任务状态机唯一出口、schools 只读字典（seed 幂等 + DB FK 双保险）；统一 ErrorResponse/request_id 贯穿/审计日志脱敏
  - frontend：移动优先 H5 零构建实现（`frontend/index.html` + `styles.css` + `app.js`），FastAPI 静态托管（**模块内实现决策**：本机无 Node 构建链，Vue3+Vite 为可替换壳；决策已记 `MODULE_DESIGN.md`）
  - tests：**54 项全部通过**（unit/API/集成/安全，覆盖 MODULE_TEST 清单与 DoD）
- M001 模块状态 Developing → Testing（待 PM DoD 验收）；API-M001-001~012 保持 Frozen（实现未触发契约变更，无需 CR）

### 更新

- `docs/modules/M001/` 九件套回填实现版（`MODULE_FILES.md`/`MODULE_TEST.md`/`MODULE_DESIGN.md` 状态与内容）；`MODULE_REGISTRY.md`、`AGENT_REGISTRY.md`、`PROJECT_STATUS.md`（→ v0.6.0）；新增 `.gitignore`、`backend/requirements.txt`

## v0.5.0 —— 2026-09-08

### 变更 / 决策

- **用户批准 M001 契约草案 v0.1.1**（签署区 `docs/modules/M001/MODULE_CONTRACT.md`）→ Contract/API/Data 基线 **Frozen**；M001 模块状态 Designing → Developing；API-M001-001~012 状态 Draft → Frozen（修改须走 CR）
- 向 **AGENT-M001** 签发 **Task-001**（实现 M001：backend/frontend 工程骨架 + 功能实现 + 测试 + 回填九件套实现版）→ Active；AGENT-M002~007 保持 Planned（前序验收后按序签发）

### 更新

- `docs/modules/M001/` 九件套状态/签署区同步（Frozen / Developing）；`MODULE_REGISTRY.md`、`API_REGISTRY.md`、`AGENT_REGISTRY.md`、`PROJECT_STATUS.md`（→ v0.5.0）

## v0.4.1 —— 2026-09-08

### 变更 / 决策

- M001 开发输入增补**学校基础资料**（用户确认四项：全局共享字典 + 数据库 seed 预置 + 后台维护暂缓；学生档案必填关联；字段 = 名称+学段；消费限 M001）→ 新增 **REQ-009**（Approved）、**ADR-008**（Accepted）、**DATA-011**（`schools` 全局只读字典）
- M001 契约草案 v0.1.0 → **v0.1.1**：`students.school` 自由文本 → `school_id` 必填（FK→schools）；新增 API-M001-012（GET /schools 只读列表）；schools 初始化 seed 幂等，运行期无维护 API

### 更新

- 新增：`docs/adr/ADR-008.md`、`docs/requirements/REQ-009.md`
- `docs/modules/M001/` 九件套同步 v0.1.1；`DATA_MODEL.md`（DATA-011 + ownership 例外）；`REQUIREMENTS.md`（REQ-009 登记、REQ 状态列修正 Draft→Approved）；`MODULE_REGISTRY.md`、`API_REGISTRY.md`（API-M001-012）
- `PROJECT_STATUS.md` → v0.4.1（PD-009 登记）；`PROJECT.md` / `ADR-005.md` 措辞澄清：学校管理域禁止不变，"学校基础字典"（ADR-008）为限定例外

## v0.4.0 —— 2026-09-08

### 决策

- PD-007/008 经用户复核确认：**ASM-010/011 → Confirmed**（单机/局域网 + SQLite + 本地图片目录；小学语数英书面作业起步 + "无法判断"→ 标记 + 家长复核/重拍）
- **REQ-001~008 → Approved**：V1 需求基线冻结
- 进入 **Phase 2 模块契约设计**：M001（作业任务管理）九件套契约草案产出

### 更新

- `PROJECT_STATUS.md` → v0.4.0（PD 表全部 Confirmed；M001 → Designing）；`ASSUMPTIONS.md`（ASM-010/011 Confirmed）；`MODULE_REGISTRY.md`（M001 Designing）；`REQUIREMENTS.md` + REQ-001~008（Approved）
- 新增：`docs/modules/M001/`（模块文档九件套，契约草案）

## v0.3.0 —— 2026-09-08

### 决策

- 用户确认关键设计决策（PD）并落库 ADR：
  - PD-003 → **ADR-004**：移动优先 H5 + Python FastAPI + SQLite 单体
  - PD-004 → **ADR-005**：纯家庭模式身份模型（家庭账号 + 学生档案，家庭级数据隔离）
  - PD-005 → **ADR-006**：正确度分科混合判定（客观题对照参考答案 / 主观题不判对错并注明）
  - PD-006 → **ADR-007**：AI Provider 抽象 + Mock 先行（本地无 key 跑通全链路）
- 新增默认假设 **ASM-010**（PD-007：单机部署 + SQLite + 本地图片目录）、**ASM-011**（PD-008：小学语数英书面作业起步、无法判断→标记+复核/重拍），状态 Open 待用户复核

### 更新

- `ARCHITECTURE.md` / `SYSTEM_SUMMARY.md`：技术架构、部署、数据、身份、业务流用语按 ADR-004~007 同步
- `DATA_MODEL.md`：存储选型定为 SQLite + 本地图片目录；DATA-002 收敛为家庭账号 + 学生档案（Owner M001）
- `ASSUMPTIONS.md`：ASM-007/008 转 Confirmed，新增 ASM-010/011
- `PROJECT_STATUS.md`：PD-003~006 → Confirmed；版本推进至 v0.3.0

## v0.2.0 —— 2026-09-08

### 新增

- 纳入 V1 MVP 需求（用户「V1 MVP 总控 Agent 指令」，AI 每日作业智能评定系统）：
  - `docs/REQUIREMENTS.md` 登记 REQ-001~008（Draft）；新增 `docs/requirements/REQ-001~008.md` 需求单
  - `docs/MODULE_REGISTRY.md` 登记 M001~M007（需求 M01~M07 别名映射）
  - `docs/AGENT_REGISTRY.md` 登记 AGENT-M001~M007
  - `docs/DATA_MODEL.md` 登记 DATA-001~010 核心实体草案
  - `docs/API_REGISTRY.md` 状态更新（契约阶段逐模块登记）
  - `docs/RISK_REGISTER.md` 创建（RISK-001~004）
  - `docs/PROJECT.md` / `docs/SYSTEM_SUMMARY.md` / `docs/ARCHITECTURE.md` 由骨架填充为 V1 内容

### 决策

- ADR-002：V1 范围控制（仅 7 模块闭环，禁止提前开发未来功能）
- ADR-003：AI 评价边界与原则（可观察行为/配置化权重/分级重写/允许"无法判断"）
- 模块 ID 映射：需求 `M01~M07` ↔ 正式 `M001~M007`
- 待决决策 PD-003~008 等用户确认（见 `PROJECT_STATUS.md`）

## v0.1.0 —— 2026-09-08

### 新增

- 建立文档治理骨架（文档驱动 + 总控 Agent 多 Agent 协作模式），并沉淀治理模板包 `ai-governance-template/`
