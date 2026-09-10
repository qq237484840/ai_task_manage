# M001 模块设计 —— 作业任务管理

- **状态**：**v0.2.0（Frozen，用户批准 2026-09-10）** —— 代码基线为 v0.1.2（89 passed），本设计描述 **CR-003 修订后目标态**；实施（`CHANGE-003` ③）= **`Task-007`**（已签发，契约已定稿）
- **技术上下文**：ADR-004（FastAPI + SQLite 单体）；ADR-005（家庭级数据隔离）；ADR-009（两级主体）；**ADR-013（双层模型：按天事实层 + 跨天聚合层）**；ADR-008（学校字典全局共享只读）；`app/core/ai/`（LLM 接入层，执行方 `AGENT-AI`）

## 分层架构

```text
REST Router (api/v1) ── schemas(Pydantic 校验) ── Service(业务/状态机/归属引擎/聚合) ── Repository(SQLAlchemy) ── SQLite
                                                      │
                                                      ├─ 归属引擎 WindowResolver（策略接口，读 AT_* 配置）
                                                      ├─ app/core/ai/（链路 T 解析；Provider 抽象 + schema 校验 + 降级）
                                                      └─ shared/auth（AuthContext.family_id 注入）+ 审计日志
```

- Router 只做参数与 DTO 映射；Service 承载业务规则（归属引擎、状态机、聚合生成、冻结、归属校验）；Repository 承担 ORM 查询
- 内部消费者（M002 等）直接调用 Service 接口（`MODULE_API.md` 内部接口），不经 REST

## 关键技术决策

| 决策点 | 选择 | 理由 |
| --- | --- | --- |
| ORM | SQLAlchemy 2.0 | 类型化查询 + SQLite→PostgreSQL 迁移路径（ADR-004 预留） |
| Schema | Pydantic v2（FastAPI 内置） | 契约请求/响应即 schema |
| 密码哈希 | 标准库 `hashlib.scrypt`（每账号随机盐） | 免第三方依赖；强度参数集中配置 |
| 会话令牌 | `secrets.token_urlsafe(32)`，库存 `sha256(token)` | 不透明令牌、库内不可反解 |
| 前端 | Vue3 + Vite + TS + Vant 4（ADR-012），`frontend/dist` 由 FastAPI 托管 | ADR-004 H5 形态 + ADR-012 |
| ID 生成 | UUID4（TEXT 存储） | 全局唯一、无自增枚举泄露 |
| **归属引擎** | **策略接口 `WindowResolver`**（`resolve(ts) → {belong_date, week_index, window_type, group_key}`）；V1 实现 = `DefaultWindowResolver` | 规则（4 点边界/周末/假期）未来可能调整，抽接口便于替换与测试（A5） |
| **事实层唯一键** | `UNIQUE(student_id, category, belong_date)` | 按天唯一（ADR-013）；`category` 预留多任务类型 |
| **聚合落库 + 版本锁定** | `task_groups`（`policy_version`）+ `task_group_subjects` | "配置变更只管后续"天然成立、无需历史迁移（ADR-013 方案 C） |
| **保守降级** | AI 解析失败 → 保留 `placeholder` + 手工录入路径 | 解析错误不污染事实层；手工兜底必须保留 |

## 目录结构

实现实况与逐文件职责见 `MODULE_FILES.md`。要点：`backend/app/modules/m001/` 内聚 M001 业务；`backend/app/core/ai/` 为横切 LLM 接入层；`backend/app/shared/` 放认证注入、异常、审计工具。

## 归属引擎 `WindowResolver`（A5）

```python
class WindowResolver(Protocol):
    def resolve(self, ts: datetime) -> WindowInfo: ...   # WindowInfo = {belong_date, week_index, window_type, group_key}

class DefaultWindowResolver:                              # V1 实现；读 4 个 AT_* 配置
    # belong_date = (ts.astimezone(AT_TIMEZONE) - AT_DAY_CUTOFF).date()
    # week_index  = 周次(AT_TERM_START 所在周的周一 → 第 N 周)
    # window_type = day | weekend(周五 04:00~周一 04:00) | holiday(AT_TERM_END 之后，按自然周)
    # group_key   = day→belong_date；weekend→W:<该周末周五 belong_date>；holiday→H:<周起始>.<Wn>
```

- 时间戳按 **UTC** 存储，仅在 `resolve` 内转换（诚实口径）；
- 配置读取集中（`core/config.py`）；**配置生效与锁定规则**见 `MODULE_CONTRACT.md` §F4（`CONFIGURATION.md` §一）；
- 边界用例（A10）：9/9 20:00 与 9/10 03:00 同归 9/9；9/10 05:00 归 9/10；周五~周日 → 同一 `group_key`；`AT_TERM_START` 非周一时第 1 周为半周。

## 聚合生成与 `policy_version` 锁定（A6/A7）

- **`ensure_group(student, category, belong_date, window_type, group_key)`**（幂等，写路径调用）：
  1. 计算归属窗口（`WindowResolver`）
  2. `get_or_create task_groups`：命中 `UNIQUE(student_id, category, group_key)` 则复用；**新建时写入 `policy_version` = 当前生效配置版本**；命中时**不改 `policy_version`**（追加数据语义）
  3. 合并 `task_group_subjects`：按 `subject` 汇总聚合内各天 `task_contents` → upsert（`content_refs` 追加）
- **纯浏览不锁**：`GET` 列表/详情只读，**不触发** `policy_version` 写入（首次写入由任务解析完成 / 作业照片上传触发）
- **聚合维度**：每个 `belong_date` 至少一个聚合；`window_type=day` 聚合成员 = 1 天；`weekend` 聚合成员 = 3 天（周五/周六/周日）；`holiday` 聚合成员 = 自然周

## 链路 T：任务解析流程（A4）

### `TaskService.ingest(family_id, dto, scope_student_id=None)`
1. scope 校验（student 主体只能为本人）+ `student_id` 归属校验 → 非本家/非本人 `NotFound(404)`
2. `WindowResolver.resolve(now)` → 归属窗口；按 `UNIQUE(student_id, category, belong_date)` **取或建** `tasks`（`spec_status=placeholder`，`title` 自动生成）
3. 写入 `task_spec_sources`（多段：`seq`/`kind`/`text_content`/`photo_id`）
4. 调用 `app/core/ai/` 解析（`AiClient.parse_task_spec`）→ 草稿（学科 + 内容项）；成功 → 写 `task_contents` + `spec_status=parsed`；失败/超时 → 保持 `placeholder` + 返回降级提示（不阻断）
5. `ensure_group(...)` 幂等生成聚合
6. 单事务提交；返回 `TaskDetailDTO`

### `TaskService.confirm_parse(family_id, task_id, dto, scope_student_id=None)`
- 家长确认：`spec_status → confirmed`（可同时校正内容项：增/删/改）
- **隐式确认**（C7）：由 M002 判定链在「确认作业完成情况」时调用（入参携带"将一并落库的解析摘要"）；**调用方必须先展示摘要**（契约约束，非本模块可强制，写入 `MODULE_CONTRACT.md` §F1）
- 幂等：重复确认 → `200` 同结果

### `TaskService.change_belong_date(family_id, task_id, new_date, operator)`（A8/B8）
- 单事务执行 §F5 六条连锁：重算快照 → 迁移聚合 FK（目标无则 `ensure_group`）→ 源聚合空则删 → **`conclusion_status=confirmed` 拒绝**（409）→ 审计 → **回调 M002 迁移 `photo_subject_links` 挂接目标**
- 跨模块迁移经 `TaskAggregationService`（M001）+ M002 提供的内部接口（事务内编排）

## 双主体 scope（ACR-001，不变）

- Service 方法携带 `scope_student_id: str|None`：**None=family 主体**（本家任意）；**值=student 主体**（强制仅本人）
- student 主体操作他人资源 → `NotFound(404)`（防探测）；家长专属（建档/子账号管理）由 REST 层按 `ctx.is_student` 拦截 → 403

## 认证与双主体上下文（shared，不变）

- family 登录（`/family/login`）与 student 登录（`/student/login`）各发独立 token；`auth_sessions` 存 `token_hash` + `subject_type` +（student 型）`student_id`
- 登录爆破退避按命名空间隔离：key = `family:{login_name}` / `student:{login_name}`
- 所有 M001 Repository 方法签名强制携带 `family_id`（student 会话再带 `student_id` 过滤）；缺失视为程序缺陷（school_repo 公共只读例外）

## 学校字典（公共只读，ADR-008，不变）

- `schools` 全局共享（无 `family_id`）；`school_id` 校验存在性（应用 + DB FK 双保险）；seed 幂等；无写路径

## 异常与错误体

统一 `ErrorResponse{code,message,request_id}`；异常类层级（shared）：`ValidationError(400/422)`、`Unauthorized(401)`、`PermissionDenied(403/404)`、`NotFound(404)`、`Conflict(409)`、`InternalError(500)`；`request_id` 贯穿日志。

## 日志与审计

- What：任务创建/解析确认/聚合生成/改归属日/状态迁移、档案变更、登录登出、失败鉴权
- What Not：明文密码、token、学生姓名、任务内容项文本与输入源文本（`DEVELOPMENT_GUIDE.md` §7）
- 审计：变更人（family_id/session）、动作、时间戳、request_id

## 配置（随实现登记 `CONFIGURATION.md`）

`AT_TIMEZONE`/`AT_TERM_START`/`AT_TERM_END`/`AT_DAY_CUTOFF`、`task.status_flow`、`spec_status.flow`、`auth.session_ttl=30d`、`security.scrypt.{n,r,p}`、`subject.recommended`、`category.enum`、`school.stage.recommended`、`pagination.{default,max}`。

## 安全

- scrypt 哈希、会话哈希存储；登录爆破渐进退避（`family:`/`student:` 命名空间隔离）
- **双主体授权矩阵**（ACR-001 口径，不变）：

| 操作 | family 主体（家长） | student 主体（本人） | student 主体（他人） |
| --- | --- | --- | --- |
| 建档案 / 子账号开通·停用·改密 | ✅（子账号仅本家档案） | ❌ 403 | ❌ 403 |
| 档案列表/更新 | ✅ 本家全部 | ✅ 本人 | 404（防探测） |
| 任务创建（输入源上传）/ 解析确认 | ✅ 本家任意档案 | ✅ 本人档案 | 404 |
| 任务详情/合并查询/改归属日 | ✅ 本家全部 | ✅ 本人任务 | 404 |
| 跨家庭任何访问 | 404/403 | 404 | 404 |

- 未成年人数据：DB 文件权限受控（本地目录），日志脱敏，不做公网默认暴露（ASM-010）
- 输入源图片：M001 不承载图片本体，仅存 M002 受控存储引用

## 性能

- 单家庭低并发；索引齐备（`MODULE_DATA.md`）；任务 + 输入源 + 内容项 + 聚合生成单事务、批量 upsert
- 不做缓存（V1 数据量小）；`ensure_group` 幂等，避免重复聚合写

## 测试指引

见 `MODULE_TEST.md`（含新增用例设计：归属边界 4 点、周次起算、周末聚合、唯一键冲突、配置锁定按学生隔离）。

## 实现期决策记录

| # | 决策点 | 落地方式 | 说明 |
| --- | --- | --- | --- |
| 1 | 前端形态 | 现为 **Vue3+Vite+TS+Vant 4 工程**（ADR-012/Task-003） | 替代决策 1 原零构建实现 |
| 2 | 提交模型 | Repository 不自行 commit；**请求级统一 commit/rollback** | 任务+输入源+内容项+聚合天然单事务 |
| 3 | PATCH 字段语义 | `_UNSET` 哨兵区分"未提供"与"显式清空" | 支持显式清空 |
| 4 | SQLite FK | engine event 钩子开启 `PRAGMA foreign_keys=ON` | schools→students 外键真生效 |
| 5 | 时间规约 | 未标注时区视为 UTC；契约时间一律 ISO8601 UTC | 归属计算处按 `AT_TIMEZONE` 转换 |
| 6 | 学校写路径防御 | ORM/Repository 仅只读查询方法；路由层无 POST/PATCH/DELETE | ADR-008 代码级强制 |
| 7 | 种子与生效解耦 | `seed_schools` 幂等并返回新增数 | 测试用独立空库验证 |
| 8 | 状态机实现 | `_TRANSITIONS` 表驱动 + `mark_in_progress` 幂等 | 非法边统一 409 |
| 9 | 测试隔离 | conftest 每用例独立 SQLite(tmp) + 双家庭 fixture | 越权矩阵可独立断言 |
| 10 | 静态托管 | FastAPI `StaticFiles` 挂载 `frontend/dist` | 单进程部署（ASM-010） |
| 11 | ~~任务容器化（CR-001）~~ | **作废**（ADR-013：多学科登记单容器 + `group_no` 学科作业段语义取消） | 学科标签移至 `task_contents.subject` / 聚合层 |
| 12 | 两级主体（ACR-001） | `student_accounts` 独立；会话 `subject_type` 分派；命名空间隔离 | 不变 |
| 13 | 越权口径 | student 访问他人一律 404；家长专属 403 | 不变 |
| 14 | 子账号口令提示 | `password_warning` 随响应返回（不强制复杂度） | 不变 |
| 15 | ~~参考答案非基准（ACR-002/ADR-010）~~ | **随 `task_items` 废弃**（ADR-013 继承"端到端直判/不维护参考答案基准"原则） | 逐题字段退役 |
| 16 | 前端工程化（ADR-012） | Vue3+Vite+TS+Vant 4；REST 契约为唯一契约面 | 不变 |
| 17 | **归属引擎可替换**（A5） | `WindowResolver` 策略接口 + V1 `DefaultWindowResolver` | 便于规则演进与边界用例测试 |
| 18 | **聚合落库固化**（ADR-013 方案 C） | `task_groups.policy_version` 生成时写入、追加不改 | "配置变更只管后续"天然成立、无历史迁移 |
| 19 | **判定单元跨模块回写** | M002 计算结论、**经 `TaskAggregationService.commit_conclusion` 回写** | 保证 DATA-013 单一写入口（M001） |
| 20 | **改归属日跨模块迁移** | 单事务编排 + 回调 M002 迁移 `photo_subject_links` | 避免悬挂挂接引用（A8/R6） |
