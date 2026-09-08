# M001 文件级知识（L6）—— 作业任务管理

- **状态**：规划（契约基线 v0.1.1 已批准，Task-001 编码中）。下方为**目标文件规划**；编码落盘后按 `AGENT_GUIDE.md` §4 逐文件回填 File/Purpose/Dependencies/Exports/Modification Risk，形成真正 L6 清单。

## 工程根结构（FastAPI 单体，ADR-004）

```text
backend/                 FastAPI 后端（API + H5 静态托管 + 图片目录服务）
  app/
    main.py             应用装配（路由挂载 /api/v1、静态目录、异常处理器）
    core/
      config.py         pydantic-settings 配置（SQLite 路径、密钥、会话 TTL 等）
      database.py       SQLAlchemy engine/session
      seed.py           基础数据初始化：schools 字典 seed（幂等，ADR-008）
      logging.py        日志与 request_id 贯穿
    shared/
      security.py       密码 scrypt 哈希、token 生成/哈希
      auth.py           AuthContext 依赖注入、Bearer 解析（family_id 注入）
      exceptions.py     统一异常类 + ErrorResponse
    api/v1/
      family.py         注册/登录/登出路由（API-M001-001~003）
      students.py       学生档案路由（API-M001-004~006）
      tasks.py          任务路由（API-M001-007~011）
      schools.py        学校字典只读列表路由（API-M001-012，公共数据）
      deps.py           router 公共依赖
    modules/m001/
      models/orm.py     SQLAlchemy ORM（family_accounts/schools/students/auth_sessions/tasks/task_items）
      repositories/
        account_repo.py family_accounts/auth_sessions 读写
        student_repo.py students 读写（强制 family_id）
        school_repo.py   schools 只读查询（全局公共字典，无 family_id）
        task_repo.py    tasks/task_items 读写（强制 family_id，事务）
      services/
        family_space.py FamilySpaceService（get_student，返回含 school）
        task_service.py TaskService（create/update/list/get）
        task_state.py   TaskStateService（状态机/transition/mark_in_progress）
      schemas/
        common.py       分页/错误体
        family.py       FamilyRegister/Login/Token DTO
        school.py       SchoolDTO（school_id/name/stage）
        student.py      StudentCreate/Update/DTO（含 school_id 必填校验）
        task.py         TaskCreate/Update/DTO、TaskItemDTO
frontend/                移动优先 H5（建议 Vue3+Vite；托管 dist）
  src/views/…           m001 页面：注册/登录、学生档案（学校下拉 GET /schools）、任务列表/编辑（编码期定义）
tests/                   后端测试（策略见 MODULE_TEST.md）
  unit/  integration/  api/  security/
```

## 文件职责与修改风险（编码后逐项回填）

| 文件 | 职责（规划） | Modification Risk（回填） |
| --- | --- | --- |
| `services/task_service.py` | 任务 CRUD 与题目集事务、编辑状态校验 | 高（契约核心；冻结规则改动影响 M002 依赖） |
| `services/task_state.py` | 任务状态机唯一实现 | 高（非法迁移后果外溢到消费模块） |
| `repositories/*_repo.py` | 数据访问；family 过滤第一防线（school_repo 例外：公共只读） | 高（裸查询=数据越权） |
| `shared/security.py` / `auth.py` | 哈希与认证注入 | 高（安全基座，被全模块复用） |
| `core/seed.py` | schools 字典预置（幂等） | 低（初始化数据；补充学校走变更流程） |
| `api/v1/tasks.py` | REST 端点薄层 | 中（只做映射，业务下沉 Service） |
| `api/v1/schools.py` | 学校只读列表端点（无写路径） | 低（公共只读；变更影响建档下拉） |
| `models/orm.py` | 表定义/索引 | 中（结构变更走迁移） |

## 维护要求

- 方法级（L7）仅覆盖核心方法：`TaskService.create/update_task`、`TaskStateService.transition`、认证注入（见 `MODULE_DESIGN.md`）
- 任何文件增删/改名必须同步本表与 `MODULE_SUMMARY.md`（索引一致性要求）
