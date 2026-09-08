# M002 模块 API（权威源）—— 作业图片采集与归属

- **状态**：Frozen —— 契约基线 v0.3.0 已由用户批准（2026-09-08），修改须走 CR
- **REST 前缀**：`/api/v1`；**认证**：全部接口需 `Authorization: Bearer <token>`
- **主体**（ADR-009/ACR-001）：`family`（家长，可代传任一本家学生，带 `student_id`）；`student`（仅本人，`student_id` 忽略/强制本人）
- **错误体统一**：`ErrorResponse { "code", "message", "request_id" }`（HTTP 映射见契约 Failure Behavior）
- **上传内容类型**：`multipart/form-data`；其余 `application/json`；时间一律 UTC ISO-8601
- **DTO 约定**：`QualityCheckItem = {id, passed, value, threshold, severity(reject|warn)}`；`QualityReport = {ruleset_version, passed, checks[]}`；`Suggestion = {task_id, subject, group_no, confidence, model, prompt_version, suggested_at}`（由 M003 写，M002 展示）

## 公共 REST API 清单

| API ID | 名称 | Method/Path | 摘要 |
| --- | --- | --- | --- |
| API-M002-001 | 创建上传批次 | POST `/upload-batches` | 学生/家长（代传带 student_id）开启一次上传会话 |
| API-M002-002 | 上传作业照片 | POST `/photos` | multipart 单张：校验→质检→归一→入库 `unassigned` |
| API-M002-003 | 照片列表/待处理队列 | GET `/photos` | 按学生/状态/批次/任务过滤（含 suggestion 摘要） |
| API-M002-004 | 受控取图 | GET `/photos/{photo_id}/content` | 原图/归一图内容流（鉴权 + 访问审计 + Range） |
| API-M002-005 | 照片归属操作 | POST `/photos/{photo_id}/associate` | assign/confirm_suggestion/reject；首张 assigned 触发任务 in_progress |
| API-M002-006 | 撤销/清理照片 | DELETE `/photos/{photo_id}` | 删除未消费照片（物理删 + 审计）；已消费 409 |

## 详细契约

### API-M002-001 创建上传批次
- `POST /api/v1/upload-batches`（Bearer）
- Request：`{ "student_id": "uuid?" }` —— family 主体必填本家学生；student 主体忽略（=本人）
- Response `201`：`{ "batch_id": "uuid", "family_id": "uuid", "student_id": "uuid", "created_by_type": "family|student", "created_by_id": "uuid", "created_at": "..." }`
- Errors：`401`；`403/404` student 越权/不存在（对外 404）；`500`

### API-M002-002 上传作业照片
- `POST /api/v1/photos`（Bearer）
- Request：`multipart/form-data`
  - `file`（必填）：图片文件（`image/jpeg|png|webp`，≤10MB）
  - `batch_id`（必填，uuid）：归属的上传批次
- 处理流程（单事务）：
  1. 校验批次归属（本家庭 + 学生主体仅本人）与批次计数 < `upload.max_photos_per_batch`（超限 422 `batch_photo_limit`）
  2. 基础校验（类型 415 / 大小 413 / 像素上限 422）→ 本地规则质检（v1.0）
  3. 未通过 → **不入库**：`422 image_quality_rejected`（message 逐项原因），无任何残留
  4. 通过 → 轻量归一 → 原始图+归一图写受控存储 → 插入 `photos` 行（`seq_no` = 批次当前最大 + 1，**服务端自增**；status=`unassigned`）
- Response `201`：
```json
{
  "photo_id": "uuid",
  "batch": { "batch_id": "uuid", "student_id": "uuid" },
  "seq_no": 1,
  "status": "unassigned",
  "quality": { "ruleset_version": "v1.0", "passed": true, "checks": [] },
  "content_urls": { "original": "/api/v1/photos/<photo_id>/content?kind=original", "normalized": "/api/v1/photos/<photo_id>/content?kind=normalized" }
}
```
- Errors：`401`；`404` 批次不存在/越权（对外 404）；`409 concurrent_conflict`（并发争用）；`413 image_too_large`；`415 unsupported_media_type`；`422` 校验失败 / `image_quality_rejected` / `batch_photo_limit`；`500`
- Idempotency：不幂等（每次上传产生新照片；前端去抖）；重试产生重复页，可走 DELETE 清理

### API-M002-003 照片列表/待处理队列
- `GET /api/v1/photos?student_id=&status=&batch_id=&task_id=&page=&page_size=`（Bearer）
- Query：family 主体可按本家学生过滤；student 主体强制本人。`status ∈ unassigned|suggested|assigned|rejected`（可组合，缺省全部）；`task_id` 过滤 assigned/suggested 的目标任务
- Response `200`：
```json
{
  "items": [
    {
      "photo_id": "uuid", "student_id": "uuid", "batch_id": "uuid", "seq_no": 1,
      "status": "suggested", "created_at": "...",
      "assignment": { "task_id": "uuid", "subject": "math", "group_no": 1, "assigned_at": "..." },
      "suggestion": { "task_id": "uuid", "subject": "math", "group_no": 1, "confidence": 0.87, "model": "...", "prompt_version": "...", "suggested_at": "..." },
      "quality": { "ruleset_version": "v1.0", "passed": true, "checks": [] },
      "content_urls": { "original": "...", "normalized": "..." }
    }
  ],
  "page": 1, "page_size": 20, "total": 1
}
```
- Errors：`401`；`404` 越权（对外 404）；`422` 参数非法

### API-M002-004 受控取图
- `GET /api/v1/photos/{photo_id}/content?kind=original|normalized`（Bearer；kind 缺省 = `normalized`）
- 行为：校验照片归属当前主体（family 本家 / student 本人）→ 写访问审计（photo_id/kind/subject/request_id/ts）→ 流式返回（`normalized` 恒 JPEG；`original` 按原始 mime），支持 `Range`
- Response `200 image/*`；Errors：`401`；`404` 不存在/越权/文件缺失（同 404）；`422` kind 非法

### API-M002-005 照片归属操作
- `POST /api/v1/photos/{photo_id}/associate`（Bearer；执行者：家长或学生本人）
- Request：`{ "action": "assign|confirm_suggestion|reject", "task_id": "uuid?", "subject": "string?", "group_no": 1? }`
  - `assign`：必填三元组 → 归属到指定学科作业段
  - `confirm_suggestion`：采纳 `suggestion_json` 目标（无建议或已消费 → 422/409）
  - `reject`：标记无效（不参与识别/报告）
- 处理（assign/confirm_suggestion，单事务）：
  1. 校验照片未被消费（`consumed_at IS NULL`，否则 409 `photo_consumed`）
  2. 校验目标：M001 `get_task_group(task_id, subject, group_no)` 存在、任务绑定同一学生、`can_accept_photo`（任务 `published|in_progress`）、任务已 assigned 计数 < `association.max_photos_per_task`（409 `task_photo_limit`）
  3. 写归属三元组与 `assigned_at` → status=`assigned`
  4. 该任务 assigned 计数由 0→1 → 同事务调 `mark_in_progress`（幂等）
- Response `200`：`{ "photo_id": "uuid", "status": "assigned|rejected", "assignment": {…}, "task": { "task_id": "uuid", "status": "in_progress" } }`
- Errors：`401`；`404`；`409` `task_not_acceptable` / `task_photo_limit` / `photo_consumed` / `concurrent_conflict`；`422` 参数/建议缺失；`500`
- Idempotency：已 assigned 再 assign 同三元组 → 200 幂等；不同三元组 → 409（须先删除未消费图或走变更）

### API-M002-006 撤销/清理照片
- `DELETE /api/v1/photos/{photo_id}`（Bearer；执行者：家长或学生本人）
- 语义：仅 `consumed_at IS NULL` 的照片可删（物理删原/归文件 + 行 + 审计 reason=user_undo）；删除已 assigned 照片**不回退**任务状态
- Response `204`；Errors：`401`；`404`；`409 photo_consumed`；`500`

## 内部服务接口（进程内 Python Interface，供 M003/M007）

> 实现由 AGENT-M002（Task-002）提供；所有方法须传主体上下文（family_id + 可选 student_id 限制），越权抛 `PermissionDenied`（对外 404）。

| 接口 | 方法 | 说明 | 消费者 |
| --- | --- | --- | --- |
| `PhotoQueryService` | `list_photos(family_id, *, student_id=None, status=None, batch_id=None, task_id=None) -> list[PhotoDTO]` | 照片列表（含归属/建议摘要） | H5 后端、M007 |
| `PhotoQueryService` | `get_photo(family_id, photo_id) -> PhotoDTO` | 单照片详情 | M003/M007 |
| `PhotoQueryService` | `get_for_recognition(family_id, *, task_id=None, subject=None, group_no=None, photo_ids=None) -> list[PhotoDTO]` | 供 M003 识别取图（**同机本地路径直读**） | M003 |
| `PhotoQueryService` | `mark_consumed(family_id, photo_ids) -> None` | 识别完成后置 `consumed_at`（消费锁定） | M003 |
| `PhotoQueryService` | `count_assigned(family_id, task_id) -> int` | 任务已 assigned 照片数（归属上限校验；供判定链判断证据是否齐备） | M001(CR)、M003/M004(契约轮)、M007 |

> 说明：
> - `PhotoDTO` 含本地文件路径（original_path/normalized_path）——仅限同机进程内消费；对外一律 API-M002-004，禁止外发路径
> - `suggestion_json` 由 M003 内部写入（写接口归 M003 契约轮定稿）；`mark_consumed` 的调用时机（识别前锁定 or 完成后锁定）在 M003 契约轮确认
> - M002 消费的 M001 接口：`get_student` / `get_task` / `get_task_group`（CR-001）/ `can_accept_photo`（CR-001）/ `mark_in_progress`
