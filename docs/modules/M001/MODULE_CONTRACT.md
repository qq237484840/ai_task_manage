# M001 模块契约（黑盒）—— 作业任务管理

- **Module ID**：M001 ｜ **版本**：**v0.2.0（Frozen）** ｜ **日期**：2026-09-10
- **状态**：**契约 v0.2.0 —— Frozen（用户批准 2026-09-10）**（前版 v0.1.2 为 Stable 基线；本次按 `CR-003`（Approved）/`ADR-013`（Accepted）/`REQ-010`（Approved）作**破坏性语义修订**，经 PM 复核 APPROVED 后由用户批准冻结）
- **适用**：黑盒约定。内部实现（类/库/表结构细节）见 `MODULE_DESIGN.md` 与 `MODULE_DATA.md`
- **权威源**：`docs/requirements/CLARIFICATION-2026-09-10.md`（冲突时以其为准）
- **v0.2.0 变更摘要（CR-003）**：① **事实层按天**：`tasks` 唯一键改 `(student_id, category, belong_date)`，新增 `category`/`belong_date`/`week_index`/`window_type`/`spec_status`；`task_items` **Deprecated**；原「多学科登记单容器 + 学科作业段 `group_no`」条款**作废**。② **新增聚合层**：`task_groups`（含 `policy_version`）+ `task_group_subjects`（**★判定单元**）。③ **链路 T**：输入源（图片 / 粘贴文本，多段）→ AI 解析草稿 → 家长确认 / **隐式确认**；上传**无需填写任何内容**。④ **归属引擎** `WindowResolver`（4 点边界 / 周次 / 周末聚合 / 假期自然周）。⑤ **配置锁定语义** + **手工改归属日连锁规则** 契约化。⑥ 新增端点 **API ID 已由 PM 分配 = `API-M001-018~021`**（Draft）。

## Purpose

V1 入口基座：提供纯家庭模式下的家庭空间（家庭账号 + 学生子账号两级主体认证、学生档案，档案必填关联全局学校字典）与**按天作业任务（布置）解析与聚合**能力（链路 T；归属引擎；按天事实层 + 跨天聚合层），支撑 M002（链路 H）的挂接与判定输入。

## Responsibilities / Non-Responsibilities

见 `MODULE.md`（M001 的 Purpose/Responsibilities/Non-Responsibilities 即为本契约黑盒职责，不再复制）。

## Inputs / Outputs

| 类型 | 说明 |
| --- | --- |
| Inputs | 家长注册 / 家长登录 / **学生登录凭据**；学生档案信息（含必填 `school_id`）；子账号开通/停用/改密；**任务输入源（图片 / 粘贴文本，多段，无需填写内容）**；解析确认动作（含隐式确认）；**手工改归属日**动作；状态推进指令 |
| Outputs | family/student 双型会话 token；档案/子账号状态；**任务事实**（`tasks` + 内容项 + 输入源）；**解析草稿与确认结果**（`spec_status`）；**聚合与聚合学科子任务**；归属窗口计算（`belong_date`/`week_index`/`window_type`）；状态迁移结果与校验错误 |

## Exposed APIs

- REST（前缀 `/api/v1`）：
  - **既有面** `API-M001-001~017`（登记 `API_REGISTRY.md`；其中创建/查询任务相关随本变更修订，见 `MODULE_API.md`）
  - **CR-003 新增**：输入源上传、解析草稿查询、解析结果确认（含隐式确认）、归属窗口/聚合查询、改归属日 —— **新增端点 API ID = `API-M001-018~021`**（由 PM 分配并登记 `API_REGISTRY.md`，Draft）
- 内部服务接口（进程内，供 M002；V2 供 M005/M007）：`FamilySpaceService`、`StudentAccountService`、`TaskQueryService`（事实层 + 聚合层）、`TaskStateService`、`WindowResolver`

## Events

- V1 为单体同步架构，**不引入异步事件总线**；状态变化以 API 响应与操作日志记录，消费模块（M002 等）经查询接口获取状态（诚实声明：无 outbox/消息队列）
- 任务创建/解析确认/聚合生成/状态迁移/改归属日 写入审计日志（audit），供追溯

## 核心流程

### F1 链路 T —— 任务创建（输入源 → AI 解析草稿 → 确认 / 隐式确认）

1. **上传输入源**：家长/学生在菜单「任务」提交输入源（图片 `kind=image` / 粘贴文本 `kind=text`，多段），**无需填写任何内容**；服务端按上传时刻经 `WindowResolver` 解析归属窗口 → 取/建当日 `tasks`（`spec_status=placeholder`，`title` 自动生成如「09-09 周三」）
2. **AI 解析**：经 `app/core/ai/` 得「今日任务」草稿 = 学科子任务（学科标签）+ 内容项列表（`task_contents`）；同学科 → 追加内容项（不去重，家长可删）；新学科 → 新增内容项标签；落 `spec_status=parsed`（解析结果写入 `task_contents`）
3. **家长确认**：任务页展示草稿（学科 + 内容项列表）→ 家长确认 → `spec_status=confirmed`
4. **隐式确认（C7）**：亦可在「确认作业完成情况」（M002 判定链）时**一并自动落库**；**前提 = 确认页必须展示"本次将一并落库的任务解析摘要"（学科 + 内容项列表）**，避免盲确认
5. **幂等**：同日重复上传按 §A3 归集（追加内容项 / 新增学科），不新建 `tasks`（唯一键冲突 → 复用当日任务）

- `spec_status` 状态机：`placeholder`（占位主任务，作业/照片先到）→ `parsed`（AI 草稿就绪）→ `confirmed`（家长确认 / 隐式确认）；允许 `placeholder → confirmed`（家长直接确认空/手工）。`title` 可自动生成，家长可改。

### F2 归属引擎 `WindowResolver`（策略接口）

- `resolve(ts) → {belong_date, week_index, window_type, group_key}`
  - `belong_date = (ts − AT_DAY_CUTOFF).date()`（`AT_TIMEZONE`=Asia/Shanghai；时间戳按 UTC 存储，仅在归属计算处转换）——例：9/9 20:00 与 9/10 03:00 同归 **9/9**
  - `week_index` = `AT_TERM_START` **所在周的周一**起算第 N 周
  - `window_type`：周一到周四 `day`；**周五 04:00 ~ 周一 04:00** `weekend`；`AT_TERM_END` 之后 `holiday`（按自然周）
  - `group_key`：`day` → `belong_date`；`weekend` → 周末聚合键（如 `W:2026-09-11`）；`holiday` → 假期周键（如 `H:2026-07-01.W1`）
- **策略接口**（便于替换规则）；读 4 个 `AT_*` 配置（`CONFIGURATION.md`）

### F3 聚合生成与 `policy_version` 锁定

- **每个 `belong_date` 至少一个聚合**（最小聚合 = 1 天）；展示/挂接/判定/（V2）报告走**同一代码路径**，仅成员集合不同
- 写入时 `ensure_group`（幂等）：取/建 `task_groups`（`group_key` + `policy_version` = 生成时生效配置版本）+ 同步 `task_group_subjects`（按 `subject` 合并聚合内内容项）
- **追加数据只新增成员，不改 `policy_version`**（周末聚合周五即可能生成，周六/周日数据追加）

### F4 配置锁定语义（关键，A7/B5）

| 规则 | 内容 |
| --- | --- |
| 影响面 | 配置变更**只影响未聚合对象**；**已聚合按生成时配置**（`task_groups.policy_version`）执行 |
| 锁定粒度 | 每个 `(学生, 聚合对象)` **独立锁**（同一日期：小明走旧配置、小红走新配置） |
| 锁定触发 | **数据写入**（任务解析完成 / 作业照片上传）；**纯浏览不锁**（进列表页只 `ensure_group`，不锁配置） |
| 固化 | `belong_date`/`week_index` **上传时固化**，配置变更**不回算历史** |
| 实现 | `task_groups.policy_version` 于聚合生成时写入，后续追加数据不改该字段；未生成聚合按当前生效配置生成 |

### F5 手工改归属日连锁规则（A8/B8）

① **重算快照**（`belong_date`/`week_index`/聚合成员）；② **迁移主表 FK**（目标聚合无则建）；③ **源聚合变空则删**；④ **已被完成分析消费的作业禁改**（`task_group_subjects.conclusion_status = confirmed` → **V1 直接拒绝**）；⑤ **记审计**（操作人 / 原值→新值 / 时间）；⑥ **跨聚合迁移须同步更新 `photo_subject_links` 的挂接目标**（由 M002 提供的内部接口执行，M001 在事务编排中调用）。

## Data Ownership

- **DATA-001**（`tasks`；`task_items` Deprecated）、**DATA-002**、**DATA-011**、**DATA-012**（`task_groups`）、**DATA-013**（`task_group_subjects`）、**DATA-014**（`task_contents`）、**DATA-015**（`task_spec_sources`）Owner = **M001**；唯一写入口，其他模块只读消费
- **例外**：`task_group_subjects.conclusion`/`conclusion_status` 由 **M002 提供结论值**，但**写入必须经 M001 内部接口**（`TaskAggregationService.commit_conclusion`），M002 不得直写
- DATA-011（`schools`，全局共享只读）由 M001 承载：仅初始化 seed 写入，运行期无写路径；任何模块/用户均不得运行期增删改（ADR-008）
- **不拥有**：DATA-016/017（挂接 / 完成分析，Owner = M002）、DATA-018（窗口策略配置，Owner = 共享配置，M001 只读）、DATA-009（AI 调用记录，`app/core/ai/` 写入）
- 详见 `MODULE_DATA.md` / `DATA_MODEL.md`

## Configuration

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `AT_TIMEZONE` | `Asia/Shanghai` | 归属日 / 周次计算时区（固定，不跟随设备） |
| `AT_TERM_START` | 部署侧填写 | 学期开始日（`week_index` 起算 = 该日所在周的周一） |
| `AT_TERM_END` | 部署侧填写 | 学期结束日（区间外 = 假期，V1 按自然周聚合） |
| `AT_DAY_CUTOFF` | `04:00` | 归属日边界；`belong_date = (ts − cutoff).date()` |
| `window policy` | 周五~周日合并 / 假期自然周 | 窗口聚合规则（带生效日期，变更不回溯） |
| `task.status_flow` | `draft→published→in_progress→closed` | 任务状态机（非法迁移拒绝） |
| `spec_status.flow` | `placeholder→parsed→confirmed` | 解析状态机 |
| `subject.recommended` | `chinese/math/english` | V1 建议学科值（ASM-011），不写死 |
| `category.enum` | `school` | 任务类型（V1 仅 school，字段预留多任务类型 V2） |
| `school.stage.recommended` | `primary/junior/senior` | 学校学段建议值（ADR-008） |
| `pagination.default` | `page_size=20, max=100` | 列表分页 |
| `auth.session_ttl` | 30 天 | 会话有效期 |
| `security.password_hash` | scrypt（标准库） | 密码单向哈希，禁止明文/可逆存储 |

> 归属/窗口类配置的**生效与锁定规则**见 §F4（`CONFIGURATION.md` §一）。

## Security

- 认证：注册/登录获取**不透明会话 token**（存储仅存 token 哈希，不存原文）
- 授权：所有业务请求经 Bearer token 解析出 `family_id` 注入上下文；**家庭数据的一切 M001 查询强制按 `family_id` 过滤**，跨家庭访问统一 403。**例外**：`schools` 为全局共享公共只读字典，登录即可查询，不做家庭过滤（ADR-008）
- 密码：scrypt + 每账号随机盐；禁止明文落库/落日志
- 敏感数据：未成年学生档案、任务内容项文本、输入源文本不写普通日志；日志脱敏（`DEVELOPMENT_GUIDE.md` §7）
- 登录防爆破：失败计数 + 渐进退避（`family:` / `student:` 命名空间隔离）
- 输入源图片：M001 仅存**引用**（`task_spec_sources.photo_id`，归属 M002 受控存储），不携带图片本体；受控取图走 M002 鉴权端点
- CORS/输入校验：FastAPI + Pydantic 严格校验；请求体大小限制

## Performance

- V1 单家庭低并发（单机 SQLite，ADR-004）；登录哈希与 AI 解析为较重操作（AI 经 `app/core/ai/`，超时降级）
- 索引：`tasks(student_id, category, belong_date)`（UNIQUE）、`tasks(family_id, student_id, belong_date)`、`task_contents(task_id)`、`task_spec_sources(task_id)`、`task_groups(student_id, category, group_key)`（UNIQUE）、`task_group_subjects(group_id, subject)`（UNIQUE）、`students(family_id)`、`students(school_id)`、`schools(name, stage)`（UNIQUE）、`auth_sessions(token_hash)`
- 列表默认倒序（新在前），分页上限 100
- `ensure_group` 幂等且仅在写入路径触发（纯浏览不触发锁定）

## Failure Behavior

| 场景 | 行为 |
| --- | --- |
| 参数/模型校验失败 | 400/422，错误体 `ErrorResponse{code,message,request_id}`（含 `school_id` 缺失/不存在、`group_no` 旧字段 → 弃用提示） |
| 未登录/会话过期 | 401 |
| 跨家庭访问/无权 | 403 |
| 资源不存在 | 404 |
| 唯一键冲突（同日同类型任务已存在） | 409（**或按 §F1 幂等复用**，由端点语义决定）；非法状态迁移/冲突 → 409（附当前状态） |
| AI 解析失败/超时 | 任务保留 `placeholder`（或 `parsed` 仅含已得结果）+ 提示家长**手工录入内容项**；**降级不阻断事实层写入** |
| 已消费聚合生效时改归属日 | 409（拒绝，§F5④） |
| 存储故障 | 500 + 完整请求日志（含 request_id），客户端可见统一错误体 |
| 一致性 | 任务 + 输入源 + 内容项（+ 幂等聚合生成）在**同一事务**内完成，失败整体回滚；改归属日连锁在单事务内完成（含 M002 挂接迁移回调） |

## Version / Compatibility

- **破坏性变更清单（v0.1.2 → v0.2.0）**：① `tasks` 唯一键 `(family_id,…)` → **`(student_id, category, belong_date)`**；② `task_items` 与「学科作业段 `group_no`」**作废**；③ `tasks.subject`/`content` **Deprecated**；④ 新增 5 张表（`task_contents`/`task_spec_sources`/`task_groups`/`task_group_subjects`）；⑤ 任务创建由"手工录入题目"改为"输入源解析"；⑥ 内部接口 `get_task_group(s)`/`can_accept_photo`（段级）**语义作废**，改为窗口/聚合级
- **兼容性**：V1 无历史生产数据，开发库直接演进（`CHANGE-003` §5）；旧表 `task_items` 保留以兼容旧数据与回滚，不提供兼容读契约
- 任何后续修改走 CR/ACR（`ID_GOVERNANCE.md`）

## 签署区（批准记录）

| 角色 | 结论 | 日期 | 签名 |
| --- | --- | --- | --- |
| 用户（决策者） | **批准（Frozen）** | 2026-09-10 | 用户 |
| Project Master | **复核 APPROVED**（Task-004 交付物；API ID 分配登记、`DATA_MODEL` 字段级同步） | 2026-09-10 | Project Master |

> **v0.2.0 已于 2026-09-10 由用户批准并冻结（Frozen）**；② 契约修订评审（`CHANGE-003` ②，Task-004）关闭，③ 实施（`Task-007`）依据本定稿启动（Contract First 前置已满足）。前版 v0.1.1 为 Frozen 基线（2026-09-08 用户批准），v0.1.2 为 CHANGE-001 Applied 定稿。
