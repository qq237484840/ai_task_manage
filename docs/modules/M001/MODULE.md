# M001 模块总览 —— 作业任务管理

- **Module ID**：M001（对应需求原文 M01）
- **状态**：Stable（2026-09-08 PM 按 DoD 验收 APPROVED，Task-001 交付；**CHANGE-001 编码完成待 PM 复核**，2026-09-08）
- **版本**：v0.1.1（2026-09-08 批准，契约基线 Frozen）；CHANGE-001 执行回填（CR-001/CR-002/ACR-001/ACR-002）→ 收口定稿 v0.1.2
- **Domain**：作业评定
- **Owner Agent**：AGENT-M001
- **文档目录**：`docs/modules/M001/`

## Purpose

V1 的**基座模块**：承载"家庭空间与作业任务"这一入口域。依 ADR-005（纯家庭模式）+ ADR-009（**两级主体**），M001 同时拥有：
1. **家庭空间**：家庭账号（家长）注册/登录/会话、学生档案维护、**学生子账号**（家长开通，学生独立登录仅本人，ACR-001）；档案必填关联学校（全局共享学校字典 DATA-011，ADR-008）
2. **作业任务生命周期**：创建/查看/更新/状态推进，题目逐题建模（**多学科登记单容器 CR-001**：学科粒度 = `(subject, group_no)`；题型标注；`reference_answer` 为**非判定基准辅助字段** ADR-010）

家庭业务数据归属 `family_id`，M001 是 V1 家庭级数据隔离的第一道边界；**例外**：学校基础字典（DATA-011）为全局共享只读公共数据，不归属家庭（ADR-008）。student 会话在 family 底线之上强制本人（授权矩阵见 `MODULE_DESIGN.md`）。

## Responsibilities

- 家庭账号注册、登录、登出与会话管理（安全哈希存储）；学生子账号开通/停用/改密与学生登录（ACR-001，见 `MODULE_API.md`）
- 学生档案创建/列表/更新（档案归属当前家庭，跨家庭/他人越权 404 防探测；创建/更新必须携带存在的 `school_id`）
- 提供**学校基础字典（全局共享只读）查询**：`GET /schools` 按学段/关键词过滤，作为建档下拉数据源（ADR-008；V1 仅 seed 预置数据，无运行期维护 API）
- 作业任务创建/列表/详情/更新（含题目集：`subject`、`group_no` 学科作业段、`item_type` 题型标注、客观题可选非基准 `reference_answer`）；student 主体可为本人创建任务
- 任务状态机推进：`draft → published → in_progress → closed`（发布后可被学生视角查看/上传；开始上传后不可改题目，防基准漂移）
- 对外暴露任务与档案的查询入口，供 M002/M004/M005/M007 与本模块 UI 使用
- 作为 V1 认证基础设施的账号数据源（登录校验、主体上下文注入由 shared 认证层完成，账号数据读写归 M001）

## Non-Responsibilities

- 不采集/不存储作业图片（M002）；不做图像质检、识别（M003）、匹配（M004）、评分（M005）、评语（M006）、报告（M007）
- 不生成报告内容；不聚合跨日历史
- 不做班级/学校管理域/多教师/审批流（ADR-002/005/008 明确禁止；全局共享只读学校基础字典 DATA-011 为限定例外，非学校管理域，见 ADR-008）
- 不实现学校字典的后台维护功能（新建/改名/停用等 V1 不开发，仅预留边界）
- 不调用任何 AI Provider（属共享 AI 抽象层，M001 全程无 AI 调用，不产生 DATA-009）
- 不实现多租户/数据跨家庭共享；学生子账号之外不引入任何新角色（ADR-002/009）

## Dependencies

- 业务模块：**无**（M001 是第一个编码模块，无业务依赖；登录/认证校验基础属 shared/infrastructure，先于或伴随 M001 落地）
- 共享/基础设施：日志、异常与错误体、配置、数据库/存储访问、密码哈希与会话工具、**双主体上下文鉴权依赖注入（AuthContext: family/student）**

## Consumers

| 消费者 | 用途 | 消费方式 |
| --- | --- | --- |
| M002 图片采集 | 校验任务存在与可上传状态、学科作业段归属（subject+group_no）、学生档案归属；上传完成后推进任务到 in_progress | 内部服务接口 `TaskQueryService`（含 `get_task_group`/`can_accept_photo`）/`TaskStateService` |
| M004 任务匹配 | 读取任务学科作业段题目序号/题干（不含答案亦可） | 内部服务接口 |
| M005 质量评价 | 读取题目 + 客观题 `reference_answer`（辅助字段） | 内部服务接口（include_answers=true，同一家庭上下文） |
| M007 报告 | 读取任务基本信息、学生档案（含学校，ADR-008）、状态 | 内部服务接口 |
| H5 UI | 家长/学生双入口注册登录、档案与任务的全部操作；建档时学校下拉（`GET /schools`） | REST API（`MODULE_API.md`） |

## Owned Data

| 数据实体 | 说明 | 权威源 |
| --- | --- | --- |
| DATA-001 作业任务 | `tasks`（多学科登记单容器）+ `task_items`（题目集/学科作业段 group_no/辅助参考答案） | `MODULE_DATA.md` |
| DATA-002 用户档案 | `family_accounts`（家长）+ `students` + `student_accounts`（学生子账号）+ `auth_sessions`（family/student 两型会话） | `MODULE_DATA.md` |
| DATA-011 学校字典 | `schools`（全局共享只读，seed 预置；仅初始化写，运行期无写路径） | `MODULE_DATA.md` |

写入规则：DATA-001/DATA-002 的**唯一写入口为 M001**；其他模块只能经 M001 服务接口/API 读取，禁止直改 M001 数据表（`DEVELOPMENT_GUIDE.md` §7 数据 Ownership）。DATA-011 运行期无人可写（无写 API），仅初始化 seed。

## Exposed Services

- **REST API**（前缀 `/api/v1`）：家庭认证、学生子账号（ACR-001 新增）、学校字典、学生档案、作业任务（清单见 `MODULE_API.md`；API-M001-001~012 Frozen 面 + ACR-001 新增端点待编号）
- **内部服务接口**（进程内 Python Interface，供同进程其他模块调用）：`FamilySpaceService`、`TaskQueryService`（含 CR-001 段级查询）、`TaskStateService`（方法级契约见 `MODULE_API.md` §内部接口）

## Forbidden Access

- 其他模块不得直接读/写 M001 拥有的数据表或绕过 M001 接口
- 禁止在 M001 之外为家庭/学生/任务创建旁路写入点（数据一致性与归属校验只在 M001 一处）
- M001 家庭数据访问一律带 `family_id` 强制过滤；student 主体场景再带 `student_id` 本人过滤；未带归属上下文的裸查询视为缺陷（`schools` 公共只读查询除外）
