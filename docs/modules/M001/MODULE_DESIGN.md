# M001 模块设计 —— 作业任务管理

- **状态**：实现中（契约基线 v0.1.1 已批准；由 AGENT-M001 在 Task-001 编码中细化并保持同步）
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
| 前端 | 移动优先响应式 H5，建议 Vue3 + Vite 构建后由 FastAPI 托管 `frontend/dist`（编码开始时最终确定，不影响 API 契约） | ADR-004 H5 形态；构建产物静态托管最简单 |
| ID 生成 | UUID4（TEXT 存储） | 全局唯一、无自增枚举泄露 |
| 事务 | 任务+题目集单事务写 | 部分失败整体回滚 |
| 学校字典 | 全局共享表 + seed 预置；只读查询，无写路径（ADR-008） | 公共基础数据最小实现；维护后台 V1 不做 |

## 目录结构（规划目标，编码时校准）

见 `MODULE_FILES.md`。要点：`backend/app/modules/m001/` 内聚 M001 业务；`backend/app/shared/` 放认证注入、异常、审计工具（公共代码治理见 `DEVELOPMENT_GUIDE.md` §13）。

## 学校字典（公共只读，ADR-008/REQ-009）

- `schools` 表全局共享（无 `family_id`）；`StudentCreate/Update.school_id` 校验值必须存在（应用层查询 + DB FK 双保险）
- 数据初始化：`core/seed.py`（幂等）随 DB 首次初始化预置常用学校（V1 起步 `stage=primary`，覆盖常见小学若干所）
- REST 仅只读 `GET /schools`（stage/keyword/分页）；**不存在任何学校写路径**（不提供 create/update/delete 的 Router/Service 方法；后台维护为未来变更预留，不实现）
- `StudentDTO.school` 由 students 查询 join schools 组装；学校名称为公共信息，日志无需脱敏
- 学校变更（补录/改名/停用）V1 不提供运行期手段：seed 变更走部署升级；需求层面变更走 CR（`REQ-009`）

## 核心方法与数据流（L7 方法级）

### `TaskService.create_task(family_id, dto)`
1. 校验 `student_id` 归属（StudentRepo.get）→ 非本家庭抛 `PermissionDenied(403/404)`
2. 校验题目集：非空；`seq` 从 1 连续唯一；客观题 `reference_answer` 可选；主观题 `reference_answer` 必须空；字段长度
3. 同一事务内写入 `tasks`（status=draft）+ `task_items`（批量）
4. 返回完整 `TaskDetailDTO`；审计日志记录 task 创建（不含参考答案）

### `TaskService.update_task(family_id, task_id, dto)`
1. 读取任务并校验归属；`status ∈ {draft, published}` 才允许编辑，否则 `409 Conflict`
2. 题目变更时：整体替换 `task_items`（事务内 delete+insert，seq 规则同上）
3. in_progress/closed 一律 `409`（评分基准稳定）

### `StudentService`（档案，含学校关联）
- create/update：校验 `family_id` 归属（403/404）+ `school_id` 存在性（422，school_repo 只读查询）
- get/list：join `schools` 组装 `StudentDTO.school`；学生档案删除 V1 不支持（未成年人数据留存）

### `TaskStateService.transition(family_id, task_id, action)`
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

### 认证与家庭上下文（shared）
- 登录成功：签发 token → `auth_sessions` 存 `token_hash`；`AuthContext(family_id, session_id)` 注入请求
- 所有 M001 Repository 方法签名强制携带 `family_id`；缺失视为程序缺陷（防裸查询；school_repo 公共只读例外）
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

- scrypt 哈希、会话哈希存储；登录爆破渐进退避
- 家庭上下文强制注入；越权统一 403（资源不存在场景按资源归属对外返回 404，防枚举）
- 未成年人数据：DB 文件权限受控（本地目录），日志脱敏，不做公网默认暴露（ASM-010 局域网）
- `schools` 公共只读：仅 seed 写；运行期写路径一律不存在（防御：ORM 层不提供写方法）

## 性能

- 单家庭低并发；索引齐备（`MODULE_DATA.md`）；任务+题目写为单事务、批量 insert
- 不做缓存（V1 数据量小）；登录哈希为唯一较重操作

## 测试指引

见 `MODULE_TEST.md`（含"为何需要/为何不需要"说明）。
