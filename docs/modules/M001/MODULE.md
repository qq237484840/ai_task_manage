# M001 模块总览 —— 作业任务管理

- **Module ID**：M001（对应需求原文 M01）
- **状态**：Stable（代码基线 v0.1.2）→ **契约 v0.2.0 —— Frozen（用户批准 2026-09-10）**（`Task-004` 交付并经 PM 复核 APPROVED；依据 `CR-003`/`ADR-013`/`REQ-010`；③ 实施 = **`Task-007`**）
- **版本**：**v0.2.0（草案）**（2026-09-10 按 CR-003 修订：事实层按天 + 聚合层跨天 + 链路 T 解析；取代 v0.1.2 的"多学科登记单容器 / 学科作业段 / 逐题条目"语义）
- **Domain**：作业评定
- **Owner Agent**：AGENT-M001
- **文档目录**：`docs/modules/M001/`
- **权威源**：`docs/requirements/CLARIFICATION-2026-09-10.md`（冲突时以其为准）、`REQ-010`、`ADR-013`、`CONFIGURATION.md`

## Purpose

V1 的**基座模块**：承载"家庭空间 + 按天作业任务（布置）解析"入口域。依 ADR-005（纯家庭模式）+ ADR-009（**两级主体**）+ **ADR-013（双层模型：按天事实层 + 跨天聚合层）**，M001 同时拥有：

1. **家庭空间**：家庭账号（家长）注册/登录/会话、学生档案维护、**学生子账号**（家长开通，学生独立登录仅本人，ACR-001）；档案必填关联学校（全局共享学校字典 DATA-011，ADR-008）
2. **链路 T（任务解析）**：菜单「任务」上传输入源（图片 / 粘贴文本，多段 `task_spec_sources`）→ AI（`app/core/ai/`）解析「今日任务」→ 子任务（学科）+ 内容项草稿 → 家长确认 / 隐式确认（`spec_status`）
3. **事实层（按天）**：`tasks` 唯一键 **`(student_id, category, belong_date)`**；只承载"哪天布置了什么"，**不承载判定**
4. **聚合层（跨天）**：`task_groups` → `task_group_subjects`（**★判定单元**）；每个 `belong_date` 至少一个聚合，展示/挂接/判定/报告走同一代码路径

家庭业务数据归属 `family_id`，M001 是 V1 家庭级数据隔离的第一道边界；**例外**：学校基础字典（DATA-011）为全局共享只读公共数据，不归属家庭（ADR-008）。student 会话在 family 底线之上强制本人（授权矩阵见 `MODULE_DESIGN.md`）。

## Responsibilities

- 家庭账号注册、登录、登出与会话管理（安全哈希存储）；学生子账号开通/停用/改密与学生登录（ACR-001，见 `MODULE_API.md`）
- 学生档案创建/列表/更新（档案归属当前家庭，跨家庭/他人越权 404 防探测；创建/更新必须携带存在的 `school_id`）
- 提供**学校基础字典（全局共享只读）查询**：`GET /schools` 按学段/关键词过滤（ADR-008；V1 仅 seed 预置数据，无运行期维护 API）
- **链路 T 任务解析**：接收输入源（图片 / 粘贴文本多段）→ 调用 `app/core/ai/` 得解析草稿 → `task_contents` 内容项 + 学科子任务草稿 → 家长确认/隐式确认（`spec_status`）
- **归属引擎 `WindowResolver`**：计算 `belong_date`（`AT_DAY_CUTOFF` 日界 / `AT_TIMEZONE`）+ `week_index`（`AT_TERM_START`/`AT_TERM_END`）+ `window_type`（`day|weekend|holiday`）；周末 = 周五 04:00 ~ 周一 04:00；假期按自然周
- **事实层与聚合层写入与查询**：`tasks`（按天唯一）+ `task_contents` + `task_spec_sources`；幂等生成 `task_groups`/`task_group_subjects`（含 `policy_version` 锁定）；**手工改归属日连锁规则**
- 任务状态机推进：`draft → published → in_progress → closed`（发布后可被学生视角查看）
- 对外暴露任务/聚合/档案查询入口，供 M002 及（V2）M005/M007 与本模块 UI 使用
- 作为 V1 认证基础设施的账号数据源（登录校验、主体上下文注入由 shared 认证层完成，账号数据读写归 M001）

## Non-Responsibilities

- 不采集/不存储作业图片（M002）；不做图像质检/归一/受控存储（M002）
- **不做挂接建议、逐张复核、窗口级门控、完成情况分析**（链路 H，归 M002；`ADR-014` 决议 1）
- 不做评分（M005，V2）、评语（M006，V2）、报告（M007，V2）
- 不做内容项级判定（V2）；不维护参考答案基准（端到端直判，ADR-013 继承 ADR-010 原则）
- 不做班级/学校管理域/多教师/审批流（ADR-002/005/008 明确禁止；全局共享只读学校基础字典 DATA-011 为限定例外，非学校管理域，见 ADR-008）
- 不实现学校字典的后台维护功能（新建/改名/停用等 V1 不开发，仅预留边界）
- **不直接调用 AI Provider**：AI 能力统一经 `app/core/ai/`（执行方 `AGENT-AI`/Task-006）调用，M001 只持有链路 T 的解析编排与结果落库
- 不实现多租户/数据跨家庭共享；学生子账号之外不引入任何新角色（ADR-002/009）

## Dependencies

- 业务模块：**无**（M001 是第一个编码模块，无业务依赖）
- 共享/基础设施：日志、异常与错误体、配置、数据库/存储访问、密码哈希与会话工具、**双主体上下文鉴权依赖注入（AuthContext: family/student）**、**LLM 接入层 `app/core/ai/`**（链路 T 解析；接口契约由 M001 引用，不分配 API ID）
- 配置：`AT_TIMEZONE` / `AT_TERM_START` / `AT_TERM_END` / `AT_DAY_CUTOFF`（`CONFIGURATION.md`；生效与锁定规则见契约）

## Consumers

| 消费者 | 用途 | 消费方式 |
| --- | --- | --- |
| M002 作业采集与挂接 | 校验任务存在与可上传状态、**归属窗口**（`belong_date`/聚合）、聚合学科子任务清单（挂接目标）、学生档案归属；上传后**幂等** `ensure_group`/推进任务 | 内部服务接口 `TaskQueryService`/`WindowResolver`/`TaskStateService` |
| M002 完成分析 | 读取聚合子任务与内容项（判定对象）、回写结论到 `task_group_subjects` | 内部服务接口 |
| （V2）M005/M007 | 读取任务/聚合/学生档案（含学校） | 内部服务接口（**V1 不启用**，ADR-014 决议 2） |
| H5 UI | 家长/学生双入口注册登录、档案与任务的全部操作；任务页确认解析摘要 | REST API（`MODULE_API.md`） |

## Owned Data

| 数据实体 | 说明 | 权威源 |
| --- | --- | --- |
| DATA-001 作业任务（**事实层按天**） | `tasks`（唯一键 `(student_id, category, belong_date)`）；`task_items` **Deprecated** | `MODULE_DATA.md` |
| DATA-002 用户档案 | `family_accounts` + `students` + `student_accounts` + `auth_sessions` | `MODULE_DATA.md` |
| DATA-011 学校字典 | `schools`（全局共享只读，seed 预置；仅初始化写，运行期无写路径） | `MODULE_DATA.md` |
| DATA-012 聚合任务 | `task_groups`（含 `policy_version` 锁定） | `MODULE_DATA.md` |
| DATA-013 聚合学科子任务 | `task_group_subjects`（**★判定单元**） | `MODULE_DATA.md` |
| DATA-014 任务内容项 | `task_contents`（V1 只读展示，不参与挂接/判定） | `MODULE_DATA.md` |
| DATA-015 任务输入源 | `task_spec_sources`（多段：text / image） | `MODULE_DATA.md` |

写入规则：上列数据的**唯一写入口为 M001**；其他模块只能经 M001 服务接口/API 读取，禁止直改 M001 数据表（`DEVELOPMENT_GUIDE.md` §7 数据 Ownership）。DATA-011 运行期无人可写（无写 API），仅初始化 seed。**DATA-016/017（挂接/完成分析）Owner = M002**、**DATA-018（窗口策略配置）Owner = 共享配置（M001 只读）**。

## Exposed Services

- **REST API**（前缀 `/api/v1`）：家庭认证、学生子账号、学校字典、学生档案、**任务（输入源上传 / 解析草稿 / 确认 / 聚合查询）**（清单见 `MODULE_API.md`；API-M001-001~017 既有面 + CR-003 新增端点 **`API-M001-018~021`**）
- **内部服务接口**（进程内 Python Interface，供同进程其他模块调用）：`FamilySpaceService`、`TaskQueryService`（事实层 + **聚合层**）、`TaskStateService`、`WindowResolver`（方法级契约见 `MODULE_API.md` §内部接口）

## Forbidden Access

- 其他模块不得直接读/写 M001 拥有的数据表或绕过 M001 接口
- 禁止在 M001 之外为家庭/学生/任务/聚合创建旁路写入点（数据一致性与归属校验只在 M001 一处）
- M001 家庭数据访问一律带 `family_id` 强制过滤；student 主体场景再带 `student_id` 本人过滤；未带归属上下文的裸查询视为缺陷（`schools` 公共只读查询除外）
- **M002 不得直写 `task_groups`/`task_group_subjects`**：`conclusion`/`conclusion_status` 的回写必须经 M001 内部接口（`TaskAggregationService.commit_conclusion`）
