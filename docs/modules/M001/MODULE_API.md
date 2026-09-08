# M001 模块 API（权威源）—— 作业任务管理

- **状态**：Frozen（契约基线 v0.1.1，2026-09-08 用户批准；API-M001-001~012 修改须走 CR，见 `API_REGISTRY.md` 状态机）
- **REST 前缀**：`/api/v1`；**认证**：除注册/登录外均需 `Authorization: Bearer <token>`
- **错误体统一**：`ErrorResponse { "code": string, "message": string, "request_id": string }`（HTTP 状态映射见契约 Failure Behavior）
- **请求/响应内容类型**：`application/json`；时间一律 UTC ISO-8601
- API ID 由 Project Master 分配（`API-M001-nnn`），修改须走 CR
- **DTO 约定**：`StudentDTO = { student_id, name, grade_level, relation, school: { school_id, name, stage }, created_at, updated_at }`（school 为档案必填关联的公共字典条目，ADR-008/REQ-009）

## 公共 REST API 清单

| API ID | 名称 | Method/Path | 摘要 |
| --- | --- | --- | --- |
| API-M001-001 | 注册家庭账号 | POST `/family/register` | 创建家庭账号（login_name 唯一） |
| API-M001-002 | 家庭登录 | POST `/family/login` | 校验凭据，返回会话 token |
| API-M001-003 | 家庭登出 | POST `/family/logout` | 注销当前会话 |
| API-M001-004 | 创建学生档案 | POST `/students` | 当前家庭下新增学生档案（必填关联学校） |
| API-M001-005 | 学生档案列表 | GET `/students` | 当前家庭全部学生档案 |
| API-M001-006 | 更新学生档案 | PATCH `/students/{student_id}` | 更新档案字段（含改关联学校） |
| API-M001-007 | 创建作业任务 | POST `/tasks` | 含题目集（逐题学科/题型/可选参考答案） |
| API-M001-008 | 任务列表 | GET `/tasks` | 按状态/学生过滤，分页倒序 |
| API-M001-009 | 任务详情 | GET `/tasks/{task_id}` | 含题目；`include_answers` 控制参考答案可见 |
| API-M001-010 | 更新任务 | PATCH `/tasks/{task_id}` | 仅 draft/published 且未开始上传时可改（防基准漂移） |
| API-M001-011 | 推进任务状态 | POST `/tasks/{task_id}/status` | 合法迁移：publish/close/reopen |
| API-M001-012 | 学校字典列表 | GET `/schools` | 全局共享只读学校列表（建档下拉数据源，ADR-008） |

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
- 约束：`school_id` 必填且必须存在于 `schools`（seed 预置字典）；不存在 → 422
- Response `201 StudentDTO`（含 `school: {school_id, name, stage}`）

### API-M001-005 学生档案列表
- `GET /api/v1/students`（Bearer）
- Response `200 [ StudentDTO... ]`（仅当前家庭；school 为公共字典 join 展示）

### API-M001-006 更新学生档案
- `PATCH /api/v1/students/{student_id}`（Bearer）
- Request：可更新字段同创建（部分字段；`school_id` 可改，校验同上，不存在 → 422）
- Response `200 StudentDTO`
- Errors：`404`（含跨家庭查询——不泄露存在性）；`403` 越权（同 404 语义下返回 403 亦可，二选一，实现用 404）

### API-M001-007 创建作业任务
- `POST /api/v1/tasks`（Bearer）
- Request
```json
{
  "title": "数学口算 20 题",
  "subject": "math",
  "grade_level": "3",
  "content": "课本 P23 练习",
  "student_id": "<uuid>",
  "deadline": "2026-09-08T20:00:00Z",
  "items": [
    { "seq": 1, "item_type": "objective", "subject": "math", "stem": "12 × 8 = ?", "reference_answer": "96" }
  ]
}
```
- 约束：`student_id` 必须属于当前家庭（403/404）；至少 1 题；`items` 唯一 seq；客观题 `reference_answer` 可选（无则不判对错，ADR-006）；主观题 `reference_answer` 拒绝（防误导）
- Response `201 TaskDTO`（状态 draft）
- Errors：`422` 校验；`403/404` 学生档案不属本家庭

### API-M001-008 任务列表
- `GET /api/v1/tasks?status=&student_id=&page=&page_size=`（Bearer）
- Response `200 { "items": [TaskSummaryDTO], "page": n, "page_size": n, "total": n }`（倒序）

### API-M001-009 任务详情
- `GET /api/v1/tasks/{task_id}?include_answers=false`（Bearer）
- Response `200 TaskDTO`（含 `items`）；`include_answers=true` 时客观题返回 `reference_answer`
- Errors：`404` 不存在/不属于本家庭

### API-M001-010 更新任务
- `PATCH /api/v1/tasks/{task_id}`（Bearer）
- Request：可改标题/内容/题目集/截止时间（仅当 `status in {draft, published}` 且尚未有任何上传提交——有提交即冻结题目）
- Errors：`409` 状态不允许修改（任务已开始）

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

## 内部服务接口（进程内 Python Interface，供同进程模块）

> 供 M002/M004/M005/M007 引用；实现由 AGENT-M001 提供，方法签名在契约批准后冻结。所有方法须传 `family_id` 上下文，越权抛 `PermissionDenied`。

| 接口 | 方法 | 说明 | 消费者 |
| --- | --- | --- | --- |
| `FamilySpaceService` | `get_student(family_id, student_id) -> StudentDTO` | 校验档案归属并返回（含 school 信息） | M002 |
| `TaskQueryService` | `get_task(family_id, task_id, include_answers=False) -> TaskDetailDTO` | 任务+题目读取 | M002/M004/M005/M007 |
| `TaskQueryService` | `list_tasks(family_id, *, student_id=None, status=None) -> list[TaskDetailDTO]` | 列表读取 | M007 |
| `TaskQueryService` | `can_accept_submission(family_id, task_id, student_id) -> bool` | 该任务对该学生档案当前可上传？ | M002 |
| `TaskStateService` | `mark_in_progress(family_id, task_id)` | 首次有效上传后由 M002 调用推进 | M002 |

> 注：`reference_answer` 仅在评分域（M005，同一家庭上下文）允许读取；M004 匹配不需要答案。DTO 字段与 REST 一致，避免双套模型（单 Source of Truth 于 `MODULE_DATA.md` 字段定义）。
> 学校名称查询：M007 展示"学生 · 学校"时经 `FamilySpaceService.get_student`（StudentDTO.school）或学校只读查询获取；学校字典为公共数据，无家庭上下文限制。
