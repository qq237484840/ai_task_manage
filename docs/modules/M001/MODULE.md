# M001 模块总览 —— 作业任务管理

- **Module ID**：M001（对应需求原文 M01）
- **状态**：Developing（Task-001 编码中；契约 v0.1.1 已批准 Frozen）
- **版本**：v0.1.1（2026-09-08 批准，契约基线）
- **Domain**：作业评定
- **Owner Agent**：AGENT-M001
- **文档目录**：`docs/modules/M001/`

## Purpose

V1 的**基座模块**：承载"家庭空间与作业任务"这一入口域。依 ADR-005（纯家庭模式），M001 同时拥有：
1. **家庭空间**：家庭账号注册/登录/会话、学生档案维护（DATA-002，V1 身份模型的全部账号侧）；档案必填关联学校（全局共享学校字典 DATA-011，ADR-008）
2. **作业任务生命周期**：创建/查看/更新/状态推进，题目逐题建模（学科/题型/客观题参考答案，ADR-006），是评分对照基准来源（DATA-001）

家庭业务数据归属 `family_id`，M001 是 V1 家庭级数据隔离的第一道边界；**例外**：学校基础字典（DATA-011）为全局共享只读公共数据，不归属家庭（ADR-008）。

## Responsibilities

- 家庭账号注册、登录、登出与会话管理（安全哈希存储，见 `MODULE_DESIGN.md`）
- 学生档案创建/列表/更新（档案归属当前家庭，跨家庭越权返回 403；创建/更新必须携带存在的 `school_id`）
- 提供**学校基础字典（全局共享只读）查询**：`GET /schools` 按学段/关键词过滤，作为建档下拉数据源（ADR-008；V1 仅 seed 预置数据，无运行期维护 API）
- 作业任务创建/列表/详情/更新（含题目集，题目含 `subject`、`item_type`（objective|subjective）、客观题可选 `reference_answer`）
- 任务状态机推进：`draft → published → in_progress → closed`（发布后可被学生档案视角查看/上传；开始上传后不可改题目，防评分基准漂移）
- 对外暴露任务与档案的查询入口，供 M002/M004/M005/M007 与本模块 UI 使用
- 作为 V1 认证基础设施的账号数据源（登录校验、`family_id` 注入由 shared 认证层完成，账号数据读写归 M001）

## Non-Responsibilities

- 不采集/不存储作业图片（M002）；不做图像质检、识别（M003）、匹配（M004）、评分（M005）、评语（M006）、报告（M007）
- 不生成报告内容；不聚合跨日历史
- 不做班级/学校管理域/多教师/审批流（ADR-002/005/008 明确禁止；全局共享只读学校基础字典 DATA-011 为限定例外，非学校管理域，见 ADR-008）
- 不实现学校字典的后台维护功能（新建/改名/停用等 V1 不开发，仅预留边界）
- 不调用任何 AI Provider（属共享 AI 抽象层，M001 全程无 AI 调用，不产生 DATA-009）
- 不实现多租户/数据跨家庭共享

## Dependencies

- 业务模块：**无**（M001 是第一个编码模块，无业务依赖；登录/认证校验基础属 shared/infrastructure，先于或伴随 M001 落地）
- 共享/基础设施：日志、异常与错误体、配置、数据库/存储访问、密码哈希与会话工具、家庭上下文鉴权依赖注入（AuthContext）

## Consumers

| 消费者 | 用途 | 消费方式 |
| --- | --- | --- |
| M002 图片采集 | 校验任务存在与可上传状态、学生档案归属；上传完成后推进任务到 in_progress | 内部服务接口 `TaskQueryService`/`TaskStateService` |
| M004 任务匹配 | 读取任务题目序号/题干（对照基准，不含答案亦可） | 内部服务接口 |
| M005 质量评价 | 读取题目 + 客观题参考答案（判定基准） | 内部服务接口（include_answers=true，同一家庭上下文） |
| M007 报告 | 读取任务基本信息、学生档案（含学校，ADR-008）、状态 | 内部服务接口 |
| H5 UI | 注册/登录、档案与任务的全部操作；建档时学校下拉（`GET /schools`） | REST API（`MODULE_API.md`） |

## Owned Data

| 数据实体 | 说明 | 权威源 |
| --- | --- | --- |
| DATA-001 作业任务 | `tasks` + `task_items`（题目集/参考答案） | `MODULE_DATA.md` |
| DATA-002 用户档案 | `family_accounts` + `students` + `auth_sessions`（家庭账号/学生档案/会话） | `MODULE_DATA.md` |
| DATA-011 学校字典 | `schools`（全局共享只读，seed 预置；仅初始化写，运行期无写路径） | `MODULE_DATA.md` |

写入规则：DATA-001/DATA-002 的**唯一写入口为 M001**；其他模块只能经 M001 服务接口/API 读取，禁止直改 M001 数据表（`DEVELOPMENT_GUIDE.md` §7 数据 Ownership）。DATA-011 运行期无人可写（无写 API），仅初始化 seed。

## Exposed Services

- **REST API**（前缀 `/api/v1`）：家庭认证、学校字典、学生档案、作业任务（清单见 `MODULE_API.md`，API-M001-001~012）
- **内部服务接口**（进程内 Python Interface，供同进程其他模块调用）：`FamilySpaceService`、`TaskQueryService`、`TaskStateService`（方法级契约见 `MODULE_API.md` §内部接口）

## Forbidden Access

- 其他模块不得直接读/写 M001 拥有的数据表或绕过 M001 接口
- 禁止在 M001 之外为家庭/学生/任务创建旁路写入点（数据一致性与归属校验只在 M001 一处）
- M001 家庭数据访问一律带 `family_id` 强制过滤；未带归属上下文的裸查询视为缺陷（`schools` 公共只读查询除外）
