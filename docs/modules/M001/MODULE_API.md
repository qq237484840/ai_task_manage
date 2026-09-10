# M001 模块 API（权威源）—— 作业任务管理

- **状态**：**v0.2.0（Frozen，用户批准 2026-09-10）** —— 按 `CR-003`/`ADR-013` 修订（任务创建改输入源解析、新增聚合查询端点）。API-M001-001~006/012 保持既有契约；**任务相关端点（007~011）与新增端点为本次修订面**；新增端点 API ID **已由 PM 分配 = `API-M001-018~021`**（`API_REGISTRY.md`，Draft，随 `Task-007` 实施转 Active）；前版 v0.1.2 定稿（2026-09-08）
- **REST 前缀**：`/api/v1`；**认证**：除注册/登录外均需 `Authorization: Bearer <token>`
- **两级主体（ACR-001/ADR-009）**：`family`（家长，Bearer 来自 `/family/login`）= 本家任意学生可操作 + 兜底；`student`（学生子账号，Bearer 来自 `/student/login`）= **仅本人数据**（URL 传参他人 → 404 防探测；管理类家长专属操作 → 403）。两类 token 均可被既有资源端点识别，`family_id` 为过滤底线
- **错误体统一**：`ErrorResponse { "code": string, "message": string, "request_id": string }`（HTTP 状态映射见契约 Failure Behavior）
- **请求/响应内容类型**：`application/json`；时间一律 UTC ISO-8601
- **API ID**：既有 `API-M001-001~017` 由 Project Master 分配；**本变更新增端点 API ID = `API-M001-018~021`**（已由 PM 分配登记 `API_REGISTRY.md`，Draft；原「申请清单」见文末）
- **DTO 约定**：`StudentDTO = { student_id, name, grade_level, relation, school: { school_id, name, stage }, created_at, updated_at }`（school 为档案必填关联的公共字典条目，ADR-008/REQ-009）
  - `TaskDTO`（事实层）= `{ task_id, student_id, category, belong_date, week_index, window_type, spec_status, title, grade_level, status, deadline, contents: [ContentItemDTO], sources: [SourceDTO], created_at, updated_at }`
  - `ContentItemDTO = { content_id, subject, seq, text }`｜`SourceDTO = { source_id, seq, kind(text|image), text_content|null, photo_id|null }`
  - `TaskGroupDTO`（聚合层）= `{ group_id, student_id, category, group_key, display_name, window_type, policy_version, subjects: [TaskGroupSubjectDTO], created_at }`
  - `TaskGroupSubjectDTO = { group_subject_id, subject, content_refs, conclusion|null, conclusion_status(pending|draft|confirmed) }`
  - ~~`TaskDetailDTO.subject`（`'mixed'` 容器标注）/`items`（逐题）~~ **作废**（ADR-013）

## 公共 REST API 清单

| API ID | 名称 | Method/Path | 摘要 |
| --- | --- | --- | --- |
| API-M001-001 | 注册家庭账号 | POST `/family/register` | 创建家庭账号（login_name 唯一，家长命名空间） |
| API-M001-002 | 家庭登录 | POST `/family/login` | 校验凭据，返回 family 主体会话 token |
| API-M001-003 | 家庭登出 | POST `/family/logout` | 注销当前会话 |
| API-M001-004 | 创建学生档案 | POST `/students` | **家长专属**：本家新增学生档案（必填关联学校） |
| API-M001-005 | 学生档案列表 | GET `/students` | family=本家全部；student=仅本人档案 |
| API-M001-006 | 更新学生档案 | PATCH `/students/{student_id}` | family=本家任意；student=仅本人（他人 → 404） |
| API-M001-007 | **上传任务输入源（链路 T）** | POST `/tasks` | **修订**：提交输入源（图片 / 粘贴文本，多段，**无需填内容**）→ 归属窗口 + AI 解析草稿；返回 `TaskDTO`（`spec_status=placeholder\|parsed`） |
| API-M001-008 | 任务列表 | GET `/tasks` | **修订**：按 `belong_date`/`week_index`/`status`/学生过滤，分页倒序；student 主体仅本人（查他人 → 404） |
| API-M001-009 | 任务详情 | GET `/tasks/{task_id}` | **修订**：含内容项 + 输入源；**不再返回逐题 `items`** |
| API-M001-010 | 更新任务 | PATCH `/tasks/{task_id}` | **修订**：改 `title`/`grade_level`/`deadline` + 内容项增删改 |
| API-M001-011 | 推进任务状态 | POST `/tasks/{task_id}/status` | 合法迁移：publish/close/reopen（不变） |
| API-M001-012 | 学校字典列表 | GET `/schools` | 全局共享只读学校列表（建档下拉数据源，ADR-008） |
| API-M001-013 | 开通学生子账号 | POST `/students/{student_id}/account` | **family 仅**：为学生档案开通子账号（login_name 学生命名空间唯一；弱口令返回 password_warning） |
| API-M001-014 | 更新学生子账号 | PATCH `/students/{student_id}/account` | **family 仅**：停用/启用（status）或改密（password），至少一项 |
| API-M001-015 | 学生登录 | POST `/student/login` | 校验子账号凭据 → student 主体会话 token（subject_type=student）；命名空间独立防爆破 |
| API-M001-016 | 学生登出 | POST `/student/logout` | student/family 均可注销当前会话（204 幂等） |
| API-M001-017 | 学生主体信息 | GET `/student/me` | **student 仅**：当前学生档案（StudentDTO）；family 主体 → 403 |

> API-M001-013~017（ACR-001 新增）由 Project Master 于 2026-09-08 CHANGE-001 收口分配编号并登记 `API_REGISTRY.md`（状态 Active）；详细契约见文末"ACR-001 新增端点"小节。

## CR-003 新增端点（**API-M001-018~021**，2026-09-10 PM 分配登记）

| API ID | 名称 | Method/Path | 摘要 | 消费者 |
| --- | --- | --- | --- | --- |
| API-M001-018 | 解析结果确认（含**隐式确认**） | POST `/tasks/{task_id}/parse-confirmation` | 家长确认解析草稿 → `spec_status=confirmed`；M002 判定链可携带「本次将一并落库的解析摘要」调用（隐式确认 C7） | H5（任务页 / M002 确认页） |
| API-M001-019 | 聚合任务列表 | GET `/task-groups` | 按 `week_index`/`student_id`/`window_type` 查询聚合（「作业」列表：周次分组 + 周末聚合展示） | H5（M002 作业列表） |
| API-M001-020 | 聚合任务详情 | GET `/task-groups/{group_id}` | 聚合任务 + 聚合学科子任务（**★判定单元**）详情 | H5 / M002 |
| API-M001-021 | 手工改归属日 | POST `/tasks/{task_id}/belong-date` | 按契约 §F5 六条连锁规则改归属日（含跨聚合 `photo_subject_links` 迁移回调） | H5（家长维护） |

> 上列 4 端点 = `CHANGE-003` §2.1 A9 申请清单；**ID 由 Project Master 于 2026-09-10 分配**并登记 `API_REGISTRY.md`（状态 Draft，随实施转 Active）。

## 详细契约

### API-M001-001 注册家庭账号
- `POST /api/v1/family/register`
- Request `{ "login_name": str(3..64), "password": str(8..128), "display_name": str(1..32) }`
- Response `201 { "family_id": uuid, "display_name": str }`
- Errors：`409` login_name 已存在；`422` 校验失败（密码强度等）

### API-M001-002 家庭登录
- `POST /api/v1/family/login`
- Request `{ "login_name": str, "password": str }`
- Response `200 { "token": str, "expires_at": ISO8601 }`（token 原文仅此一次返回，库中只存哈希）
- Errors：`401` 凭据错误；`403` 账号被临时锁定（爆破退避）

### API-M001-003 家庭登出
- `POST /api/v1/family/logout`（Bearer）
- Response `204`（删除当前会话；幂等）

### API-M001-004 创建学生档案
- `POST /api/v1/students`（Bearer）
- Request `{ "name": str(1..32), "grade_level": str|null, "school_id": uuid, "relation": str|null }`
- 主体：**family 仅**（student 主体 → 403）
- 约束：`school_id` 必填且必须存在于 `schools`（seed 预置字典）；不存在 → 422
- Response `201 StudentDTO`（含 `school: {school_id, name, stage}`）

### API-M001-005 学生档案列表
- `GET /api/v1/students`（Bearer）
- 主体：family=本家全部；student=仅本人档案（会话绑定档案单条）
- Response `200 [ StudentDTO... ]`（school 为公共字典 join 展示）

### API-M001-006 更新学生档案
- `PATCH /api/v1/students/{student_id}`（Bearer）
- Request：可更新字段同创建（部分字段；`school_id` 可改，校验同上，不存在 → 422）
- 主体：family=本家任意；student=仅本人（URL 传他人 → 404 防探测）
- Response `200 StudentDTO`
- Errors：`404`（含跨家庭/他人查询——不泄露存在性）；`422` school_id 不存在

### API-M001-007 上传任务输入源（链路 T）（修订）
- `POST /api/v1/tasks`（Bearer）
- Request：
```json
{
  "student_id": "<uuid>",
  "category": "school",
  "grade_level": "3",
  "sources": [
    { "seq": 1, "kind": "image", "photo_id": "<uuid>" },
    { "seq": 2, "kind": "text", "text_content": "数学：口算 20 题；语文：抄写第 3 课生字" }
  ]
}
```
- 语义：**上传无需填写任何内容**；`belong_date`/`week_index`/`window_type` 由 `WindowResolver` 按**上传时刻**自动解析；同日同类型已有任务 → **幂等归集**（追加 `sources` / 追加 `task_contents`），不新建；否则新建 `tasks`（`spec_status=placeholder`，`title` 自动生成如「09-09 周三」，家长可改）
- 解析：服务端调用 `app/core/ai/` 得「今日任务」草稿（学科 + 内容项）→ 落 `task_contents` 并置 `spec_status=parsed`；**解析失败/超时 → 保持 `placeholder`** 并返回降级提示（非阻断，家长可手工录入）
- 约束：`student_id` 属当前家庭；student 主体只能为**本人**（他人/不存在 → 404 防探测）；`sources` 至少 1 段、`seq` 连续；`kind=image` 时 `photo_id` 必须为**本家已上传照片**（M002，存在性校验经内部接口）
- Response `201 TaskDTO`（含 `contents`/`sources`；`spec_status=placeholder|parsed`）
- Errors：`422` 校验失败；`404` 学生档案/照片不属本家庭或非本人；`409` 归属日冲突（并发写入，客户端重试即幂等）
- 幂等：`Idempotency-Key` 头可选；同 key 重复提交返回首次结果

### API-M001-007b 补充输入源（同日内追加）
- 同 `POST /api/v1/tasks`（携带已存在任务的同一 `student_id` + 同一归属日）→ 追加 `sources`/`contents`，不新建任务（A3：同学科追加内容项、新学科新增标签）
- 响应与错误同 API-M001-007；**不改变**已有聚合的 `policy_version`

### API-M001-008 任务列表
- `GET /api/v1/tasks?status=&student_id=&page=&page_size=`（Bearer）
- Response `200 { "items": [TaskSummaryDTO], "page": n, "page_size": n, "total": n }`（倒序）

### API-M001-009 任务详情（修订）
- `GET /api/v1/tasks/{task_id}`（Bearer）
- Response `200 TaskDTO`（含 `contents` 内容项 + `sources` 输入源 + `spec_status`）；**不再返回逐题 `items`/`reference_answer`**（`task_items` 废弃）
- Errors：`404` 不存在/不属于本家庭

### API-M001-010 更新任务（修订）
- `PATCH /api/v1/tasks/{task_id}`（Bearer）
- Request：改 `title`/`grade_level`/`deadline`、内容项增删改（家长维护草稿）
- 约束：`belong_date`/`week_index`/`window_type` **不可经本端点修改**（须走「手工改归属日」端点，触发 §F5 连锁）；聚合被完成分析消费后归属字段禁改（409）
- Errors：`409` 状态/锁不允许修改；`422` 校验失败

### API-M001-011 推进任务状态
- `POST /api/v1/tasks/{task_id}/status`
- Request `{ "action": "publish" | "close" | "reopen" }`
- 合法迁移：`draft→publish→published`；`published|in_progress→close→closed`；`closed→reopen→published`
- Response `200 { "task_id": uuid, "status": str }`；非法迁移 `409`

### API-M001-012 学校字典列表
- `GET /api/v1/schools?stage=&keyword=&page=&page_size=`（Bearer）
- 说明：全局共享只读字典（seed 预置，ADR-008/REQ-009）；供创建/更新学生档案时下拉选择。**不做家庭过滤**（公共数据）；运行期无任何学校写 API
- Query：`stage` ∈ `primary|junior|senior`（可空，默认不过滤）；`keyword` 名称模糊匹配（可空）；分页同默认规则
- Response `200 { "items": [ { "school_id": uuid, "name": str, "stage": str } ], "page": n, "page_size": n, "total": n }`
- Errors：`401` 未登录；`422` 参数非法

## CR-003 新增端点详细契约（API-M001-018~021）

> 4 端点 = `CHANGE-003` §2.1 A9；契约要素（请求/响应/错误/鉴权/幂等/事务/副作用/兼容性）齐备；ID 已由 PM 于 2026-09-10 分配。

### API-M001-018 解析结果确认（含隐式确认）
- `POST /api/v1/tasks/{task_id}/parse-confirmation`（Bearer）
- Request `{ "confirmed": true, "contents": [ { "content_id": uuid, "subject": str, "text": str } ] | null, "implicit": bool=false, "digest": { "subjects": [str], "content_texts": [str] } | null }`
- 语义：家长确认解析草稿 → `spec_status=confirmed`；`contents` 提供则**整体替换**内容项（校正草稿）；`implicit=true` 时由 **M002 判定链**调用（携带 `digest` = 本次将一并落库的解析摘要），用于「确认作业完成情况」时一并确认任务解析（C7）
- **约束**：`implicit=true` 时调用方**必须已展示 `digest`**（契约层约束；M001 记录调用来源 = `app/core/ai/`/M002）
- 幂等：重复确认 `200` 同结果
- Errors：`404` 任务不属本家/不存在；`409` 任务已 `confirmed` 且 `contents` 冲突；`422` 校验失败

### API-M001-019 聚合任务列表
- `GET /api/v1/task-groups?student_id=&week_index=&window_type=&page=&page_size=`（Bearer）
- 用途：「作业」列表（周次分组 + 周末聚合展示）；family=本家全部，student=仅本人
- Response `200 { "items": [TaskGroupDTO], "page": n, "page_size": n, "total": n }`
- Errors：`404` 学生档案不属本家/非本人；`422` 参数非法

### API-M001-020 聚合任务详情
- `GET /api/v1/task-groups/{group_id}`（Bearer）
- Response `200 TaskGroupDTO`（含 `subjects: [TaskGroupSubjectDTO]` 判定单元 + `policy_version`）
- Errors：`404` 聚合不属本家/不存在

### API-M001-021 手工改归属日
- `POST /api/v1/tasks/{task_id}/belong-date`（Bearer）
- Request `{ "belong_date": "YYYY-MM-DD" }`
- 语义：按契约 §F5 六条连锁规则执行（单事务）：重算快照 → 迁移聚合 FK（目标无则建）→ 源聚合空则删 → **`conclusion_status=confirmed` 拒绝（409）** → 审计 → **跨聚合迁移同步 `photo_subject_links` 挂接目标**（M002 内部接口回调）
- Response `200 TaskDTO`（含新 `belong_date`/`week_index`/`window_type`）
- 副作用：可能创建/删除聚合、触发 M002 挂接迁移；审计留痕
- Errors：`409`（已被完成分析消费 / 非法目标日）；`404` 任务不属本家；`422` 校验失败

## ACR-001 新增端点详细契约（API-M001-013~017）

> 新增端点由 ACR-001（Approved）随 CHANGE-001 落地（2026-09-08 PM 收口分配 API ID）；状态 Active（CHANGE 批准引入），待用户批准冻结面扩展（如有，走 CHANGE 复核）。

### API-M001-013 开通学生子账号
- `POST /api/v1/students/{student_id}/account`（Bearer；**family 仅**，student 主体 → 403）
- Request `{ "login_name": str(3..64), "password": str(6..128) }`（学生弱口令放行，响应带提示）
- Response `201 { "student_id": uuid, "login_name": str, "status": "active", "created_at": ISO, "updated_at": ISO, "password_warning": str|null }`
- Errors：`404` 学生档案不存在/不属本家庭（防探测）；`409` 该学生已有子账号或登录名被占用；`422` 校验失败

### API-M001-014 更新学生子账号（停用/启用/改密）
- `PATCH /api/v1/students/{student_id}/account`（Bearer；**family 仅**）
- Request `{ "status": "active"|"disabled"|null, "password": str(6..128)|null }`（至少一项显式；PATCH 语义）
- Response `200` 同开通响应（status/password_warning 反映变更后实况）
- Errors：`404` 学生档案或子账号不存在/不属本家庭；`422` 校验失败

### API-M001-015 学生登录
- `POST /api/v1/student/login`（公开）
- Request `{ "login_name": str, "password": str }`
- Response `200 { "token": str, "expires_at": ISO, "subject_type": "student", "student_id": uuid, "student_name": str }`
- 命名空间：与家庭登录名可同名不互扰；登录防爆破按 `student` 命名空间独立
- Errors：`401` 凭据错误/账号已停用；`403` 账号被临时锁定（爆破退避）

### API-M001-016 学生登出
- `POST /api/v1/student/logout`（Bearer；student/family 均可注销当前会话）
- Response `204`（幂等）

### API-M001-017 学生主体信息
- `GET /api/v1/student/me`（Bearer；**student 仅**）
- Response `200 StudentDTO`（当前学生档案，含 school）
- Errors：`403` family 主体或未绑定学生档案

## 内部服务接口（进程内 Python Interface，供同进程模块）

> 供 M002/M004/M005/M007 引用；实现由 AGENT-M001 提供，方法签名在契约批准后冻结。所有方法须传 `family_id` 上下文，越权抛 `PermissionDenied`。

| 接口 | 方法 | 说明 | 消费者 |
| --- | --- | --- | --- |
| `FamilySpaceService` | `get_student(family_id, student_id) -> StudentDTO` | 校验档案归属并返回（含 school 信息） | M002 |
| `TaskQueryService` | `get_task(family_id, task_id) -> TaskDTO` | 任务（事实层）+ 内容项 + 输入源读取 | M002 |
| `TaskQueryService` | `list_tasks(family_id, *, student_id=None, belong_date=None, status=None) -> list[TaskDTO]` | 事实层列表 | M002 |
| `TaskQueryService` | `resolve_window(ts) -> WindowInfo` | 归属窗口解析（预览；**纯计算，不锁配置**） | M002、H5 |
| `TaskQueryService` | `list_groups(family_id, *, student_id=None, week_index=None, window_type=None) -> list[TaskGroupDTO]` | 聚合列表 | M002 |
| `TaskQueryService` | `get_group(family_id, group_id) -> TaskGroupDTO` | 聚合任务 + 判定单元读取 | M002 |
| `TaskQueryService` | `ensure_group(family_id, student_id, category, belong_date) -> TaskGroupDTO` | 幂等取/建聚合（写路径；**不覆盖已存在聚合的 `policy_version`**） | M002 |
| `TaskAggregationService` | `commit_conclusion(family_id, group_subject_id, conclusion, evidence, confidence, status) -> TaskGroupSubjectDTO` | M002 回写判定结论（**DATA-013 唯一写入口**） | M002 |
| `TaskAggregationService` | `migrate_links_hook(family_id, task_id, old_group_key, new_group_key)` | 改归属日时通知 M002 迁移 `photo_subject_links`（M001 在事务中回调） | M001 → M002 |
| `TaskStateService` | `mark_in_progress(family_id, task_id)` | 首次有效写入后由 M002 调用推进（幂等） | M002 |

> ~~`get_task_groups` / `get_task_group` / `can_accept_photo` / `can_accept_submission`（段级 `(subject, group_no)` 语义）~~ **作废**（ADR-013：学科作业段取消）

## API ID 申请清单（**已由 PM 分配**，2026-09-10；登记 `API_REGISTRY.md`）

> 依据 `CHANGE-003` §2.1 A9；**禁止模块 Agent 自行编号**（`ID_GOVERNANCE.md`）。同时列明**既有端点修订**（不新增 ID，走 CR 修订）。

| 申请序号 | 名称 | Method/Path | 用途 | 分配 ID |
| --- | --- | --- | --- | --- |
| M001-A1 | 解析结果确认（含隐式确认） | POST `/api/v1/tasks/{task_id}/parse-confirmation` | 家长/C7 隐式确认解析草稿 → `spec_status=confirmed` | **API-M001-018** |
| M001-A2 | 聚合任务列表 | GET `/api/v1/task-groups` | 「作业」列表（周次分组 + 周末聚合） | **API-M001-019** |
| M001-A3 | 聚合任务详情 | GET `/api/v1/task-groups/{group_id}` | 聚合 + 判定单元详情 | **API-M001-020** |
| M001-A4 | 手工改归属日 | POST `/api/v1/tasks/{task_id}/belong-date` | §F5 连锁规则改归属日 | **API-M001-021** |

**既有端点修订（不新增 ID）**：`API-M001-007`（POST `/tasks` → 上传输入源 + AI 解析）、`API-M001-008`（列表按 `belong_date`/`week_index`）、`API-M001-009`（详情返回内容项/输入源，去掉 `items`）、`API-M001-010`（更新面收窄，归属字段改走 M001-A4）。`API-M001-001~006`、`API-M001-011~017` 语义不变。

> 内部接口越权语义统一 `PermissionDenied`（REST 层转对外 404/403 防探测口径）；student 主体调内部接口同样由上层带 `scope_student_id` 限定本人。

> 注：原 `reference_answer` 辅助字段随 `task_items` 废弃（ADR-013 继承「端到端直判、不维护参考答案基准」原则）；DTO 字段与 REST 一致，避免双套模型（单一 Source of Truth 于 `MODULE_DATA.md` 字段定义）。

> 学校名称查询：M007 展示"学生 · 学校"时经 `FamilySpaceService.get_student`（StudentDTO.school）或学校只读查询获取；学校字典为公共数据，无家庭上下文限制。
