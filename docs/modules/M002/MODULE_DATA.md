# M002 模块数据（权威源）—— 作业图片采集与归属

- **状态**：Frozen —— 契约基线 v0.3.0 已由用户批准（2026-09-08），字段级变更走 CR
- **Owner**：M002（DATA-003 唯一写入口）；映射全局实体 DATA-003（`DATA_MODEL.md` 为全局登记，本文件字段级权威源）
- **存储**：SQLite 单文件 + **本地受控图片目录**（ADR-004/ASM-010）；文件与库记录同生命周期
- **依赖**：任务/学科作业段来自 M001（CR-001：`task_items.group_no`，段标识 `(task_id, subject, group_no)`）；主体两级（ADR-009/ACR-001）

## 表结构与字段

### `upload_batches`（上传批次 = 一次拍摄/上传会话，映射 DATA-003）

> 语义：学生（或家长代传）一次"拍照/选图上传会话"的组织单位；无状态机、不参与归属判定；仅作上传次序与审计记录。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `batch_id` | TEXT(UUID) | PK | 批次 ID |
| `family_id` | TEXT(UUID) | FK→family_accounts, NOT NULL | 归属家庭（索引） |
| `student_id` | TEXT(UUID) | FK→students, NOT NULL | 照片所属学生档案 |
| `created_by_type` | TEXT | NOT NULL | 发起主体 `family\|student` |
| `created_by_id` | TEXT(UUID) | NOT NULL | 发起主体 id（student 会话 = 本人；family = 家庭账号） |
| `created_at` | TEXT(ISO) | NOT NULL | 创建时间 |

索引：`(family_id, student_id, created_at)`、`(student_id, created_at)`。

### `photos`（照片记录，映射 DATA-003）

> 每行 = 一张**通过质检**的图（原始图 + 归一图），含归属状态机。失败图**不建行不留文件**。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `photo_id` | TEXT(UUID) | PK | 照片 ID |
| `batch_id` | TEXT(UUID) | FK→upload_batches, NOT NULL | 所属上传批次（索引） |
| `family_id` | TEXT(UUID) | FK→family_accounts, NOT NULL | **冗余归属家庭**（防御纵深：读取一律按此过滤，写入须与其批次一致，单测断言） |
| `student_id` | TEXT(UUID) | FK→students, NOT NULL | 照片所属学生（须 = 批次学生） |
| `seq_no` | INT | NOT NULL | 批次内页序（1 起，**服务端自增**，(batch_id, seq_no) UNIQUE） |
| `status` | TEXT | NOT NULL DEFAULT 'unassigned' | `unassigned/suggested/assigned/rejected`（状态机见契约） |
| `task_id` | TEXT(UUID) | NULL | 归属目标任务（suggested/assigned 有值；FK→tasks） |
| `subject` | TEXT | NULL | 归属学科（段 subject，与 task_items.group 一致） |
| `group_no` | INT | NULL | 归属学科作业段序号（CR-001） |
| `suggestion_json` | TEXT | NULL | AI（M003）归属建议快照：`{task_id, subject, group_no, confidence, model, prompt_version, suggested_at}` |
| `assigned_at` | TEXT(ISO) | NULL | 归属生效时间（status=assigned） |
| `consumed_at` | TEXT(ISO) | NULL | 已消费（M003 识别完成/锁定）；非空后不可删/改派 |
| `created_by_type` / `created_by_id` | TEXT | NOT NULL | 上传主体（同批次规则） |
| `original_mime` | TEXT | NOT NULL | 原始类型（`image/jpeg|png|webp`） |
| `original_path` / `normalized_path` | TEXT | NOT NULL | 受控目录内相对路径（原图 / 归一图 JPEG） |
| `file_size_bytes` | INT | NOT NULL | 原始文件字节数 |
| `width` / `height` | INT | NOT NULL | 归一图宽高（px） |
| `sha256` | TEXT | NOT NULL | 原始图内容哈希 |
| `quality_report_json` | TEXT | NOT NULL | 质检快照：`{ruleset_version, checks:[{id,passed,value,threshold,severity}]}` |
| `created_at` / `updated_at` | TEXT(ISO) | NOT NULL | 审计时间 |

约束：`UNIQUE(batch_id, seq_no)`；归属校验（服务层）：`(task_id, subject, group_no)` 须为 M001 存在的学科作业段且任务 `student_id = photos.student_id`。索引：`(batch_id, seq_no)` UNIQUE、`(family_id, status, created_at)`、`(family_id, task_id)`（归属计数/过滤）、`(student_id, created_at)`。
`family_id` 与批次一致、`student_id` 与批次一致：由 M002 服务层单点保证，列入单测/集成断言。

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

- **双层归属过滤**：查询强制 `family_id`（学生主体另限本人 `student_id`）；`photos.family_id`/`student_id` 必须等于其批次
- **写入唯一 Owner**：M002 是两表与图片文件的唯一写入口；M003 仅经内部接口写 `suggestion_json` 与 `mark_consumed`，M007 只读
- **失败不留痕**：质检被拒图片不写文件/不建行/不改任务状态
- **不可变与撤销**：`consumed_at IS NULL` 的照片可删除（物理删 + 行删 + 审计）；已消费不可变；任务题目冻结语义随 CR-001 调整为"存在 assigned 照片"（M001 侧保障，M002 提供计数）
- **文件-记录一致性**：先写文件后写行（同请求）；行失败 → 清理文件；存储失败 → 500 且无残留
- **in_progress 触发（新语义）**：associate 使任务 assigned 计数 0→1 时，同事务调 `TaskStateService.mark_in_progress`（幂等）；删除已 assigned 照片不回退任务状态
- **数量上限**：批次内照片数 ≤ `upload.max_photos_per_batch`；任务已 assigned ≤ `association.max_photos_per_task`
- **敏感数据**：图片高敏感；suggestion/quality 快照随行存储；文件与作答内容不落普通日志

## 与全局数据模型的关系

- DATA-003 登记（Writer/Reader/敏感级别/生命周期）以 `DATA_MODEL.md` 为准；字段级以本文件为准；漂移时优先本文件并提请同步顶层
- DATA-001（tasks/task_items + CR-001 group_no）与 DATA-002（两级主体）变更随 `CR-001`/`ACR-001`/`CR-002`/`ACR-002` 批准（均 Approved）后由 M001/MODULE 与 `DATA_MODEL.md` 同步；判定结果字段归 DATA-004/005（M003/M004，v0.3.0），M002 不持有判定结果
