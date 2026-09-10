# M002 模块 API（权威源）—— 作业图片采集与归属

- **状态**：**v0.4.1（Frozen，用户批准 2026-09-10；v0.4.1 = `CR-004` Applied，仅 `API-M002-007` 响应体收敛，非破坏性）** —— v0.4.0 按 `CR-003`/`ADR-013`/`ADR-014` 修订（入口 `kind`、N:N 挂接、逐张复核、门控、完成分析）。既有 `API-M002-001/002/003/005` 修订；新增端点 API ID **已由 PM 分配 = `API-M002-007~011`**（`API_REGISTRY.md`；**已 Active**，`Task-008` 实施 + PM 复验）；前版 v0.4.0 Frozen（2026-09-10）、v0.3.0 Frozen（2026-09-08）
- **REST 前缀**：`/api/v1`；**认证**：全部接口需 `Authorization: Bearer <token>`
- **主体**（ADR-009/ACR-001）：`family`（家长，可代传任一本家学生，带 `student_id`）；`student`（仅本人，`student_id` 忽略/强制本人）
- **错误体统一**：`ErrorResponse { "code", "message", "request_id" }`（HTTP 映射见契约 Failure Behavior）
- **上传内容类型**：`multipart/form-data`；其余 `application/json`；时间一律 UTC ISO-8601
- **API ID**：既有 `API-M002-001~006` 由 PM 分配；**本变更新增端点 API ID = `API-M002-007~011`**（已由 PM 分配登记 `API_REGISTRY.md`，Draft；原「申请清单」见文末）
- **DTO 约定**：`QualityCheckItem = {id, passed, value, threshold, severity(reject|warn)}`；`QualityReport = {ruleset_version, passed, checks[]}`；`PhotoDTO = {photo_id, student_id, batch_id, kind, seq_no, status, task_id(窗口级), links:[LinkDTO], quality, content_urls, created_at}`
  - `LinkDTO = {link_id, group_subject_id, subject(展示用), source(ai|manual), confidence|null, confirmed_at|null, rejected_at|null}`
  - **`LinkSuggestionItem`（v0.4.1，`CR-004`）= {link_id, group_subject_id, subject|null(展示用), confidence|null, source(ai|manual), suggested_at}**；**`LinkSuggestionResult` = `API-M002-007` 响应 `{photo_id, status, suggestions:[LinkSuggestionItem]}`**
  - `GateStatusDTO = {group_key, window_type, total_photos, pending_photos, satisfied}`
  - ~~`Suggestion = {task_id, subject, group_no, ...}`（段级）~~ **作废**（ADR-013；建议态改由 `links` 承载）

## 公共 REST API 清单

| API ID | 名称 | Method/Path | 摘要 |
| --- | --- | --- | --- |
| API-M002-001 | 创建上传批次（修订） | POST `/upload-batches` | 开启上传会话；**新增 `kind`**（菜单「任务」→ `task_spec` ／「作业」→ `homework`，权威字段） |
| API-M002-002 | 上传作业照片（修订） | POST `/photos` | multipart 单张：校验→质检→归一→入库 `unassigned`（**不填任何内容**；`kind` 冗余自批次） |
| API-M002-003 | 照片列表/待处理队列（修订） | GET `/photos` | 按学生/状态/批次/窗口/子任务过滤（含 **N:N 挂接关系**摘要） |
| API-M002-004 | 受控取图 | GET `/photos/{photo_id}/content` | 原图/归一图内容流（鉴权 + 访问审计 + Range）（不变） |
| API-M002-005 | 照片挂接复核（修订） | POST `/photos/{photo_id}/links` | **逐张复核**：accept / reject / 改挂（manual）；可跨学科多条；首条确认触发 `in_progress` |
| API-M002-006 | 撤销/清理照片 | DELETE `/photos/{photo_id}` | 删除未消费照片（物理删 + 审计）；已消费 409（不变） |
| API-M002-007 | 挂接建议查询/重试 | GET `/photos/{photo_id}/link-suggestions` | 查询（或触发重试）AI 挂接建议（异步结果） |
| API-M002-008 | 门控状态查询 | GET `/photo-gates` | 窗口级门控：总照片 / 待复核 N / 是否满足（`?group_key=`） |
| API-M002-009 | 完成分析生成 | POST `/completion-analyses` | 对窗口内聚合子任务生成完成情况草稿（**门控未达成 409**） |
| API-M002-010 | 完成分析确认 | POST `/completion-analyses/{analysis_id}/confirmation` | 家长确认草稿 → 回写 M001 判定单元（`commit_conclusion`） |
| API-M002-011 | 完成分析重跑 | POST `/completion-analyses/{analysis_id}/rerun` | 重跑（`run_no` 递增）生成新草稿 |

> 上列 5 端点 = `CHANGE-003` §2.2 B8 申请清单；**ID 由 Project Master 于 2026-09-10 分配**并登记 `API_REGISTRY.md`（状态 Draft，随实施转 Active）。

## 详细契约

### API-M002-001 创建上传批次（修订）
- `POST /api/v1/upload-batches`（Bearer）
- Request：`{ "student_id": "uuid?", "kind": "homework|task_spec" }` —— family 主体必填本家学生；student 主体忽略（=本人）；**`kind` 由菜单入口决定**（缺省 `homework`），本表字段为权威
- Response `201`：`{ "batch_id": "uuid", "family_id": "uuid", "student_id": "uuid", "kind": "homework", "created_by_type": "family|student", "created_by_id": "uuid", "created_at": "..." }`
- Errors：`401`；`403/404` student 越权/不存在（对外 404）；`422` `kind` 非法；`500`

### API-M002-002 上传作业照片
- `POST /api/v1/photos`（Bearer）
- Request：`multipart/form-data`
  - `file`（必填）：图片文件（`image/jpeg|png|webp`，≤10MB）
  - `batch_id`（必填，uuid）：归属的上传批次
- 处理流程（单事务）：
  1. 校验批次归属（本家庭 + 学生主体仅本人 + **`kind` 冗余自批次**）与批次计数 < `upload.max_photos_per_batch`（超限 422 `batch_photo_limit`）
  2. 基础校验（类型 415 / 大小 413 / 像素上限 422）→ 本地规则质检（v1.0）
  3. 未通过 → **不入库**：`422 image_quality_rejected`（message 逐项原因），无任何残留
  4. 通过 → 轻量归一 → 原始图+归一图写受控存储 → 插入 `photos` 行（`seq_no` = 批次当前最大 + 1，**服务端自增**；status=`unassigned`）
  5. **异步触发挂接建议**（不阻塞本响应）；建议失败 → 照片维持 `unassigned`，家长可**手工挂接**（降级 B6）
- Response `201`：
```json
{
  "photo_id": "uuid",
  "batch": { "batch_id": "uuid", "student_id": "uuid", "kind": "homework" },
  "kind": "homework",
  "seq_no": 1,
  "status": "unassigned",
  "quality": { "ruleset_version": "v1.0", "passed": true, "checks": [] },
  "content_urls": { "original": "/api/v1/photos/<photo_id>/content?kind=original", "normalized": "/api/v1/photos/<photo_id>/content?kind=normalized" }
}
```
> 「作业」入口上传时**不携带任何内容**（不选任务、不选学科、不填文本）。
- Errors：`401`；`404` 批次不存在/越权（对外 404）；`409 concurrent_conflict`（并发争用）；`413 image_too_large`；`415 unsupported_media_type`；`422` 校验失败 / `image_quality_rejected` / `batch_photo_limit`；`500`
- Idempotency：不幂等（每次上传产生新照片；前端去抖）；重试产生重复页，可走 DELETE 清理

### API-M002-003 照片列表/待处理队列（修订）
- `GET /api/v1/photos?student_id=&status=&batch_id=&kind=&task_id=&group_subject_id=&page=&page_size=`（Bearer）
- Query：family 主体可按本家学生过滤；student 主体强制本人。`status ∈ unassigned|suggested|assigned|rejected`（可组合，缺省全部）；`kind ∈ task_spec|homework`；`task_id` 过滤**窗口级归属**；`group_subject_id` 过滤已挂接该聚合子任务的照片
- Response `200`：
```json
{
  "items": [
    {
      "photo_id": "uuid", "student_id": "uuid", "batch_id": "uuid", "kind": "homework", "seq_no": 1,
      "status": "suggested", "created_at": "...",
      "task_id": "uuid",
      "links": [
        { "link_id": "uuid", "group_subject_id": "uuid", "subject": "math", "source": "ai", "confidence": 0.87, "confirmed_at": null, "rejected_at": null }
      ],
      "quality": { "ruleset_version": "v1.0", "passed": true, "checks": [] },
      "content_urls": { "original": "...", "normalized": "..." }
    }
  ],
  "page": 1, "page_size": 20, "total": 1
}
```
- Errors：`401`；`404` 越权（对外 404）；`422` 参数非法
> ~~`assignment`（`subject`/`group_no` 段级）~~ / ~~`suggestion` 段级快照~~ **作废**（ADR-013）；改由 `links`（N:N）承载。

### API-M002-004 受控取图
- `GET /api/v1/photos/{photo_id}/content?kind=original|normalized`（Bearer；kind 缺省 = `normalized`）
- 行为：校验照片归属当前主体（family 本家 / student 本人）→ 写访问审计（photo_id/kind/subject/request_id/ts）→ 流式返回（`normalized` 恒 JPEG；`original` 按原始 mime），支持 `Range`
- Response `200 image/*`；Errors：`401`；`404` 不存在/越权/文件缺失（同 404）；`422` kind 非法

### API-M002-005 照片挂接复核（修订）
- `POST /api/v1/photos/{photo_id}/links`（Bearer；执行者：家长或学生本人）
- Request：`{ "action": "accept|reject|relink", "group_subject_id": "uuid?", "link_id": "uuid?" }`
  - `accept`：确认挂接 —— 以 `link_id` 定位 AI 建议 link 并置 `confirmed_at`；若仅给 `group_subject_id` 则为**手工挂接**（`source=manual` + `confirmed_at`，兜底 B6）
  - `reject`：驳回 —— 置 `rejected_at`（保留审计）；照片可另挂
  - `relink`：改挂 —— 先驳回旧 link，再新建 `source=manual` + `confirmed_at` 的 link
  - **一张照片可跨学科挂接多条**（N:N）；同一子任务重复挂接幂等
- 处理（单事务）：
  1. 校验照片未被消费（`consumed_at IS NULL`，否则 409 `photo_consumed`）
  2. 校验目标：M001 `get_group` 中存在 `group_subject_id`、其归属学生 = 照片学生、所属窗口任务可挂接（`published|in_progress`，否则 409 `task_not_acceptable`）、该子任务已确认挂接 < `association.max_photos_per_subject`（409 `subject_photo_limit`）
  3. 写入/更新 `photo_subject_links`；照片存在 ≥1 `confirmed_at` → `status=assigned`，并置 `assigned_at`
  4. 照片**首条确认挂接**使窗口任务计数 0→1 → 同事务调 M001 `mark_in_progress`（幂等）
- Response `200`：`{ "photo_id": "uuid", "status": "assigned|suggested|rejected", "links": [LinkDTO], "gate": GateStatusDTO }`
- Errors：`401`；`404`；`409` `task_not_acceptable` / `subject_photo_limit` / `photo_consumed` / `concurrent_conflict`；`422` 参数非法；`500`
- Idempotency：同照片同 `group_subject_id` 重复 accept → 200 幂等

### API-M002-006 撤销/清理照片
- `DELETE /api/v1/photos/{photo_id}`（Bearer；执行者：家长或学生本人）
- 语义：仅 `consumed_at IS NULL` 的照片可删（物理删原/归文件 + 行 + 审计 reason=user_undo）；删除已 assigned 照片**不回退**任务状态
- Response `204`；Errors：`401`；`404`；`409 photo_consumed`；`500`

## CR-003 新增端点详细契约（API-M002-007~011）

### API-M002-007 挂接建议查询/重试（**响应体 v0.4.1 = `CR-004` Applied，以运行实现为准**）
- `GET /api/v1/photos/{photo_id}/link-suggestions?retry=false`（Bearer；`retry` 缺省 `false`）
- 语义：返回该照片**当前有效**的挂接项 —— `rejected_at IS NULL` 的 `photo_subject_links`（含 `source=ai` 未确认建议、`source=manual` 手工挂接、以及已确认项）；`retry=true` 触发**幂等**重试建议（仅处理未挂接照片；AI 不可用时静默降级、不报错）
- `subject` 为**展示用**学科名（经 M001 契约内接口解析），解析失败时为 `null`
- Response `200`：
```json
{
  "photo_id": "uuid",
  "status": "unassigned|suggested|assigned|rejected",
  "suggestions": [
    { "link_id": "uuid", "group_subject_id": "uuid", "subject": "数学",
      "confidence": 0.87, "source": "ai", "suggested_at": "2026-09-10T10:06:48.613Z" }
  ]
}
```
  - `status` = 照片状态；`suggested_at` = 该挂接项创建时间（UTC ISO-8601）；`suggestions` 为空数组表示无有效挂接项
- Errors：`401`；`404`（照片不存在 / 越权，对外 404）；`500`

### API-M002-008 门控状态查询
- `GET /api/v1/photo-gates?student_id=&group_key=`（Bearer）
- 语义：窗口级门控状态 —— 总照片数 / **待复核 N** / 是否满足（满足 = 该窗口全部照片挂接已确认）
- Response `200`：`GateStatusDTO`（可返回数组，按窗口）
- Errors：`401`；`404`；`422`

### API-M002-009 完成分析生成
- `POST /api/v1/completion-analyses`（Bearer）
- Request：`{ "student_id": "uuid", "group_key": "string" }`
- 语义：对窗口内每个聚合学科子任务经 `app/core/ai/` 生成完成情况草稿 → 写 `completion_analyses`（`status=draft`、`run_no` = 当前最大 +1）
- **门控前置**：窗口内存在未确认挂接照片 → 409 `gate_not_satisfied`（附「待复核 N 张」）
- Response `201`：`{ "items": [ { "analysis_id", "group_subject_id", "conclusion", "confidence", "status": "draft", "run_no" } ] }`
- Errors：`401`；`404`；`409 gate_not_satisfied`；`422`；`500`（AI 失败 → 草稿 `无法判断` + 提示手工）

### API-M002-010 完成分析确认
- `POST /api/v1/completion-analyses/{analysis_id}/confirmation`（Bearer）
- Request：`{ "conclusion": "完成|部分完成|未完成|无法判断?" }`（可校正）
- 语义：置 `status=confirmed` + `confirmed_at` → **经 M001 `commit_conclusion` 回写** `task_group_subjects`（同事务编排）→ 置相关照片 `consumed_at`（消费锁定）
- Response `200`：`{ "analysis_id", "group_subject_id", "conclusion", "status": "confirmed" }`
- Errors：`401`；`404`；`409 已确认/concurrent_conflict`；`422`

### API-M002-011 完成分析重跑
- `POST /api/v1/completion-analyses/{analysis_id}/rerun`（Bearer）
- 语义：重跑分析（`run_no` 递增）生成新草稿（覆盖当前草稿；已确认结论不被覆盖，须先撤销确认——V1 重跑仅限 `draft`）
- Response `201`：新草稿 `{analysis_id, conclusion, status:"draft", run_no}`
- Errors：`401`；`404`；`409`（已确认）；`422`

## 内部服务接口（进程内 Python Interface，供 M001/M007）

> 实现由 AGENT-M002（Task-002，增量改接）提供；所有方法须传主体上下文（family_id + 可选 student_id），越权抛 `PermissionDenied`（对外 404）。

| 接口 | 方法 | 说明 | 消费者 |
| --- | --- | --- | --- |
| `PhotoQueryService` | `list_photos(family_id, *, student_id=None, status=None, batch_id=None, kind=None, task_id=None, group_subject_id=None) -> list[PhotoDTO]` | 照片列表（含 **N:N links** 摘要） | H5 后端、（V2）M007 |
| `PhotoQueryService` | `get_photo(family_id, photo_id) -> PhotoDTO` | 单照片详情 | （V2）M007 |
| `PhotoQueryService` | `get_gate_status(family_id, *, student_id=None, group_key=None) -> list[GateStatusDTO]` | **窗口级门控状态** | H5、M002 内部 |
| `PhotoQueryService` | `list_confirmed_links(family_id, group_subject_id) -> list[PhotoDTO]` | 某聚合子任务的已确认挂接照片（分析取图） | M002 内部、M001（计数） |
| `PhotoQueryService` | `count_confirmed_links(family_id, group_subject_id) -> int` | 子任务已确认挂接照片数（上限校验 / 证据齐备判断） | M001、M002 |
| `PhotoLinkService` | `migrate_links(family_id, task_id, old_group_key, new_group_key) -> None` | **改归属日时迁移挂接目标**（M001 在事务中回调，A8/R6） | M001（反向调用） |

> 说明：
> - `PhotoDTO` 含本地文件路径（original_path/normalized_path）——**仅限同机进程内消费**；对外一律 API-M002-004，禁止外发路径
> - 挂接建议与分析**均由 M002 经 `app/core/ai/` 生成**（不再有 M003/M004 写接口；`ADR-014` 决议 1）
> - M002 消费的 M001 接口（v0.2.0）：`get_student` / `get_task` / `list_groups` / `get_group` / `ensure_group` / `commit_conclusion` / `mark_in_progress`
> - 已废弃（v0.3.0 段级语义）：~~`get_for_recognition(subject, group_no)`~~、~~`mark_consumed`（改由分析确认触发）~~、~~`count_assigned(task_id)`（改按子任务 `count_confirmed_links`）~~

## API ID 申请清单（**已由 PM 分配**，2026-09-10；登记 `API_REGISTRY.md`）

> 依据 `CHANGE-003` §2.2 B8；**禁止模块 Agent 自行编号**（`ID_GOVERNANCE.md`）。同时列明**既有端点修订**（不新增 ID，走 CR 修订）。

| 申请序号 | 名称 | Method/Path | 用途 | 分配 ID |
| --- | --- | --- | --- | --- |
| M002-B1 | 挂接建议查询/重试 | GET `/api/v1/photos/{photo_id}/link-suggestions` | 查询/重试 AI 挂接建议 | **API-M002-007** |
| M002-B2 | 门控状态查询 | GET `/api/v1/photo-gates` | 窗口级门控（待复核 N / 是否满足） | **API-M002-008** |
| M002-B3 | 完成分析生成 | POST `/api/v1/completion-analyses` | 生成完成情况草稿（门控前置） | **API-M002-009** |
| M002-B4 | 完成分析确认 | POST `/api/v1/completion-analyses/{analysis_id}/confirmation` | 确认草稿 → 回写判定单元 | **API-M002-010** |
| M002-B5 | 完成分析重跑 | POST `/api/v1/completion-analyses/{analysis_id}/rerun` | 重跑生成新草稿 | **API-M002-011** |

**既有端点修订（不新增 ID）**：`API-M002-001`（加 `kind`）、`API-M002-002`（`kind` 冗余 + 异步建议）、`API-M002-003`（`links` 替代 `assignment`/`suggestion`）、`API-M002-005`（归属操作 → **挂接复核**，路径 `/associate` → `/links`）。`API-M002-004`、`API-M002-006` 语义不变。
