# M001 模块契约（黑盒）—— 作业任务管理

- **Module ID**：M001 ｜ **版本**：v0.1.1（契约基线，Frozen） ｜ **日期**：2026-09-08
- **状态**：Frozen —— 契约基线已由用户批准（签署区，2026-09-08）；任何修改走 CR/ACR（`ID_GOVERNANCE.md`）
- **适用**：黑盒约定。内部实现（类/库/表结构细节）见 `MODULE_DESIGN.md` 与 `MODULE_DATA.md`
- **v0.1.1 变更摘要**：用户 M001 开发输入增补"学校基础资料"（REQ-009/ADR-008/DATA-011）：新增全局共享只读 `schools` 字典（seed 预置，无运行期维护 API）；`students.school` 自由文本 → `school_id` 必填（FK→schools）；新增 API-M001-012（`GET /schools`）；学生档案必填关联学校（名称+学段）

## Purpose

V1 入口基座：提供纯家庭模式下的家庭空间（家庭账号认证、学生档案，档案必填关联全局学校字典）与作业任务生命周期管理，题目逐题建模（学科/题型/客观题参考答案），支撑 M002~M007 的闭环输入与评分对照基准。

## Responsibilities / Non-Responsibilities

见 `MODULE.md`（M001 的 Purpose/Responsibilities/Non-Responsibilities 即为本契约黑盒职责，不再复制）。

## Inputs / Outputs

| 类型 | 说明 |
| --- | --- |
| Inputs | 注册/登录凭据；学生档案信息（含必填 `school_id`，选自预置学校字典）；任务与题目集（含可选参考答案）；状态推进指令 |
| Outputs | 会话 token；档案/任务/题目数据；学校字典只读列表（建档下拉）；状态迁移结果与校验错误 |

## Exposed APIs

- REST：`API-M001-001~012`（前缀 `/api/v1`；完整契约 `MODULE_API.md`；登记 `API_REGISTRY.md`）
- 内部服务接口（进程内，供 M002/M004/M005/M007）：`FamilySpaceService`、`TaskQueryService`、`TaskStateService`

## Events

- V1 为单体同步架构，**不引入异步事件总线**；任务状态变化以 API 响应与操作日志记录，消费模块（M002 等）经查询接口获取状态（诚实声明：无 outbox/消息队列）
- 任务创建/发布/关闭等状态迁移写入审计日志（audit），供追溯

## Data Ownership

- DATA-001（`tasks`/`task_items`）、DATA-002（`family_accounts`/`students`/`auth_sessions`）Owner = M001；唯一写入口，其他模块只读消费
- DATA-011（`schools`，全局共享只读）由 M001 承载：仅初始化 seed 写入，运行期无写路径；任何模块/用户均不得运行期增删改（ADR-008）
- 详见 `MODULE_DATA.md` / `DATA_MODEL.md`

## Configuration

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `task.status_flow` | `draft→published→in_progress→closed` | 任务状态机（非法迁移拒绝） |
| `subject.recommended` | `chinese/math/english` | V1 建议学科值（ASM-011）；字段存文本，不写死可扩展 |
| `item_type.enum` | `objective/subjective` | 题型枚举（ADR-006 判定依据） |
| `school.stage.recommended` | `primary/junior/senior` | 学校学段建议值（ADR-008）；V1 seed 起步 `primary` |
| `pagination.default` | `page_size=20, max=100` | 列表分页 |
| `auth.session_ttl` | 30 天 | 会话有效期（家庭自用场景） |
| `security.password_hash` | scrypt（标准库） | 密码单向哈希，禁止明文/可逆存储 |

## Security

- 认证：注册/登录获取**不透明会话 token**（存储仅存 token 哈希，不存原文）
- 授权：所有业务请求经 Bearer token 解析出 `family_id` 注入上下文；**家庭数据的一切 M001 查询强制按 `family_id` 过滤**，跨家庭访问统一 403。**例外**：`schools` 为全局共享公共只读字典，登录即可查询，不做家庭过滤（ADR-008）
- 密码：scrypt + 每账号随机盐；禁止明文落库/落日志
- 敏感数据：未成年人学生档案与作业作答内容（参考答案）不写普通日志；日志脱敏（`DEVELOPMENT_GUIDE.md` §7）；学校名称为公共信息无需脱敏
- 登录防爆破：失败计数 + 渐进退避（轻量，V1 本地场景）
- CORS/输入校验：FastAPI + Pydantic 严格校验；请求体大小限制

## Performance

- V1 单家庭低并发（单机 SQLite，ADR-004）；登录哈希为最重操作（~50-100ms），可接受
- 索引：`tasks(family_id, status, created_at)`、`task_items(task_id)`、`students(family_id)`、`students(school_id)`、`schools(name, stage)`（UNIQUE）、`auth_sessions(token_hash)`
- 列表默认倒序（新在前），分页上限 100

## Failure Behavior

| 场景 | 行为 |
| --- | --- |
| 参数/模型校验失败 | 400/422，错误体 `ErrorResponse{code,message,request_id}`（含 `school_id` 缺失/不存在） |
| 未登录/会话过期 | 401 |
| 跨家庭访问/无权 | 403 |
| 资源不存在 | 404 |
| 非法状态迁移/冲突 | 409（附当前状态） |
| 存储故障 | 500 + 完整请求日志（含 request_id），客户端可见统一错误体 |
| 一致性 | 单任务写操作在单事务内完成（任务+题目同事务），失败整体回滚 |

## Version / Compatibility

- v0.1.1 Draft（2026-09-08）：在 v0.1.0 上增补"学校基础资料"（REQ-009/ADR-008/DATA-011）；冻结后基线进入 `MODULE_CHANGELOG.md`；任何后续修改走 CR/ACR（`ID_GOVERNANCE.md`）
- V1 新模块，无历史兼容负担；与 REQ-001/REQ-009、DATA-001/DATA-002/DATA-011 严格一致

## 签署区（批准记录）

| 角色 | 结论 | 日期 | 签名 |
| --- | --- | --- | --- |
| 用户（决策者） | **批准** | 2026-09-08 | 用户 |
| Project Master | **批准** | 2026-09-08 | PM（总控） |

> 契约基线 **v0.1.1 Frozen**（2026-09-08 用户批准）。M001 状态转 Developing，Task-001 已签发（`AGENT_REGISTRY.md`）；API-M001-001~012 修改须走 CR。
