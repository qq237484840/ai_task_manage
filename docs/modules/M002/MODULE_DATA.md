# M002 模块数据（权威源）—— 作业图片采集与归属

- **状态**：**v0.4.0（Frozen，用户批准 2026-09-10）** —— 按 `CR-003`/`ADR-013`/`ADR-014` 修订：入口 `kind`（任务/作业）、**归属放开为 N:N（照片 ↔ 聚合子任务）**、新增 `completion_analyses`、`M003`/`M004` 前向引用清理；前版 v0.3.0 Frozen（2026-09-08）
- **Owner**：M002（DATA-003 / **DATA-016** / **DATA-017** 唯一写入口）；映射全局实体 **DATA-003 / DATA-016 / DATA-017**（`DATA_MODEL.md` 为全局登记，本文件字段级权威源）
- **存储**：SQLite 单文件 + **本地受控图片目录**（ADR-004/ASM-010）；文件与库记录同生命周期
- **依赖**：**M001 归属窗口 + 聚合层**（`tasks.belong_date`/`window_type`；`task_groups`；`task_group_subjects` = **★判定单元**，ADR-013）；主体两级（ADR-009/ACR-001）
- **权威源**：`docs/requirements/CLARIFICATION-2026-09-10.md`（冲突时以其为准）、`docs/adr/ADR-013.md`、`docs/adr/ADR-014.md`、`docs/CONFIGURATION.md`

## 表结构与字段

### `upload_batches`（上传批次 = 一次拍摄/上传会话，映射 DATA-003）

> 语义：学生（或家长代传）一次"拍照/选图上传会话"的组织单位；无状态机、不参与归属判定；仅作上传次序与审计记录。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `batch_id` | TEXT(UUID) | PK | 批次 ID |
| `family_id` | TEXT(UUID) | FK→family_accounts, NOT NULL | 归属家庭（索引） |
| `student_id` | TEXT(UUID) | FK→students, NOT NULL | 照片所属学生档案 |
| `kind` | TEXT | NOT NULL DEFAULT 'homework' | **上传入口类型** `task_spec` \| `homework`（**由菜单入口决定**：菜单「任务」→ `task_spec`；菜单「作业」→ `homework`）；**kind 的权威在本字段**，`photos.kind` 为其冗余副本 |
| `created_by_type` | TEXT | NOT NULL | 发起主体 `family\|student` |
| `created_by_id` | TEXT(UUID) | NOT NULL | 发起主体 id（student 会话 = 本人；family = 家庭账号） |
| `created_at` | TEXT(ISO) | NOT NULL | 创建时间 |

索引：`(family_id, student_id, created_at)`、`(student_id, created_at)`、`(family_id, kind, created_at)`。

### `photos`（照片记录，映射 DATA-003）

> 每行 = 一张**通过质检**的图（原始图 + 归一图），含归属状态机；`kind` 冗余自批次（由上传入口决定）。失败图**不建行不留文件**。**归属为 N:N**：具体归属对象由 `photo_subject_links`（DATA-016）承载（照片 ↔ 聚合学科子任务），本表 `task_id` 仅为**窗口级归属**。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `photo_id` | TEXT(UUID) | PK | 照片 ID |
| `batch_id` | TEXT(UUID) | FK→upload_batches, NOT NULL | 所属上传批次（索引） |
| `family_id` | TEXT(UUID) | FK→family_accounts, NOT NULL | **冗余归属家庭**（防御纵深：读取一律按此过滤，写入须与其批次一致，单测断言） |
| `student_id` | TEXT(UUID) | FK→students, NOT NULL | 照片所属学生（须 = 批次学生） |
| `kind` | TEXT | NOT NULL | 入口类型（冗余自 `upload_batches.kind`；`task_spec\|homework`），写入须与批次一致 |
| `seq_no` | INT | NOT NULL | 批次内页序（1 起，**服务端自增**，(batch_id, seq_no) UNIQUE） |
| `status` | TEXT | NOT NULL DEFAULT 'unassigned' | `unassigned/suggested/assigned/rejected`（N:N 语义：无 link / 有未确认建议 link / 有 ≥1 已确认 link / 家长判无效） |
| `task_id` | TEXT(UUID) | NULL | **窗口级归属**：照片归属窗口对应的 `tasks`（FK→tasks；可反推，冗余便于过滤/计数） |
| `assigned_at` | TEXT(ISO) | NULL | 归属生效时间（status=assigned） |
| `consumed_at` | TEXT(ISO) | NULL | 已消费（链路 H 分析完成/锁定）；非空后不可删/改派 |
| `created_by_type` / `created_by_id` | TEXT | NOT NULL | 上传主体（同批次规则） |
| `original_mime` | TEXT | NOT NULL | 原始类型（`image/jpeg|png|webp`） |
| `original_path` / `normalized_path` | TEXT | NOT NULL | 受控目录内相对路径（原图 / 归一图 JPEG） |
| `file_size_bytes` | INT | NOT NULL | 原始文件字节数 |
| `width` / `height` | INT | NOT NULL | 归一图宽高（px） |
| `sha256` | TEXT | NOT NULL | 原始图内容哈希 |
| `quality_report_json` | TEXT | NOT NULL | 质检快照：`{ruleset_version, checks:[{id,passed,value,threshold,severity}]}` |
| `created_at` / `updated_at` | TEXT(ISO) | NOT NULL | 审计时间 |
| ~~`subject`~~ | — | **Deprecated** | 原「归属学科」（CR-001 段级）→ 归属对象改由 `photo_subject_links.group_subject_id` 承载（ADR-013 / N:N） |
| ~~`group_no`~~ | — | **Deprecated** | 原「学科作业段序号」**作废**（ADR-013：学科作业段取消） |
| ~~`suggestion_json`~~ | — | **Deprecated** | 原「AI 归属建议快照」→ 建议态/确认态改由 `photo_subject_links`（`source=ai\|manual` + `confirmed_at`）承载（B3）；注释中「**M003 建议快照**」漂移**清理**（B7：现状仅 `m001`/`m002` 模块） |

约束：`UNIQUE(batch_id, seq_no)`；**归属校验（服务层）**：`photo_subject_links.group_subject_id` 须为 M001 存在的聚合学科子任务，且其归属学生 = `photos.student_id`、窗口可归属。索引：`(batch_id, seq_no)` UNIQUE、`(family_id, status, created_at)`、`(family_id, task_id)`、`(family_id, kind, created_at)`、`(student_id, created_at)`。
`family_id`/`student_id`/`kind` 与批次一致：由 M002 服务层单点保证，列入单测/集成断言。

### `photo_subject_links`（作业照片挂接，映射 DATA-016 —— **N:N**）

> 照片 ↔ **聚合学科子任务**（`task_group_subjects`，★判定单元）多对多挂接；承载 AI 建议态与确认态；**Owner = M002**。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `link_id` | TEXT(UUID) | PK | 挂接 ID |
| `photo_id` | TEXT(UUID) | FK→photos, NOT NULL | 照片（索引） |
| `family_id` | TEXT(UUID) | FK, NOT NULL | 归属家庭（防御纵深） |
| `group_subject_id` | TEXT(UUID) | NOT NULL | 聚合学科子任务引用（**M001 实体**，跨模块仅存引用、不建 FK） |
| `source` | TEXT | NOT NULL | 来源 `ai\|manual` |
| `confidence` | REAL | NULL | AI 置信度（`source=ai`） |
| `confirmed_at` | TEXT(ISO) | NULL | 家长/学生确认时间（非空 = 已确认挂接） |
| `rejected_at` | TEXT(ISO) | NULL | 驳回时间（建议被否，保留审计） |
| `created_at` / `updated_at` | TEXT(ISO) | NOT NULL | 审计时间 |

约束：`UNIQUE(photo_id, group_subject_id)`；索引 `(photo_id, confirmed_at)`、`(group_subject_id, confirmed_at)`；`confirmed_at` 与 `rejected_at` 互斥。

### `completion_analyses`（完成情况分析，映射 DATA-017）

> 聚合学科子任务级完成结论（依据照片 + 置信度 + 草稿/确认 + 重跑版本）；**Owner = M002**；确认后经 M001 内部接口回写 DATA-013。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `analysis_id` | TEXT(UUID) | PK | 分析 ID |
| `group_subject_id` | TEXT(UUID) | NOT NULL | 聚合学科子任务（索引；跨模块引用） |
| `family_id` | TEXT(UUID) | FK, NOT NULL | 归属家庭（索引；防御纵深） |
| `student_id` | TEXT(UUID) | FK→students, NOT NULL | 归属学生 |
| `conclusion` | TEXT | NOT NULL | `完成\|部分完成\|未完成\|无法判断` |
| `evidence_photo_ids` | TEXT(JSON) | NULL | 依据照片 id 列表 |
| `confidence` | REAL | NULL | 置信度 |
| `status` | TEXT | NOT NULL DEFAULT 'draft' | `draft\|confirmed`（确认后回写 DATA-013 `conclusion_status=confirmed`） |
| `model` / `prompt_version` | TEXT | NULL | 模型与 prompt 版本（可追溯） |
| `run_no` | INT | NOT NULL DEFAULT 1 | 重跑版本号（同一子任务多次分析递增） |
| `confirmed_by` / `confirmed_at` | TEXT | NULL | 确认人 / 时间 |
| `created_at` / `updated_at` | TEXT(ISO) | NOT NULL | 审计时间 |

约束：`UNIQUE(group_subject_id, run_no)`；同一子任务的当前草稿取最大 `run_no` 的 `draft`。

## 图片存储布局（本地受控目录）

```
<image_store.root>/                       # 默认 backend/data/images（ASM-010，随部署整体备份）
  <family_id>/
    <batch_id>/
      <seq_no>_<photo_id>.<orig_ext>     # 原始图（原样，mime 决定扩展名）
      <seq_no>_<photo_id>_n.jpg          # 归一图（恒 JPEG）
```

- 目录/文件名不含学生姓名等敏感文本；路径相对根存储，落库相对路径（迁移/备份可整体搬移）
- 不挂公开静态目录；进程内按相对路径读写；对外经 API-M002-004 鉴权流式返回
- 备份 = 数据库 dump + `<image_store.root>` 整体备份（ASM-010 约定）

## 约束与规则

- **双层归属过滤**：查询强制 `family_id`（学生主体另限本人 `student_id`）；`photos.family_id`/`student_id`/`kind` 必须等于其批次
- **入口 `kind` 权威**：`upload_batches.kind` 为准（菜单「任务」→ `task_spec`，菜单「作业」→ `homework`）；`photos.kind` 为冗余副本，写入时强校验一致
- **写入唯一 Owner**：M002 是 `upload_batches`/`photos`/`photo_subject_links`/`completion_analyses` 与图片文件的唯一写入口；M001 只读消费（挂接引用/判定目标）；无其他模块直写路径
- **挂接 N:N 与建议态**：AI 建议 = `photo_subject_links`（`source=ai`、`confirmed_at` 空）；确认 = 置 `confirmed_at`；驳回 = 置 `rejected_at`（保留审计）；**手工挂接路径必须保留**（降级兜底 B6）
- **失败不留痕**：质检被拒图片不写文件/不建行/不改任务状态
- **不可变与撤销**：`consumed_at IS NULL` 的照片可删除（物理删 + 行删 + 级联 `photo_subject_links` + 审计）；已消费不可变
- **文件-记录一致性**：先写文件后写行（同请求）；行失败 → 清理文件；存储失败 → 500 且无残留
- **in_progress 触发**：照片首次**确认挂接**（`photo_subject_links.confirmed_at` 落位）使窗口任务 assigned 计数 0→1 时，同事务调 M001 `TaskStateService.mark_in_progress`（幂等）；删除已确认照片不回退任务状态
- **窗口级门控**（B4）：窗口/聚合下全部照片挂接确认后才触发完成分析；未满足 → 提示「待复核 N 张」
- **数量上限**：批次内照片数 ≤ `upload.max_photos_per_batch`；单个聚合子任务已确认挂接数 ≤ `association.max_photos_per_subject`
- **敏感数据**：图片高敏感；挂接/分析/quality 快照随行存储；文件与作答内容不落普通日志

## 与全局数据模型的关系

- **M002 Owned**：DATA-003（`upload_batches`/`photos` + 本地图片目录）、DATA-016（`photo_subject_links`）、DATA-017（`completion_analyses`）—— 登记（Writer/Reader/敏感级别/生命周期）以 `DATA_MODEL.md` 为准，字段级以本文件为准；漂移时优先本文件并提请同步顶层
- **非 M002 Owned（只读引用）**：DATA-001（`tasks`，M001：`belong_date`/`window_type` 窗口归属）、DATA-012/013（`task_groups`/`task_group_subjects` 判定单元，M001：本模块只存 `group_subject_id` 引用）、DATA-004/005（识别/匹配结果，`app/core/ai/` + 本模块链路 H 写入，见 B5）
- **`M003`/`M004` 前向引用清理**（B7/`ADR-014`）：原「M003 识别」「M004 判定」表述统一改为**链路 T（M001）/ 链路 H（M002）+ 横切 `app/core/ai/`**；Module ID 保留但状态 **Deferred**，不再作为依赖方
