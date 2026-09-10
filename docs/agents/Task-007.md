# Task-007 任务书 —— M001 实施（事实层按天 + 归属引擎 + 聚合层 + 链路 T）

- **Task ID**：Task-007 ｜ **Agent**：`AGENT-M001` ｜ **Module**：M001（作业任务管理）
- **签发**：Project Master，2026-09-10 ｜ **状态**：**已交付 → PM 复核 APPROVED（2026-09-10）**（全量 `pytest` = 207 passed / 0 failed；含前端任务域） ｜ **Kind**：**实施（编码）**
- **启动前置（Contract First，硬约束）**：M001 契约 **v0.2.0 Frozen（用户批准 2026-09-10）** —— **前置已于 2026-09-10 满足**（`Task-004` 交付 + PM 复核 APPROVED + 用户批准冻结）。契约未定稿前本任务**不得落地任何代码**。
- **前置依据**：`docs/modules/M001/MODULE_CONTRACT.md`（v0.2.0 Frozen，权威）、`MODULE_DATA.md` / `MODULE_API.md` / `MODULE_DESIGN.md` / `MODULE_TEST.md`（同版本）、`docs/adr/ADR-013.md`、`docs/adr/ADR-014.md`、`docs/requirements/CLARIFICATION-2026-09-10.md`、`docs/requirements/REQ-010.md`、`docs/DATA_MODEL.md`（DATA-001/012~015）、`docs/CONFIGURATION.md`、`docs/changes/CHANGE-003.md` §2.1 A1~A11
- **任务书登记**：`docs/AGENT_REGISTRY.md`（`AGENT-M001` 行）｜ **验收**：`CHANGE-003` ③ 里程碑（域 A/B/C）+ `MODULE_TEST.md` 用例设计 + 本任务 §6 DoD

## 1. Objective（目标）

按 `CHANGE-003` §3 顺序推进 **M001 基座实施**（③ 第一步）：把 M001 从「手工录入题目的任务容器」重构为 **「事实层按天 + 聚合层跨天」** 的双层模型，并落地 **链路 T**（布置输入源 → AI 解析草稿 → 家长确认）与 **归属引擎 `WindowResolver`**，为 M002 链路 H（挂接/门控/完成分析）提供挂接目标与判定单元。

## 2. Requirements（权威源，只读，禁止复制改写）

- `docs/modules/M001/**`（九件套 v0.2.0 Frozen）—— **本任务的唯一契约来源**
- `docs/adr/ADR-013.md`（双层模型：事实层按天 + 聚合层跨天，**挂接与判定落聚合层**；ADR-010 判定粒度 Superseded）
- `docs/adr/ADR-014.md`（M003 链路 T 归 M001；M004 职责归 M002）
- `docs/adr/ADR-011.md`（真实三方默认 / Mock 降级）、`docs/DATA_MODEL.md`（DATA-001 修订 + DATA-012~015）
- `docs/CONFIGURATION.md`（`AT_TIMEZONE` / `AT_TERM_START` / `AT_TERM_END` / `AT_DAY_CUTOFF` 与**生效/锁定规则 5 条**）
- 现有基座：`backend/app/core/config.py`（pydantic-settings，前缀 `AT_`）、`backend/app/shared/`、`backend/app/modules/m001/**`（v0.1.2 实况）、`backend/tests/`（89 基线）

## 3. Scope（范围）

### 3.1 本任务交付

| # | 交付 | 说明 |
| --- | --- | --- |
| 1 | **事实层按天** | `tasks` 新增 `category`（V1 仅 `school`，读全局只读字典 seed）/`belong_date`/`week_index`/`window_type`/`spec_status`；**唯一键 `(student_id, category, belong_date)`**；`tasks.title` 由窗口解析器生成（如「09-09 周三」）；`subject`/`content` **Deprecated（不写）**；`task_items` **停止写入**（表保留，兼容旧数据） |
| 2 | **归属引擎 `WindowResolver`** | 策略接口 `resolve(ts) → {belong_date, week_index, window_type, group_key}`；**凌晨 4 点切日**（`AT_DAY_CUTOFF`）/`AT_TIMEZONE`；`week_index` = `AT_TERM_START` 所在周周一起算；**V1 只实现学期内解析器**，假期解析器留空（保底：整段假期 = 1 窗口、不按天建主任务） |
| 3 | **聚合层（落库固化）** | 新增 `task_groups`（含 **`policy_version`**）+ `task_group_subjects`（**★判定单元**，含 `conclusion_status`）；`ensure_group` **惰性 + 幂等**（进列表页 / 任务解析完成 / 作业照片上传触发）；**每个 `belong_date` 至少一个聚合**（最小 1 天）；周末 = 展示层聚合（周一 04:00 前的上传归上一周末窗口） |
| 4 | **配置锁定语义** | 配置变更**只影响未聚合对象**；已聚合按生成时 `policy_version`；**锁定粒度 = 每个 `(student_id, 聚合对象)` 独立锁**；**锁定触发 = 数据写入，纯浏览不锁**；`belong_date` 上传即固化、**不回算历史** |
| 5 | **链路 T 解析** | 输入源上传（**图片 / 粘贴文本，多段**；作业上传**不填内容**）→ 经 `app/core/ai/` 解析（**Mock 可解阻**）→ 草稿落库 → 家长**确认** / **隐式确认**；`spec_status = placeholder\|parsed\|confirmed`；**占位主任务**（作业先到时自动建行，标题自动生成） |
| 6 | **手工改归属日连锁** | 契约 §F5 六条：重算快照 → 迁移主表 FK（目标无行则建）→ 源窗口变空删行 → **已被完成分析消费的作业禁改**（V1 拒绝）→ 记审计；跨聚合迁移须通知 M002 迁移挂接目标（`migrate_links_hook`） |
| 7 | **API 面** | 修订 `API-M001-007`（`POST /tasks` 改「创建 + 载入输入源」）/`009`（详情含解析草稿）/`010`；**新增 `API-M001-018~021`**（解析结果确认含隐式确认 / 聚合任务列表 / 聚合任务详情 / 手工改归属日）—— ID 已由 PM 分配登记（Draft → 本任务实施后转 Active） |
| 8 | **前端（M001 任务域）** | 任务创建入口改为**上传布置照片/粘贴文本**；`TaskEditorView` 降级为**草稿确认/修正**界面；任务列表/详情展示 **归属日 + 周次** |
| 9 | **测试** | 既有 **89 项不回归**；新增用例按 `MODULE_TEST.md` §新增用例设计（归属边界 4 点 / 周次 / 周末聚合 / 唯一键冲突 / **配置锁定按学生隔离** / 改归属日连锁 / 链路 T 确认与隐式确认） |

### 3.2 Allowed-Files（可写）

- `backend/app/modules/m001/**`（唯一业务写区）
- `backend/app/api/v1/**`（**仅 M001 相关路由**：tasks / task_groups / belong_date 等）
- `backend/tests/**`（新增 M001 用例，禁止破坏既有用例）
- `frontend/src/views/**`、`frontend/src/api/**`、`frontend/src/router/**`（**仅任务域**：任务创建/编辑/列表/详情）
- `docs/modules/M001/MODULE_CHANGELOG.md`（实施完成后回填版本历史）

### 3.3 Forbidden-Files / 边界

- **禁止改动 M002 业务代码/契约**（`backend/app/modules/m002/**`、`docs/modules/M002/**`）—— M002 侧由 `Task-008` 负责
- **禁止越界修改治理层文档**（Registry / ADR / CHANGE / REQUIREMENTS / ROADMAP / PROJECT_STATUS / CHANGELOG / INDEX / DATA_MODEL / CONFIGURATION / API_REGISTRY）—— 需变更先以 **Request** 报 PM
- 禁止在 `app/core/ai/` 内写代码（`AGENT-AI`/`Task-006` 写区）；上游经**内部接口**调用
- 禁止实现 V2 功能（六维评分 / 评语 / 报告 / 假期完成计划与评估报告）
- 禁止自行分配 API / DATA / Task ID；禁止跳过契约（契约未写的字段/端点不得擅自新增）

## 4. Dependencies（前置就绪条件）

- **硬前置**：M001 契约 **v0.2.0 Frozen**（✅ 2026-09-10）
- **并行**：`Task-006`（`app/core/ai/`）—— **Mock 模式即可解阻**链路 T；真实三方就绪后按 `ADR-011` 补充验证
- **下游**：`Task-008`（M002）消费本任务的**聚合层内部接口**（`get_group` / `ensure_group` / `commit_conclusion` / `mark_in_progress` / `migrate_links_hook`）—— 接口签名变更必须以 Request 报 PM

## 5. Expected Deliverables（完成即提交 PM 复核）

- 代码按 §3.1 落地，lint 无错误；`backend/.venv` 下 `pytest` **全绿（既有 89 + 新增）**
- **迁移/演进实证**：开发库按 `CHANGE-003` §5 直接演进（无数据迁移脚本）；`task_items` 停止写入后无回归
- **契约一致性实证**：`MODULE_API.md` 中每条端点与实现路径/请求响应/错误码一致；`API-M001-018~021` 状态可转 **Active**
- 前端任务域可走通：上传布置照片 → 查看/修正解析草稿 → 确认 → 列表按归属日/周次展示 → 手工改归属日
- 提交 PM 的 Request 清单（如需新增配置项 / 内部接口变更）
- 完成后：提交 PM 按本任务 §6 DoD 复核；**回填 `MODULE_CHANGELOG.md` 版本历史**

## 6. Acceptance Criteria（DoD，AGENT_GUIDE §6）

- [ ] `tasks` 唯一键 = `(student_id, category, belong_date)`；同学生同日同分类重复创建被拒（有测试）
- [ ] `WindowResolver` 4 点切日边界 4 点用例通过（03:59 / 04:00 两侧）；`week_index` 按学期开始周计算正确
- [ ] 聚合层 `ensure_group` 幂等（重复调用不产生重复聚合并有测试）；未聚合对象按**当前生效**配置生成、已聚合按 `policy_version`
- [ ] **配置锁定按学生隔离**用例通过（同配置下 A 已锁定、B 走新配置）
- [ ] 链路 T：输入源（图片 + 粘贴文本多段）→ 草稿 → 显式确认 / **隐式确认** 两条路径均落库正确；作业先到自动建**占位主任务**且标题非空
- [ ] 手工改归属日连锁 6 条全部生效（含**已消费禁改**拒绝路径与审计记录）
- [ ] `API-M001-007/009/010` 修订与 `API-M001-018~021` 新增实现与契约一致（含双主体鉴权 404/403 语义）
- [ ] 既有 **89 项不回归**；`MODULE_TEST.md` §新增用例设计全部落地通过
- [ ] 未越权改动 M002 / 治理文档 / `app/core/ai/`；未实现 V2 功能
- [ ] PM 复核 APPROVED → Task-007 关闭 → M001 进入**可验收态**（域 A 里程碑）

> 注：本任务**不含** M002 侧挂接/门控/完成分析（`Task-008`）与跨模块端到端验收（`CHANGE-003` ④ 验收剧本 7 条，含第 7 条浏览器级）。
