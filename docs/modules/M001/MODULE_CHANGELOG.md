# M001 模块变更历史

| 版本 | 日期 | 作者 | 变更 |
| --- | --- | --- | --- |
| **v0.2.0 (实现回填)** | 2026-09-10 | AGENT-M001 (Task-007) | **`CHANGE-003` ③ M001 实施完成回填**：事实层按天（`tasks` 新列 + 唯一键 `(student_id, category, belong_date)`、`task_items` 停写）→ 归属引擎 `WindowResolver`（4 点切日 / 周次 / 周五~周日合并 / 每日期至少一个聚合；假期解析器留空）→ 聚合层 `task_groups` + `task_group_subjects`（★判定单元，`ensure_group` 惰性幂等、`policy_version` 锁定不覆盖）→ 链路 T（输入源上传 → AI 解析草稿（Mock 兜底）→ 显式/隐式确认 + 图片源占位）→ 手工改归属日连锁（幂等 / 跨聚合迁移 / 空聚合回收 / 已消费 409 / `migrate_links_hook`）→ 端点 `API-M001-007/009/010` 修订 + `018~021` 新增 → 前端任务域（创建入口改「上传图片 / 粘贴文本」、`TaskEditorView` 降级草稿确认、列表/详情展示归属日 + 周次 + 窗口）。**测试**：M001 相关 101 passed（全仓 204 passed）；前端 `vue-tsc` + `vite build` 通过。详见下方「Task-007 交付说明」。 |
| **v0.2.0 (Frozen)** | 2026-09-10 | 用户（决策者） | **契约 v0.2.0 批准并冻结（Frozen）**：② 契约修订评审关闭；③ 实施 = **`Task-007`**（已签发）；后续修改一律走 CR/ACR。 |
| **v0.2.0 (PM 复核)** | 2026-09-10 | Project Master | **Task-004 契约修订 PM 复核 APPROVED（任务关闭）**：A1~A11 逐项落实、九件套与 `CLARIFICATION`/`REQ-010`/`ADR-013`/`ADR-014`/`DATA_MODEL` 一致、无越权改治理文档；**API ID 分配登记** = `API-M001-018~021`（Draft）；**`DATA_MODEL.md` DATA-001 字段级已由 PM 同步**；契约 **Frozen 待用户签署**；③ 实施可启动（Contract First：② 已 APPROVED）。 |
| **v0.2.0 (草案)** | 2026-09-10 | AGENT-M001 (Task-004) | **契约修订交付（已交付 → PM 复核 APPROVED 2026-09-10）**：按 `CR-003`(Approved)/`ADR-013`(Accepted)/`REQ-010`(Approved) 修订 —— ① **事实层按天**：`tasks` 唯一键 `(family_id,…)` → **`(student_id, category, belong_date)`**，新增 `category`/`belong_date`/`week_index`/`window_type`/`spec_status`；`tasks.subject`/`content` **Deprecated**；`task_items` 及「多学科登记单容器 / 学科作业段 `group_no`」语义**作废**（A1/A2）。② **新增聚合层**：`task_groups`（含 `policy_version` 锁定）+ `task_group_subjects`（**★判定单元**）（A6/A7）。③ **新增数据表**：`task_contents`（内容项，只读）+ `task_spec_sources`（输入源多段）（A3/A4）。④ **链路 T**：任务创建改「输入源（图片/粘贴文本，无需填内容）→ AI 解析草稿 → 家长确认/隐式确认」；`spec_status` 状态机（A4/B7）。⑤ **归属引擎 `WindowResolver`** 策略接口（4 点边界/周次/周末聚合/假期自然周）+ **配置锁定语义** + **手工改归属日连锁规则**（A5/A7/A8）。⑥ 新增端点 4 个（解析确认/聚合列表/聚合详情/改归属日），**API ID = `API-M001-018~021`**（PM 分配登记，A9）；既有 API-M001-007~010 修订。⑦ 测试设计新增（归属边界/周次/周末聚合/唯一键/配置锁定按学生隔离/聚合幂等/改归属日连锁），基线 89 passed 保持（A10）。**破坏性变更，V1 无历史生产数据故直接演进；PM 复核 APPROVED（2026-09-10），实施（`CHANGE-003` ③）可启动。** |
| v0.1.2 (定稿) | 2026-09-08 | Project Master | **CHANGE-001 PM 复核 APPROVED → 关闭（Applied）**：DoD 全项勾选；API-M001-013~017（ACR-001 新增端点）分配登记（Active）；M001 契约随变更后实况定稿 v0.1.2（本九件套状态头同步）；模块进入维护态，支持 M002 Task-002 联调。 |
| v0.1.2 (回填) | 2026-09-08 | AGENT-M001 | **CHANGE-001 编码完成回填**（CR-001/CR-002/ACR-001/ACR-002 批准合并执行；代码+测试已落地，**待 PM 复核后关闭/定稿**）：① CR-001 任务=多学科登记单容器（`tasks.subject` 可空/'mixed'；`task_items.group_no` 学科作业段 + 结构校验 + 段级查询 `get_task_group(s)`/`can_accept_photo`）；② ACR-001 两级主体（`student_accounts` 表、`auth_sessions.subject_type`/`student_id`、`AuthContext` 双主体、学生登录/登出/me、子账号管理端点、student 越权 404/家长专属 403、登录爆破命名空间隔离）；③ CR-002/ACR-002 语义面（`reference_answer` 标注为非判定基准辅助字段，判定链端到端直判不依赖参考答案）。测试 54→89 全绿（新增：student 子账号 23 + 容器化 API 4 + group_no 校验 8）；student_account_service/schema/student_auth 等文件新增，见 `MODULE_FILES.md`。 |
| v0.7.0 (验收) | 2026-09-08 | Project Master | **PM DoD 验收 APPROVED（用户：验收通过）**：Task-001 交付物按 `AGENT_GUIDE.md` §6 全项通过 → M001 Testing→**Stable**（契约 v0.1.1 Frozen 不变，API-M001-001~012 未越契约）。M001 进入维护态，M002 契约设计启动。 |
| v0.6.0 (实现) | 2026-09-08 | Project Master | **Task-001 实现回填**：M001 编码+测试完成（54 passed）——模块状态 Developing→Testing；工程落地 backend/（FastAPI）+ frontend/（零构建 H5）+ tests/；九件套实现版同步（FILES/TEST/DESIGN）；API 契约未变更（保持 Frozen）。详见项目 `CHANGELOG.md` v0.6.0。 |
| v0.1.1 (Frozen) | 2026-09-08 | 用户 + Project Master | **批准**：用户批准 M001 契约草案 v0.1.1（签署区见 `MODULE_CONTRACT.md`）→ Contract/API/Data 基线冻结；M001 转 Developing，签发 Task-001（AGENT-M001）。 |
| v0.1.1 | 2026-09-08 | Project Master | 契约草案迭代：用户 M001 开发输入增补"学校基础资料"（REQ-009/ADR-008/DATA-011）——新增 `schools` 全局只读字典表（seed 预置、无运行期写路径）；`students.school` 自由文本 → `school_id` 必填（FK→schools）；新增 API-M001-012（GET /schools）；档案 DTO 携带学校信息。九件套同步至 v0.1.1。 |
| v0.1.0 | 2026-09-08 | Project Master | 契约草案发布：M001 定位为家庭空间 + 作业任务生命周期基座（ADR-004/005/006）；九件套 v0.1 产出；API-M001-001~011 登记（Draft）。状态：待用户批准（签署区见 `MODULE_CONTRACT.md`）。 |

---

## Task-004 交付说明（v0.2.0 草案；供 PM 复核）

> 依据 `CHANGE-003` §2.1 清单 A1~A11；写区仅 `docs/modules/M001/**`。

### 1. A1~A11 逐项落实对照

| # | 修订点 | 落实位置 |
| --- | --- | --- |
| A1 | `tasks` 字段与唯一键（新增 `category`/`belong_date`/`week_index`/`window_type`/`spec_status`；唯一键 `(student_id, category, belong_date)`；`title` 可自动生成） | `MODULE_DATA.md`（`tasks` 表）、`MODULE_DESIGN.md`（决策表 §事实层唯一键、决策 17） |
| A2 | `task_items` 标 Deprecated；「多学科登记单容器 + 学科作业段 `group_no`」作废 | `MODULE_DATA.md`（`task_items` 段 + Deprecated 列）、`MODULE_CONTRACT.md`（变更摘要 ①②）、`MODULE_API.md`（DTO 约定作废行、内部接口作废注） |
| A3 | 新增 `task_contents`（DATA-014，只读）×`task_spec_sources`（DATA-015，多段） | `MODULE_DATA.md`（两表定义） |
| A4 | 任务创建流程改「输入源 → AI 解析草稿 → 确认 / 隐式确认」；上传无需填内容；`spec_status` 状态机 | `MODULE_CONTRACT.md` §F1、`MODULE_API.md` API-M001-007（修订）、`MODULE_DESIGN.md` §链路 T |
| A5 | 归属引擎 `WindowResolver.resolve(ts) → {belong_date, week_index, window_type, group_key}`（策略接口，读 4 个 `AT_*`） | `MODULE_DESIGN.md` §归属引擎、`MODULE_DATA.md`（约束与规则·归属引擎） |
| A6 | 聚合层 `task_groups`（含 `policy_version`）+ `task_group_subjects`（★判定单元）+ 查询契约 | `MODULE_DATA.md`（两表）、`MODULE_API.md`（聚合列表/详情端点） |
| A7 | 配置锁定语义（影响面/粒度/触发/固化） | `MODULE_CONTRACT.md` §F4、`MODULE_DESIGN.md` §聚合生成与锁定 |
| A8 | 手工改归属日连锁规则 | `MODULE_CONTRACT.md` §F5、`MODULE_API.md`（改归属日端点） |
| A9 | 新增端点 → API ID 由 PM 分配（禁止自行编号） | `MODULE_API.md`（«CR-003 新增端点»表 + «API ID 申请清单»：M001-A1~A4，交付时 ID 留空）；**PM 已分配 = `API-M001-018~021`（2026-09-10）** |
| A10 | 测试基线 89 passed + 新增用例（归属边界 4 点/周次/周末聚合/唯一键/配置锁定按学生隔离） | `MODULE_TEST.md`（§新增用例设计，含 U/I/A 三类 + 链路 T Mock 编排） |
| A11 | 回填九件套 + `MODULE_CHANGELOG.md` + `DATA_MODEL.md` DATA-001 字段级 | 九件套全部更新（`MODULE.md`/`MODULE_SUMMARY.md`/`MODULE_FILES.md`/本文件）；**`DATA_MODEL.md` 字段级由 PM 同步**（本任务禁写治理文档） |

### 2. 破坏性变更清单（v0.1.2 → v0.2.0）

| # | 变更 | 兼容性处置 |
| --- | --- | --- |
| 1 | `tasks` 唯一键 `(family_id,…)` → **`(student_id, category, belong_date)`** | V1 无历史生产数据，开发库直接演进（`CHANGE-003` §5） |
| 2 | 新增 5 张表（`task_contents`/`task_spec_sources`/`task_groups`/`task_group_subjects`；`task_items` 退役） | 旧表 `task_items` 保留（兼容旧数据/回滚），不提供兼容读契约 |
| 3 | `tasks.subject`/`content` **Deprecated** | 保留列（不写），字段语义移至 `task_contents`/聚合层 |
| 4 | 任务创建由「手工录入题目集」改为「输入源解析」 | 端点 `API-M001-007` 路径不变、载荷语义重定义（CR 授权） |
| 5 | 内部接口 `get_task_group(s)`/`can_accept_photo`/`can_accept_submission`（段级）**作废** | 改为窗口/聚合级接口（见 `MODULE_API.md` §内部接口） |
| 6 | `reference_answer` 辅助字段退役 | ADR-013 继承"端到端直判、不维护参考答案基准"原则 |

### 3. 开放项清单

| # | 开放项 | 状态 |
| --- | --- | --- |
| 1 | 新增端点 API ID（M001-A1~A4） | **已分配（2026-09-10）** = `API-M001-018`（解析确认）/`019`（聚合列表）/`020`（聚合详情）/`021`（改归属日），登记 `API_REGISTRY.md`（Draft） |
| 2 | `DATA_MODEL.md` DATA-001 字段级同步（新增列/唯一键/Deprecated） | **已由 PM 同步（2026-09-10）** |
| 3 | 契约签署（用户/PM） | **已关闭（2026-09-10）**：PM 复核 APPROVED + **用户批准 → Frozen**（`MODULE_CONTRACT.md` §签署区已落款） |
| 4 | ~~Q1/Q2/Q3 边界挂起项~~ | **已闭合**（`ADR-014`，无残留待确认表述） |

> 说明：契约层无未决假设；③ 实施阶段须在 PM 复核 APPROVED 后签发（Contract First）。

---

## Task-007 交付说明（v0.2.0 实现回填；供 PM 验收）

> 写区：`backend/app/modules/m001/**`、`backend/app/api/v1/**`（M001 路由）、`backend/tests/**`、`frontend/src/{views,api,router}/**`（任务域）、本文件。

### 1. 落地清单（对照 A1~A11）

| # | 修订点 | 落地位置 |
| --- | --- | --- |
| A1 | 事实层按天：`tasks` 新列（`category`/`belong_date`/`week_index`/`window_type`/`spec_status`）+ 唯一键 `(student_id, category, belong_date)` | `models/orm.py`、`repositories/task_repo.py` |
| A2 | `task_items` 停写（Deprecated 留表）；段级兼容桩保留 | `models/orm.py`、`services/task_service.py`（`get_task_group(s)`/`can_accept_photo` 标 deprecated） |
| A3 | `task_contents`（内容项，只读）+ `task_spec_sources`（输入源多段；`photo_id` 仅引用、不建跨模块 FK） | `models/orm.py`、`repositories/task_repo.py` |
| A4 | 链路 T：输入源 → AI 解析草稿 → 显式/隐式确认；`spec_status` = `placeholder`/`parsed`/`confirmed` | `services/task_service.py`（`ingest`/`confirm_parse`）、`services/task_parser.py`（AI 优先 + Mock 降级） |
| A5 | 归属引擎 `WindowResolver.resolve(ts) → {belong_date, week_index, window_type, group_key}`（4 点切日 / 周次 / 周五~周日合并；假期解析器留空） | `services/window_resolver.py`、`schemas/task_group.py`（`WindowInfo`） |
| A6 | 聚合层 `task_groups`（`policy_version`）+ `task_group_subjects`（★判定单元）+ 惰性幂等 `ensure_group` | `models/orm.py`、`services/aggregation_service.py`、`services/task_group_service.py`、`repositories/group_repo.py` |
| A7 | 配置锁定：写入触发、生成时 `policy_version` 固化、追加重算不改写既有 `policy_version` | `services/aggregation_service.py`（`ensure_group`/`refresh_group`） |
| A8 | 手工改归属日连锁（幂等 / 跨聚合迁移 / 空聚合回收 / 已消费 409 / 审计 / `migrate_links_hook`） | `services/task_service.py`（`change_belong_date`）、`services/aggregation_service.py`（`migrate_links_hook` + `register_links_migration_hook`） |
| A9 | 端点：`API-M001-007/009/010` 修订；`018`（解析确认）/`019`（聚合列表）/`020`（聚合详情）/`021`（改归属日）新增 | `api/v1/tasks.py`、`api/v1/task_groups.py`、`api/v1/deps.py`（`get_window_resolver` 注入） |
| A10 | 测试：归属边界/周次/周末合并/唯一键原子性/配置锁定/聚合幂等/改归属日/链路 T/解析确认/越权隔离/日志脱敏 | `tests/_m001_helpers.py`、`tests/unit/**`、`tests/api/**`、`tests/integration/test_internal_services.py` |
| A11 | 回填本文件（版本历史 + 交付说明） | `MODULE_CHANGELOG.md`（本段） |

### 2. 内部接口最终签名（供 M002 对接；`MODULE_API.md` §内部接口）

```python
# services/task_service.py
TaskQueryService.get_task(session, family_id, task_id) -> TaskDTO
TaskQueryService.list_tasks(session, family_id, *, student_id=None, status=None, belong_date=None, week_index=None) -> list[TaskDTO]
TaskQueryService.resolve_window(ts, *, resolver=None) -> WindowInfo
TaskQueryService.list_groups(session, family_id, *, student_id=None, week_index=None, window_type=None, resolver=None) -> list[TaskGroupDTO]
TaskQueryService.get_group(session, family_id, group_id) -> TaskGroupDTO
TaskQueryService.ensure_group(session, family_id, student_id, category, belong_date, *, resolver=None) -> TaskGroupDTO
TaskQueryService.can_accept_submission(session, family_id, task_id, student_id) -> bool
TaskStateService.transition(session, family_id, task_id, action) -> tuple[TaskDTO, str]      # publish|close|reopen
TaskStateService.mark_in_progress(session, family_id, task_id) -> tuple[TaskDTO, str]        # 已 in_progress 幂等

# services/aggregation_service.py
TaskAggregationService.ensure_group(session, family_id, student_id, category, belong_date, *, resolver=None) -> TaskGroupDTO
TaskAggregationService.member_tasks(session, group, *, resolver=None) -> list[Task]
TaskAggregationService.refresh_group(session, group, *, resolver=None) -> None
TaskAggregationService.get_group_subject(session, family_id, group_subject_id) -> TaskGroupSubjectDTO
TaskAggregationService.commit_conclusion(session, family_id, group_subject_id,
                                          conclusion, evidence_photo_ids=None, confidence=None,
                                          status="confirmed") -> TaskGroupSubjectDTO
TaskAggregationService.migrate_links_hook(session, family_id, task_id, old_group_key, new_group_key) -> None
register_links_migration_hook(fn)   # 回调唯一来源 = 注册（M002 导入期注册 `migrate_photo_links`；
                                    # `app/main.py` 启动期可幂等自愈再注册一次）。M001 不 import M002。
                                    # 未注册 → 记审计 `links_migration_skipped` 并跳过（不阻断改归属日事务）。
```

内部越权统一抛 `PermissionDeniedError`（REST 层对外映射 **404**，防探测；见 `tests/api/test_isolation.py`）。

### 3. 测试与验证

- `pytest -q` 全仓 **204 passed**（M001 相关 **101 passed**；基线 89 未回归）。
- 前端：`npx vue-tsc --noEmit -p tsconfig.app.json` 通过；`npm run build` 成功。
- 契约一致性自检：端点路径/方法/载荷/响应模型与 `MODULE_API.md` v0.2.0 逐项核对一致；未新增契约外字段与端点。

### 4. 遗留风险与说明

1. **`tzdata` 缺失回退**：运行环境（Windows venv）无 `tzdata`，`ZoneInfo("Asia/Shanghai")` 不可用 → `WindowResolver` 回退为**固定 UTC+8**（V1 部署时区无夏令时，语义等价）；若后续支持其它时区，需申请向 `requirements.txt` 增加 `tzdata`（PM 独占文件）。
2. **`PhotoListView.vue` 挂接挑选器待迁移**：该视图原按 `task_items` 段（`task→subject→group_no`）实现手工兜底归属，段模型作废后已无可列段（现为禁用态，未破坏其余流程）；**其迁移归 M002 照片域**（改按聚合学科子任务 `group_subject_id` + `/photos/{id}/links`），已同步 `m002-dev` 与 PM。
3. **假期窗口未实现**：V1 按 `CHANGE-003` 留空（`window_type=holiday` 解析器未接入），不影响日/周末语义。
4. `deps.py` 的 `get_window_resolver` 优先读 `app.state.window_resolver`（测试注入用），生产走 `app.state.settings` 构建。
