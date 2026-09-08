# M001 模块设计 —— 作业任务管理

- **状态**：已实现（Task-001 交付，`54 passed`；实现期决策记录见文末，待 PM DoD 验收）
- **技术上下文**：ADR-004（FastAPI + SQLite 单体）；ADR-005（家庭级数据隔离）；ADR-006（题目三要素建模）；ADR-008（学校字典全局共享只读 + 档案必填关联）

## 分层架构

```text
REST Router (api/v1) ── schemas(Pydantic 校验) ── Service(业务/状态机/家庭上下文) ── Repository(SQLAlchemy) ── SQLite
                                                      │
                                                      └─ shared/auth（AuthContext.family_id 注入）+ 审计日志
```

- Router 只做参数与 DTO 映射；Service 承载业务规则（状态机、冻结、归属校验）；Repository 承担 ORM 查询
- 内部消费者（M002 等）直接调用 Service 接口（`MODULE_API.md` 内部接口），不经 REST，避免无谓 HTTP 开销

## 关键技术决策

| 决策点 | 选择 | 理由 |
| --- | --- | --- |
| ORM | SQLAlchemy 2.0 | 类型化查询 + SQLite→PostgreSQL 迁移路径（ADR-004 预留），不引入额外重量 ORM |
| Schema | Pydantic v2（FastAPI 内置） | 契约请求/响应即 schema，天然契合 | 
| 密码哈希 | 标准库 `hashlib.scrypt`（每账号随机盐） | 免第三方依赖即满足单向哈希；强度参数集中配置 |
| 会话令牌 | `secrets.token_urlsafe(32)`，库存 `sha256(token)` | 不透明令牌、库内不可反解原文；过期 30 天 |
| 前端 | 移动优先响应式 H5，**已落地为"零构建原生 H5 + FastAPI 静态托管"**（决策记录见文末；不影响 API 契约，后续可平滑换 Vue3+Vite 壳） | ADR-004 H5 形态；决策时点本机无 Node 构建链，原生实现即可交付契约全量 UI；换壳成本低（REST 契约不变） |
| ID 生成 | UUID4（TEXT 存储） | 全局唯一、无自增枚举泄露 |
| 事务 | 任务+题目集单事务写 | 部分失败整体回滚 |
| 学校字典 | 全局共享表 + seed 预置；只读查询，无写路径（ADR-008） | 公共基础数据最小实现；维护后台 V1 不做 |

## 目录结构

实现实况与逐文件职责见 `MODULE_FILES.md`。要点：`backend/app/modules/m001/` 内聚 M001 业务；`backend/app/shared/` 放认证注入、异常、审计工具（公共代码治理见 `DEVELOPMENT_GUIDE.md` §13）。

## 学校字典（公共只读，ADR-008/REQ-009）

- `schools` 表全局共享（无 `family_id`）；`StudentCreate/Update.school_id` 校验值必须存在（应用层查询 + DB FK 双保险）
- 数据初始化：`core/seed.py`（幂等）随 DB 首次初始化预置常用学校（V1 起步 `stage=primary`，覆盖常见小学若干所）
- REST 仅只读 `GET /schools`（stage/keyword/分页）；**不存在任何学校写路径**（不提供 create/update/delete 的 Router/Service 方法；后台维护为未来变更预留，不实现）
- `StudentDTO.school` 由 students 查询 join schools 组装；学校名称为公共信息，日志无需脱敏
- 学校变更（补录/改名/停用）V1 不提供运行期手段：seed 变更走部署升级；需求层面变更走 CR（`REQ-009`）

## 核心方法与数据流（L7 方法级）

### 学科作业段（CR-001 容器化）
- `tasks.subject` 收敛：单学科=学科小写值；多学科登记单= NULL 或 `'mixed'`（学科标注只在题级 `(subject, group_no)`）
- `_validate_group_structure(items)`：显式分组（存在 `group_no>0`）时——**禁 0、组号从 1 起连续、组内 subject 一致、同组块连续不交错**；全 0 视为默认单段（收敛，允许跨科目）
- `TaskQueryService.get_task_groups(task)` 返回 `(subject, group_no)` 段清单；`get_task_group(family_id, task_id, subject, group_no, include_answers=False) -> TaskGroupSegmentDTO`（段不存在/越权 → `PermissionDenied`）；`can_accept_photo(...)` 委托 `can_accept_submission`（M002 归属照片的段级可用性）
- 照片最终归属到作业段（M002），完成程度由内容级判定链回写（M002 契约 v0.3.0 R4~R6）

### 双主体 scope（ACR-001）
- Service 方法新增 `scope_student_id: str|None`：**None=family 主体**（本家任意）；**值=student 主体**（强制仅本人）
- `create(list…)`：student 主体的目标 `student_id` 必须等于 scope，否则 `NotFound`（对外 404，防探测他人存在性）
- `detail/update/transition`：student 主体操作他人任务/档案 → `NotFound(404)`；family 任意
- 家长专属（建档/子账号管理/学校维护等）由 REST 层按 `ctx.is_student` 拦截 → `403 PermissionDenied`

### `TaskService.create_task(family_id, dto, scope_student_id=None)`
1. 校验 scope（student 主体只能为本人建任务）+ `student_id` 归属（StudentRepo.get）→ 非本家/非本人抛 `NotFound(404)`（family 越权经归属校验）
2. 校验题目集：非空；`seq` 从 1 连续唯一；**group_no 结构校验**（见上）；客观题 `reference_answer` 可选（**非基准辅助字段 ADR-010**）；主观题必须空；字段长度
3. 同一事务内写入 `tasks`（status=draft）+ `task_items`（批量，group_no 随行）
4. 返回完整 `TaskDetailDTO`；审计日志记录 task 创建（不含参考答案）

### `TaskService.update_task(family_id, task_id, dto, scope_student_id=None)`
1. 读取任务并校验归属与 scope（student 他人 → 404）；`status ∈ {draft, published}` 才允许编辑，否则 `409 Conflict`
2. 题目变更时：整体替换 `task_items`（事务内 delete+insert，seq + group_no 规则同上）
3. in_progress/closed 一律 `409`（基准稳定）

### `StudentService`（档案，含学校关联；双主体）
- create：家长专属（REST 按 `ctx.is_student` 403）；校验 `family_id` 归属 + `school_id` 存在性（422）
- list(`scope_student_id`)：family=本家全部；student=仅本人（get_with_school 单条）
- update(`scope_student_id`)：student 他人 → 404；family 任意；`school_id` 校验同上
- get/list：join `schools` 组装 `StudentDTO.school`；档案删除 V1 不支持（未成年人数据留存）

### `StudentAccountService`（ACR-001：家长管理学生子账号）
- `open(family_id, student_id, payload)`：学生档案必须本家（404）；**student 唯一 + login_name 全局唯一**（`IntegrityError→Conflict 409`）；scrypt 哈希（n/r/p 配置）；`password_warning` 弱口令提示（长度<8 或纯数字/无字母）
- `update(family_id, student_id, payload)`：子账号不存在/不属本家 → 404；status 变更或改密（PATCH 至少一项显式）
- 审计：`student_account_opened/updated` 仅记 `student_id`（login_name 视为弱标识，不入审计）

### `TaskStateService.transition(family_id, task_id, action, scope_student_id=None)`
- scope 校验：student 主体对非本人任务 → 404
- 状态机（合法边之外的任何迁移抛 `409 InvalidTransition`）：

```text
draft      --publish-------------------------------> published
published  --(首传, 由 M002 调用 mark_in_progress)--> in_progress
published  --close--------------------------------> closed
in_progress--close--------------------------------> closed
closed     --reopen-------------------------------> published
```

- `mark_in_progress` 仅供内部服务调用（M002 首传成功后）；重复调用幂等
- 状态变更写审计日志（who/family/task/from/to/when）

### 认证与双主体上下文（shared）
- family 登录（`/family/login`）与 student 登录（`/student/login`）各发独立 token；`auth_sessions` 存 `token_hash` + `subject_type` +（student 型）`student_id`
- `AuthContext(family_id, session_id, subject_type, student_id, is_student)` 注入请求；`resolve_auth` 解析 subject 并按会话校验
- 登录爆破退避按命名空间隔离：key = `family:{login_name}` / `student:{login_name}`（共享同一 `consume/check/clear_login_failure`）
- 所有 M001 Repository 方法签名强制携带 `family_id`（student 会话再带 `student_id` 过滤）；缺失视为程序缺陷（防裸查询；school_repo 公共只读例外）
- 登出/过期：删除会话或 `expires_at` 校验

## 异常与错误体

统一 `ErrorResponse{code,message,request_id}`；异常类层级（shared）：`ValidationError(400/422)`、`Unauthorized(401)`、`PermissionDenied(403/404)`、`NotFound(404)`、`Conflict(409)`、`InternalError(500)`；`request_id` 贯穿日志（correlation）。

## 日志与审计

- What：任务/档案变更、登录/登出、状态迁移、失败鉴权
- What Not：明文密码、token、学生姓名与参考答案等未成年人/作业敏感内容（`DEVELOPMENT_GUIDE.md` §7）
- 审计：变更人（family_id/session）、动作、时间戳、request_id

## 配置（随实现登记 `CONFIGURATION.md`）

`task.status_flow`、`auth.session_ttl=30d`、`security.scrypt.{n,r,p}`、`subject.recommended=[chinese,math,english]`、`school.stage.recommended=[primary,junior,senior]`、`pagination.{default,max}`（与契约 Configuration 表一致）

## 安全

- scrypt 哈希、会话哈希存储；登录爆破渐进退避（`family:`/`student:` 命名空间隔离，ACR-001）
- **双主体授权矩阵**（ACR-001 口径）：

| 操作 | family 主体（家长） | student 主体（本人） | student 主体（他人） |
| --- | --- | --- | --- |
| 建档案 / 子账号开通·停用·改密 | ✅（子账号仅本家档案） | ❌ 403 | ❌ 403 |
| 档案列表/更新 | ✅ 本家全部 | ✅ 本人 | 404（防探测） |
| 任务创建 | ✅ 本家任意档案 | ✅ 本人档案 | 404 |
| 任务详情/更新/状态推进 | ✅ 本家全部 | ✅ 本人任务 | 404 |
| `include_answers`（辅助参考答案） | ✅ 本家任务 | ✅ 本人任务 | 404 |
| 跨家庭任何访问 | 404/403 | 404 | 404 |

- 家庭上下文强制注入（`family_id` 底线 + student 时 `student_id`）；资源不存在/他人一律对外 404 防枚举，家长专属操作 403
- 未成年人数据：DB 文件权限受控（本地目录），日志脱敏，不做公网默认暴露（ASM-010 局域网）
- `schools` 公共只读：仅 seed 写；运行期写路径一律不存在（防御：ORM 层不提供写方法）

## 性能

- 单家庭低并发；索引齐备（`MODULE_DATA.md`）；任务+题目写为单事务、批量 insert
- 不做缓存（V1 数据量小）；登录哈希为唯一较重操作

## 测试指引

见 `MODULE_TEST.md`（含"为何需要/为何不需要"说明）。

## 实现期决策记录（Task-001 追加，与基线契约一致）

| # | 决策点 | 落地方式 | 说明 |
| --- | --- | --- | --- |
| 1 | 前端形态 | **零构建原生 H5**（`frontend/index.html`+`styles.css`+`app.js`），由 FastAPI 静态托管 | 决策时点本机无 Node/npm 构建链；REST 契约不受影响，后续可平滑换 Vue3+Vite 壳（前端决策同步更新） |
| 2 | 提交模型 | Repository 不自行 commit；**请求级统一 commit/rollback**（lifespan 之外由异常处理器兜底） | 任务+题目集天然单事务（`test_internal_services` 断言中途失败整单回滚） |
| 3 | PATCH 字段语义 | `_UNSET` 哨兵区分"字段未提供"与"显式清空（None）" | 支持把 content/deadline 清为 null；`model_fields_set` 只处理出现在请求体中的字段 |
| 4 | SQLite FK | engine event 钩子开启 `PRAGMA foreign_keys=ON` | schools→students DB 层外键约束真生效（应用层 school_repo 查询双保险） |
| 5 | 时间规约 | 未标注时区视为 UTC；契约时间一律 ISO8601 UTC | `_deadline_iso` 归一化 + schema 层校验 |
| 6 | 学校写路径防御 | ORM/Repository 仅提供只读查询方法；路由层无 POST/PATCH/DELETE | ADR-008 公共只读的代码级强制 |
| 7 | 种子与生效解耦 | `seed_schools` 幂等并返回新增数；测试用独立空库验证 | 主 app lifespan 建表+seed；seed 单测不依赖预置库 |
| 8 | 状态机实现 | `_TRANSITIONS: dict[action, dict[from→to]]` 表驱动 + `mark_in_progress` 幂等 | 非法 action/非法边统一 `InvalidTransitionError`→409；in_progress 重复 mark 幂等 |
| 9 | 测试隔离 | conftest 每用例独立 SQLite(tmp)+双家庭 fixture；scrypt 降参加速登录用例 | 无用例间污染，越权矩阵可独立断言 |
| 10 | 静态托管 | FastAPI `StaticFiles` 挂载 frontend（HTML+CSS+JS），`GET /` 直出 index.html | 单机/局域网单进程部署（ASM-010），前端零构建即可用 |
| 11 | 任务容器化（CR-001） | `tasks.subject` 可空/'mixed'，学科粒度下放到 `task_items(subject, group_no)`；`group_no=0`=默认单段收敛 | 旧单学科数据零迁移兼容；多学科登记单=一个任务多段，M002 照片归属到段 |
| 12 | 两级主体（ACR-001） | `student_accounts` 独立于 `family_accounts`；会话 `subject_type` 分派；family/student 登录名分命名空间（可同名） | 学生自主登记/拍照（仅本人），家长兜底；防爆破计数隔离避免互扰 |
| 13 | 越权口径 | student 主体访问他人资源一律对外 404；家长专属操作（建档/子账号管理）403 | 防探测他人存在性（与既有 404 语义一致）；`AuthContext.is_student` 在 REST 层短路 |
| 14 | 子账号口令提示 | `password_warning` 随开通/改密响应返回（弱口令放行但提示），不强制复杂度 | 儿童可用性优先（家庭内部产品），家长看到提示自行加强 |
| 15 | 参考答案非基准（ACR-002/ADR-010） | `reference_answer` 仅作辅助展示与人工参考；判定链端到端直判不依赖其存在 | M001 不为 M005 提供"答案比对基准"承诺，避免误导判分实现 |

> 决策 1 是 Task-001 中唯一相对规划的自适应调整；决策 11~15 为 CHANGE-001 执行期落地方式（CR-001/CR-002/ACR-001/ACR-002 批准条款）；其余决策均为对既定设计（MODULE_DESIGN 正文 + 契约 v0.1.1）的实现确认。规划版"前端 Vue3+Vite"建议不再作为实现基线。

