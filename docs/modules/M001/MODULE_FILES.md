# M001 文件级知识（L6）—— 作业任务管理

- **状态**：已实现 + CHANGE-001 编码回填（Task-001 交付 `54 passed`；CHANGE-001 后 `89 passed`，待 PM 复核）。下表 File/Purpose/Dependencies/Exports/Modification Risk 均为**落盘实况**。

## 工程根结构（FastAPI 单体 + 零构建原生 H5，ADR-004）

```text
backend/                      FastAPI 后端（API + H5 静态托管）
  requirements.txt            Python 依赖清单（fastapi/sqlalchemy/uvicorn/pydantic-settings/pytest/httpx）
  pytest.ini                  测试配置（testpaths=tests, pythonpath=.）
  app/
    main.py                   应用装配：create_app() 工厂、/api/v1 路由、静态托管、统一异常处理器、lifespan 建表+seed
    core/
      config.py               pydantic-settings（前缀 AT_）：SQLite 路径、scrypt 参数、会话 TTL、分页默认值
      database.py             SQLAlchemy engine/session；SQLite PRAGMA foreign_keys=ON 事件钩子
      seed.py                 schools 字典 seed（幂等，ADR-008）；返回本次新增计数
      logging.py              日志配置、audit_event、RequestIdMiddleware（request_id 贯穿）
      times.py                iso_from / iso_plus（UTC 时间工具）
    shared/
      security.py             scrypt 密码哈希（每账号随机盐）、会话令牌生成 + sha256 哈希
      auth.py                 AuthContext(family_id, session_id)、Bearer 解析、resolve_auth 守卫、爆破退避计数
      exceptions.py           层级化 AppError + ErrorResponse 序列化（404/401/403/409/422/500）
    api/v1/
      deps.py                 router 公共依赖（双主体 AuthContext 注入、分页参数）
      family.py               注册/登录/登出/会话查询路由（API-M001-001~003）
      student_auth.py         学生登录/登出/主体信息路由（ACR-001 新增；命名空间独立防爆破）
      students.py             学生档案 CRUD 路由（API-M001-004~006，双主体 scope）+ 子账号开通/更新（ACR-001）
      tasks.py                任务路由：创建/列表/详情/更新/状态推进（API-M001-007~011；student 限本人）
      schools.py              学校字典只读列表路由（API-M001-012，公共数据）
    modules/m001/             M001 业务内聚（models/repositories/services/schemas）
      models/orm.py           SQLAlchemy ORM：family_accounts/schools/students/student_accounts/auth_sessions/tasks/task_items
      repositories/
        account_repo.py       family_accounts/student_accounts/auth_sessions 读写（双主体会话、学生子账号唯一性、会话删除/查询）
        student_repo.py       students 读写（强制 family_id；join schools 组装档案）
        school_repo.py        schools 只读查询（全局公共字典，无 family_id）
        task_repo.py          tasks/task_items 读写（强制 family_id；group_no 段统计/段内题目；_UNSET 哨兵语义）
      services/
        family_space.py       FamilySpaceService + StudentService（档案归属、school_id 存在性双保险；list/update 支持 student scope）
        student_account_service.py  StudentAccountService（ACR-001：开通/停用/改密，弱口令提示，审计仅记 student_id）
        task_service.py       TaskService（create/list/detail/update，scope_student_id 双主体）+ TaskQueryService（含 get_task_group(s)/can_accept_photo）
        task_state.py         TaskStateService（状态机 transition/mark_in_progress；transition 支持 student scope）
      schemas/
        common.py             分页参数与通用校验
        family.py             FamilyRegister/Login/Token DTO
        school.py             SchoolDTO（school_id/name/stage）
        student.py            StudentCreate/Update/DTO（school_id 必填校验）
        student_account.py    StudentAccountCreate/Update/DTO/CreateResponse/StudentLogin（ACR-001）
        task.py               TaskCreate/Update/DTO、TaskItemIn/Out（group_no/容器化）、TaskGroupSegmentDTO
frontend/                     移动优先"零构建原生 H5"（FastAPI 静态托管，无 Node 构建链）
  index.html                  单页壳：登录/注册/学生/任务四视图 + 视图切换
  styles.css                  移动优先响应式样式（H5）
  app.js                      原生 JS：API 调用、token 管理、视图渲染、表单校验
backend/tests/                测试（策略与结果见 MODULE_TEST.md）
  conftest.py                 每用例独立 SQLite、双家庭 fixture（familyA/familyB）、scrypt 参数加速
  unit/                       test_school_seed / test_security / test_task_validation（含 CR-001 group_no 结构校验）
  integration/                test_internal_services（Repository family 隔离、任务+题目单事务回滚）
  api/                        test_family_api / test_schools_api / test_students_api / test_tasks_api / test_isolation / test_student_accounts_api / test_task_container_api
backend/data/                 运行时数据目录（SQLite 文件 + 图片目录；.gitignore）
```

## 文件职责与修改风险（已实现）

| 文件 | 职责（实现实况） | Exports（关键符号） | Modification Risk |
| --- | --- | --- | --- |
| `services/task_service.py` | 任务 CRUD 与题目集单事务写、group_no 结构校验、冻结规则（仅 draft/published 可编辑）、include_answers 遮蔽参考答案、双主体 scope_student_id、内部 TaskQueryService（含学科作业段查询） | `TaskService.create/list/detail/update`、`TaskQueryService.get_task/list_tasks/can_accept_submission/get_task_group(s)/can_accept_photo`、`validate_items`、`build_item_out` | 高（契约核心 API-M001-007~010；段/遮蔽规则改动影响 M002~M007） |
| `services/task_state.py` | 任务状态机唯一实现（_TRANSITIONS 表驱动；transition 支持 student scope） | `TaskStateService.transition/mark_in_progress` | 高（非法迁移 409 语义与 M002 首传推进耦合，变更须过 CR） |
| `services/family_space.py` | 学生档案归属 + school_id 存在性双保险 + 学校只读查询服务（list/update 支持 student 本人 scope） | `StudentService`、`FamilySpaceService.get_student` | 中（档案变更影响任务/评定归属链） |
| `services/student_account_service.py` | 学生子账号开通/停用/改密（ACR-001）、scrypt、弱口令提示、审计仅记 student_id | `StudentAccountService.open/update` | 中（家长专属管理面，越权 404/403） |
| `repositories/*_repo.py` | 数据访问；family_id 过滤第一防线（school_repo 例外：公共只读）；task_repo 支持整体 replace_items 与字段级更新 + 段统计；account_repo 双主体会话与学生子账号唯一性 | `StudentRepo`、`TaskRepo.create/replace_items/update_fields/group_stats/list_items_in_group`、`AccountRepo`（含 `get_student_credentials/create_session(双主体)`）、`SchoolRepo` | 高（裸查询 = 数据越权，RISK-004） |
| `shared/security.py` / `auth.py` | scrypt 密码哈希、令牌 sha256 存储、**双主体** AuthContext 注入守卫、爆破退避（family/student 命名空间隔离） | `hash_password/verify_password`、`resolve_auth`、`AuthContext`（subject_type/student_id/is_student）、`consume/check/clear_login_failure` | 高（安全基座，被全模块复用） |
| `shared/exceptions.py` | 统一异常层级 + ErrorResponse（含 request_id） | `AppError` 子类、`to_error_response` | 高（所有模块错误语义依赖） |
| `core/database.py` / `config.py` | engine/session（FK 开启）、集中配置 | `build_engine`、`Settings` | 中（连接/配置变更影响全后端） |
| `core/seed.py` | schools 字典幂等预置 | `seed_schools(session)` | 低（初始化数据；补学校走变更流程，REQ-009） |
| `core/logging.py` | 审计日志与 request_id 中间件 | `audit_event`、`RequestIdMiddleware` | 中（脱敏口径变更影响全模块） |
| `api/v1/*.py` | REST 端点薄层（映射到 Service，不做业务） | 各 router | 低-中（契约冻结，改动须 CR） |
| `models/orm.py` | **7 表**定义/唯一约束/索引（含 `student_accounts`、`auth_sessions.subject_type`、`tasks.subject` 可空、`task_items.group_no`） | ORM 模型类 | 中（结构变更走迁移） |
| `schemas/*.py` | Pydantic v2 请求/响应 DTO（含 `student_account.py`） | Create/Update/DTO | 中（与 API 契约绑定） |
| `frontend/index.html`/`styles.css`/`app.js` | 原生 H5 全功能 UI（登录→档案→任务闭环） | — | 低（REST 契约不变即可整体换壳 Vue3+Vite） |
| `tests/` | **89 项测试**（unit/integration/api；CHANGE-001 后） | conftest fixtures | 低（回归保障；改契约须同步） |

## 维护要求

- 方法级（L7）覆盖核心方法：`TaskService.create/update`、`TaskStateService.transition/mark_in_progress`、`TaskQueryService`、认证注入（见 `MODULE_DESIGN.md`）
- 任何文件增删/改名必须同步本表与 `MODULE_SUMMARY.md`（索引一致性要求）
