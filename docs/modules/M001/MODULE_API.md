# M001 模块 API（权威源）—— 作业任务管理

- **状态**：**v0.1.2（定稿）**（2026-09-08 CHANGE-001 PM 复核 APPROVED；API-M001-001~012 冻结面随变更后实况修订 + ACR-001 新增端点登记 API-M001-013~017）
- **REST 前缀**：`/api/v1`；**认证**：除注册/登录外均需 `Authorization: Bearer <token>`
- **两级主体（ACR-001/ADR-009）**：`family`（家长，Bearer 来自 `/family/login`）= 本家任意学生可操作 + 兜底；`student`（学生子账号，Bearer 来自 `/student/login`）= **仅本人数据**（URL 传参他人 → 404 防探测；管理类家长专属操作 → 403）。两类 token 均可被既有资源端点识别，`family_id` 为过滤底线
- **错误体统一**：`ErrorResponse { "code": string, "message": string, "request_id": string }`（HTTP 状态映射见契约 Failure Behavior）
- **请求/响应内容类型**：`application/json`；时间一律 UTC ISO-8601
- API ID 由 Project Master 分配（`API-M001-nnn`），修改须走 CR
- **DTO 约定**：`StudentDTO = { student_id, name, grade_level, relation, school: { school_id, name, stage }, created_at, updated_at }`（school 为档案必填关联的公共字典条目，ADR-008/REQ-009）；`TaskDetailDTO.subject`/`TaskSummaryDTO.subject` **可空**（CR-001 容器化：多学科登记单为 NULL/'mixed'，学科粒度见题目 `subject`+`group_no`）

## 公共 REST API 清单

| API ID | 名称 | Method/Path | 摘要 |
| --- | --- | --- | --- |
| API-M001-001 | 注册家庭账号 | POST `/family/register` | 创建家庭账号（login_name 唯一，家长命名空间） |
| API-M001-002 | 家庭登录 | POST `/family/login` | 校验凭据，返回 family 主体会话 token |
| API-M001-003 | 家庭登出 | POST `/family/logout` | 注销当前会话 |
| API-M001-004 | 创建学生档案 | POST `/students` | **家长专属**：本家新增学生档案（必填关联学校） |
| API-M001-005 | 学生档案列表 | GET `/students` | family=本家全部；student=仅本人档案 |
| API-M001-006 | 更新学生档案 | PATCH `/students/{student_id}` | family=本家任意；student=仅本人（他人 → 404） |
| API-M001-007 | 创建作业任务 | POST `/tasks` | 含题目集（逐题学科/段号 group_no/题型/非基准辅助参考答案）；student 主体可建本人任务 |
| API-M001-008 | 任务列表 | GET `/tasks` | 按状态/学生过滤，分页倒序；student 主体仅本人（查他人 → 404） |
| API-M001-009 | 任务详情 | GET `/tasks/{task_id}` | 含题目；`include_answers` 控制辅助参考答案可见 |
| API-M001-010 | 更新任务 | PATCH `/tasks/{task_id}` | 仅 draft/published 且未开始上传时可改（防基准漂移） |
| API-M001-011 | 推进任务状态 | POST `/tasks/{task_id}/status` | 合法迁移：publish/close/reopen |
| API-M001-012 | 学校字典列表 | GET `/schools` | 全局共享只读学校列表（建档下拉数据源，ADR-008） |
| API-M001-013 | 开通学生子账号 | POST `/students/{student_id}/account` | **family 仅**：为学生档案开通子账号（login_name 学生命名空间唯一；弱口令返回 password_warning） |
| API-M001-014 | 更新学生子账号 | PATCH `/students/{student_id}/account` | **family 仅**：停用/启用（status）或改密（password），至少一项 |
| API-M001-015 | 学生登录 | POST `/student/login` | 校验子账号凭据 → student 主体会话 token（subject_type=student）；命名空间独立防爆破 |
| API-M001-016 | 学生登出 | POST `/student/logout` | student/family 均可注销当前会话（204 幂等） |
| API-M001-017 | 学生主体信息 | GET `/student/me` | **student 仅**：当前学生档案（StudentDTO）；family 主体 → 403 |

> API-M001-013~017（ACR-001 新增）由 Project Master 于 2026-09-08 CHANGE-001 收口分配编号并登记 `API_REGISTRY.md`（状态 Active）；详细契约见文末"ACR-001 新增端点"小节。

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

### API-M001-007 创建作业任务
- `POST /api/v1/tasks`（Bearer）
- Request（单学科登记单）
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
- **多学科登记单（CR-001 容器化）**：`subject` 省略（NULL）或传 `'mixed'`；每道 `items[].subject` 必填，`items[].group_no` 为学科作业段号——全部缺省=0 单段（旧兼容，允许跨科目）；显式分组时从 1 起连续、段内科目一致、同段连续不交错、禁止与 0 混用
- 约束：`student_id` 必须属于当前家庭；student 主体只能为**本人**创建（他人/不存在 → 404 防探测）；至少 1 题；`items` 唯一连续 seq；`reference_answer` 为**非判定基准辅助字段**（ADR-010/ACR-002：判定链端到端直判，不以其比对）——仅客观题可选录入，主观题一律拒绝（防误导）
- Response `201 TaskDetailDTO`（状态 draft；subject 可空/'mixed'，items 含 group_no）
- Errors：`422` 校验/分组结构违规；`404` 学生档案不属本家庭或非本人（防探测）

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
| `TaskQueryService` | `get_task(family_id, task_id, include_answers=False) -> TaskDetailDTO` | 任务+题目读取 | M002/M004/M005/M007 |
| `TaskQueryService` | `list_tasks(family_id, *, student_id=None, status=None) -> list[TaskDetailDTO]` | 列表读取 | M007 |
| `TaskQueryService` | `can_accept_submission(family_id, task_id, student_id) -> bool` | 该任务对该学生档案当前可上传？ | M002 |
| `TaskQueryService` | `get_task_groups(family_id, task_id) -> list[(subject, group_no)]` | 任务内学科作业段清单（CR-001/M002 归属段校验） | M002/M004 |
| `TaskQueryService` | `get_task_group(family_id, task_id, subject, group_no, *, include_answers=False) -> TaskGroupSegmentDTO` | 某学科作业段题目（段不存在/越权 → PermissionDenied） | M002/M004 |
| `TaskQueryService` | `can_accept_photo(family_id, task_id, student_id) -> bool` | 任务当前可接受归属照片（CR-001 归属语义，与 can_accept_submission 等价） | M002 |
| `TaskStateService` | `mark_in_progress(family_id, task_id)` | 首次有效上传后由 M002 调用推进 | M002 |

> 内部接口越权语义统一 `PermissionDenied`（REST 层转对外 404/403 防探测口径）；student 主体调内部接口同样由上层带 `scope_student_id` 限定本人。

> 注：`reference_answer` 仅在评分域（M005，同一家庭上下文）允许读取；M004 匹配不需要答案。DTO 字段与 REST 一致，避免双套模型（单 Source of Truth 于 `MODULE_DATA.md` 字段定义）。
> 学校名称查询：M007 展示"学生 · 学校"时经 `FamilySpaceService.get_student`（StudentDTO.school）或学校只读查询获取；学校字典为公共数据，无家庭上下文限制。
