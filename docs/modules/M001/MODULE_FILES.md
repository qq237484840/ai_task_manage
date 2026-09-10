# M001 文件级知识（L6）—— 作业任务管理

- **状态**：**契约 v0.2.0（Frozen，用户批准 2026-09-10）**；**代码基线 = v0.2.0（③ 实施 `Task-007` 已交付，2026-09-10）**，全仓 `204 passed`（M001 相关 101，基线 89 未回归）。下表 **①/②** 已由 PM 按实施实况核对（偏差处显式标注）。

## 工程根结构（FastAPI 单体 + Vue3 前端构建产物托管，ADR-004/ADR-012）

```text
backend/                      FastAPI 后端（API + 前端静态托管）
  requirements.txt            Python 依赖清单（fastapi/sqlalchemy/uvicorn/pydantic-settings/pytest/httpx/pillow/python-multipart/**tzdata**）
  pytest.ini                  测试配置（testpaths=tests, pythonpath=.）
  app/
    main.py                   应用装配：create_app() 工厂、/api/v1 路由、静态托管、统一异常处理器、lifespan 建表+seed
    core/
      config.py               pydantic-settings（前缀 AT_）：库路径、scrypt、会话 TTL、分页、**AT_TIMEZONE/AT_TERM_START/AT_TERM_END/AT_DAY_CUTOFF**
      database.py             SQLAlchemy engine/session；SQLite PRAGMA foreign_keys=ON 事件钩子
      seed.py                 schools 字典 seed（幂等，ADR-008）
      logging.py              日志配置、audit_event、RequestIdMiddleware
      times.py                iso_from / iso_plus（UTC 时间工具）
      ai/                     **LLM 接入层（横切，执行方 AGENT-AI/Task-006）**：provider 抽象 + prompt 管理 + 结果 schema 校验 + 降级
    shared/
      security.py             scrypt 密码哈希、会话令牌生成 + sha256
      auth.py                 AuthContext(family_id, session_id, subject_type, student_id)、Bearer 解析、爆破退避
      exceptions.py           层级化 AppError + ErrorResponse
    api/v1/
      deps.py                 router 公共依赖（双主体 AuthContext 注入、分页参数）
      family.py               注册/登录/登出（API-M001-001~003）
      student_auth.py         学生登录/登出/主体信息（API-M001-015~017）
      students.py             学生档案 CRUD（API-M001-004~006）+ 子账号开通/更新（013/014）
      tasks.py                任务路由（API-M001-007~011 + **018 解析结果确认** + **021 手工改归属日**；v0.2.0 已落地）
      task_groups.py          **新增**：聚合任务列表（**019**）/详情（**020**）路由
      （belong_date.py 未建）   **实现偏差**：021 手工改归属日路由并入 `tasks.py`（PM 认可，本表按实况更正）
      schools.py              学校字典只读列表（API-M001-012）
    modules/m001/             M001 业务内聚（models/repositories/services/schemas）
      models/orm.py           ORM：family_accounts/schools/students/student_accounts/auth_sessions/tasks/**task_contents**/**task_spec_sources**/**task_groups**/**task_group_subjects**；`task_items` 保留（Deprecated）
      repositories/
        account_repo.py       family_accounts/student_accounts/auth_sessions 读写
        student_repo.py       students 读写（强制 family_id；join schools）
        school_repo.py        schools 只读查询（公共字典，无 family_id）
        task_repo.py          tasks/**task_contents**/**task_spec_sources** 读写（强制 family_id；唯一键 (student_id,category,belong_date)）
        group_repo.py         **新增**：task_groups/task_group_subjects 读写（UNIQUE(student_id,category,group_key) / UNIQUE(group_id,subject)）
      services/
        family_space.py       FamilySpaceService + StudentService
        student_account_service.py  StudentAccountService（ACR-001）
        task_service.py       TaskService（ingest/confirm_parse/update/list/detail + change_belong_date）+ TaskQueryService（事实层+聚合层）
        window_resolver.py    **新增**：`WindowResolver` 策略接口 + `DefaultWindowResolver`（belong_date/week_index/window_type/group_key）
        aggregation_service.py **新增**：`TaskAggregationService.ensure_group/commit_conclusion/migrate_links_hook` + `register_links_migration_hook`（M002 注册式回调；**M001 不反向 import M002**）
        task_group_service.py **新增**：`TaskGroupService`（= `TaskAggregationService` 契约命名别名 + 聚合查询）
        task_parser.py        **新增**：链路 T 解析（`app/core/ai/` 就绪时优先调用，否则 Mock 兜底）
        task_state.py         TaskStateService（状态机 transition/mark_in_progress）
      schemas/
        common.py             分页参数与通用校验
        family.py / school.py / student.py / student_account.py  （不变）
        task.py               TaskDTO/ContentItemDTO/SourceDTO/Create(输入源)/Update
        task_group.py         **新增**：TaskGroupDTO/TaskGroupSubjectDTO/WindowInfo
frontend/                     **Vue3 + Vite + TS + Vant 4 前端工程（ADR-012）**
  src/                        views（含「作业」改名 + 周次/周末分组；任务解析确认）+ components + api + stores + router + styles
  dist/                       Vite 构建产物（FastAPI 托管目标，不入库）
backend/tests/
  conftest.py                 每用例独立 SQLite、双家庭 fixture、scrypt 参数加速
  _m001_helpers.py            **新增**：M001 用例共享助手（输入源上传/确认/聚合构造）
  unit/                       test_school_seed / test_security / test_task_validation / **test_window_resolver（新增）** / **test_task_parser（新增）**
  integration/                test_internal_services（**聚合层与内部接口用例并入此文件**，未另建 test_aggregation.py）
  api/                        test_family_api / test_schools_api / test_students_api / test_tasks_api / test_isolation / test_student_accounts_api / test_task_container_api / **test_parse_confirmation_api（018）** / **test_task_belong_date_api（021）**
backend/data/                 运行时数据目录（SQLite 文件 + 图片目录；.gitignore）
```

## ① 既有实现（实况，v0.1.2）

| 文件 | 职责（实现实况） | Exports | Modification Risk |
| --- | --- | --- | --- |
| `services/task_service.py` | 任务 CRUD 与题目集单事务写、group_no 结构校验、冻结规则、`include_answers` 遮蔽、双主体 scope、`TaskQueryService`（含段级查询） | `TaskService.*`、`TaskQueryService.*` | **高**（本次整体重构） |
| `services/task_state.py` | 任务状态机唯一实现（`_TRANSITIONS` 表驱动；`mark_in_progress` 幂等） | `TaskStateService.transition/mark_in_progress` | 高（非法迁移 409 语义与 M002 首传推进耦合） |
| `services/family_space.py` / `student_account_service.py` | 档案归属 + school_id 双保险；子账号开通/停用/改密 | `StudentService`、`FamilySpaceService`、`StudentAccountService` | 中（**v0.2.0 不变**） |
| `repositories/*_repo.py` | 数据访问；family_id 过滤第一防线（school_repo 例外） | `StudentRepo`/`TaskRepo`/`AccountRepo`/`SchoolRepo` | 高（裸查询 = 数据越权，RISK-004） |
| `shared/security.py` / `auth.py` | scrypt、令牌 sha256、双主体 AuthContext、爆破退避 | `hash_password/verify_password`、`resolve_auth`、`AuthContext` | 高（安全基座；**v0.2.0 不变**） |
| `shared/exceptions.py` | 统一异常层级 + ErrorResponse | `AppError` 子类、`to_error_response` | 高（全模块依赖） |
| `core/database.py` / `config.py` / `seed.py` / `logging.py` | engine/session、集中配置、schools seed、审计与 request_id | `build_engine`、`Settings`、`seed_schools`、`audit_event` | 中（config 需加 4 个 `AT_*`） |
| `models/orm.py` | 7 表定义（含 `student_accounts`、`auth_sessions.subject_type`、`task_items.group_no`） | ORM 模型类 | 中→**高**（v0.2.0 增 4 表 + `tasks` 改键） |
| `api/v1/*.py` | REST 端点薄层 | 各 router | 低-中（契约冻结，改动须 CR） |
| `frontend/src/**` | 前端 SPA（Vue3+Vite+TS+Vant4，ADR-012）；**任务域已按 v0.2.0 改造**：`api/types.ts`、`api/index.ts`、`utils/format.ts`、`views/TaskListView.vue`、`TaskDetailView.vue`、`TaskEditorView.vue`（拍照/粘贴 → 草稿确认 + 改归属日 + 归属日/周次展示） | — | 低（REST 为唯一契约面） |
| `tests/` | **101 项 M001 用例**（全仓 204；基线 89 未回归） | conftest fixtures、`_m001_helpers.py` | 低（回归保障；改契约须同步） |

## ② v0.2.0 实施落盘核对（③ `Task-007` 已交付，2026-09-10）

| 文件 | 动作 | 说明 |
| --- | --- | --- |
| `services/window_resolver.py` | **新增** | `WindowResolver` 协议 + `DefaultWindowResolver`（A5）；读 4 个 `AT_*` 配置 |
| `services/aggregation_service.py` | **新增** | `ensure_group`（幂等，写 `policy_version`）/`commit_conclusion`（M002 结论回写）/`migrate_links_hook`（A6/A7/A8） |
| `services/task_service.py` | **重构** | `create(items)` → `ingest(sources)` + `confirm_parse` + `change_belong_date`；`TaskQueryService` 改为事实层 + 聚合层（去段级） |
| `models/orm.py` | **改造** | `tasks` 加 `category`/`belong_date`/`week_index`/`window_type`/`spec_status` + 唯一键；新增 `task_contents`/`task_spec_sources`/`task_groups`/`task_group_subjects`；`tasks.subject`/`content` 与 `task_items` 标 Deprecated |
| `repositories/task_repo.py` / `group_repo.py` | **改造 / 新增** | 事实层按天唯一；聚合读写 |
| `schemas/task.py` / `task_group.py` | **改造 / 新增** | 输入源/内容项/聚合 DTO |
| `api/v1/tasks.py` / `task_groups.py` | **已落地** | 修订 007~010 + `018`（tasks.py）+ `019/020`（task_groups.py）+ `021`（tasks.py）；**`belong_date.py` 未建（偏差）** |
| `core/config.py` | **改造** | 加 `AT_TIMEZONE`/`AT_TERM_START`/`AT_TERM_END`/`AT_DAY_CUTOFF` |
| `core/ai/`（M001 侧调用点） | **对接** | 经 `app/core/ai/` 解析（Mock 注入测试；真实三方默认 ADR-011） |
| `frontend/src/**` | **已落地（任务域）** | 任务域：拍照/粘贴输入源 → 草稿确认/修正 + 改归属日 + 归属日/周次展示；**遗留（后续独立任务）**：`PhotoListView.vue` 照片域挑选器需改接 v0.4.0 `/links` + `group_subject_id`，「照片」→「作业」改名 + 周次/周末分组展示 |
| `tests/**` | **已落地** | 101 项 M001（89 基线不回归）+ 归属边界/周次/周末聚合/唯一键/配置锁定按学生隔离/聚合幂等/改归属日连锁/链路 T 确认与隐式确认（见 `MODULE_TEST.md`） |

## 维护要求

- 方法级（L7）覆盖核心方法：`TaskService.ingest/confirm_parse/change_belong_date`、`WindowResolver.resolve`、`TaskAggregationService.ensure_group/commit_conclusion`、`TaskStateService.transition/mark_in_progress`、认证注入（见 `MODULE_DESIGN.md`）
- 任何文件增删/改名必须同步本表与 `MODULE_SUMMARY.md`（索引一致性要求）
