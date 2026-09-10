# M002 模块设计（白盒）—— 作业图片采集与挂接

- **状态**：**v0.4.0（Frozen，用户批准 2026-09-10）** —— 代码基线 v0.3.0（Task-002 完成，pytest 112）；本设计描述 **CR-003 修订后目标态**，实施 = **`Task-008`**（已签发，契约已定稿）；Task-002 冻结段自本定稿起增量改接
- **技术栈**：FastAPI + SQLite + Pillow（质检/归一纯本地，无外部 AI 依赖）；AI 能力经 **`app/core/ai/`**（横切，`AGENT-AI`/Task-006）调用（Provider 按 ADR-011：真实三方默认，Mock 测试桩/离线降级）
- **目录**：`backend/app/modules/m002/`

## 分层与职责

```
m002/
├─ domain/
│   ├─ models.py            # upload_batches(含 kind) / photos / photo_subject_links / completion_analyses（字段见 MODULE_DATA.md）
│   ├─ enums.py             # PhotoStatus、LinkSource(ai|manual)、AnalysisStatus(draft|confirmed)、BatchKind、错误码
│   └─ errors.py            # 统一异常（见 CONTRACT Failure Behavior）
├─ repository/
│   ├─ batch_repository.py
│   ├─ photo_repository.py   # 状态/计数/消费标记（全部带 family_id + student 过滤）
│   ├─ link_repository.py    # **新增**：photo_subject_links 读写（N:N，建议/确认/驳回）
│   └─ analysis_repository.py# **新增**：completion_analyses 读写（草稿/确认/重跑）
├─ services/
│   ├─ quality.py           # QualityChecker 协议 + LocalQualityChecker v1.0
│   ├─ normalizer.py        # 轻量归一管线
│   ├─ image_store.py       # 受控存储：相对路径读写/删除/哈希/审计
│   ├─ upload_service.py    # 批次创建（kind）+ 单张上传事务（校验→质检→归一→入库 unassigned；异步触发建议）
│   ├─ link_service.py      # **新增**：挂接建议 / 逐张复核（accept/reject/relink）/ 手工挂接 / 首确认触发 mark_in_progress
│   ├─ gate_service.py      # **新增**：窗口级门控（待复核 N / 是否满足）
│   ├─ analysis_service.py  # **新增**：完成分析生成/确认/重跑（经 ai client；确认经 M001 commit_conclusion）
│   ├─ undo_service.py      # 删除未消费照片（审计）
│   └─ photo_query_service.py  # 供 REST/内部（list/get/gate/confirmed_links/count）
├─ api/
│   ├─ upload_routes.py     # API-M002-001/002
│   ├─ photo_routes.py      # API-M002-003/004
│   ├─ link_routes.py       # **新增**：API-M002-005（复核）+ 挂接建议查询
│   ├─ gate_routes.py       # **新增**：门控状态
│   ├─ analysis_routes.py   # **新增**：完成分析生成/确认/重跑
│   └─ schemas.py           # DTO（见 MODULE_API.md）
├─ clients/
│   ├─ task_client.py       # M001 内部接口封装（get_student/get_task/list_groups/get_group/ensure_group/commit_conclusion/mark_in_progress）
│   └─ ai_client.py         # **`app/core/ai/` 调用封装**（挂接建议 + 完成分析；Provider 按 ADR-011，Mock 注入用于测试）
└─ config.py                # 配置项（见 CONTRACT Configuration）
```

> **B7 漂移清理**：原 `clients/recognition_client.py# M003 建议写接口` 与注释中「M003 识别 / M004 判定」表述**删除**（`ADR-014`：M003/M004 职责并入链路 H）；统一改为 `ai_client.py`（经 `app/core/ai/`）+ 链路 T（M001）/ 链路 H（M002）。

## 关键流程

### 上传管线（API-M002-002）
```
Bearer → subject 上下文（family/student）
 → 校验 batch 归属 + kind 冗余一致 + 计数 < max_photos_per_batch
 → MIME/大小/像素硬校验（415/413/422）
 → LocalQualityChecker.run(img) 逐项（ruleset v1.0）
     └─ 任一 reject 级未过 → 422 image_quality_rejected（不入库、无残留）
 → 归一管线（exif_transpose → RGB → JPEG(88) → 长边≤2000）
 → 原图+归一图写 <image_store.root>/family/batch/
 → 单事务 INSERT photos（seq_no = batch 当前 max + 1，服务端自增；status=unassigned；kind 冗余）
 → 提交后异步入队「挂接建议」（幂等；失败不影响上传，照片留 unassigned）
```
并发：同批次上传以 `(family_id, batch_id)` 应用级互斥串行化；冲突 `409 concurrent_conflict`。

### 挂接状态机（API-M002-005，N:N）
```
unassigned ─(AI 建议，写 photo_subject_links[source=ai, confirmed_at=null])→ suggested
suggested|unassigned ─ accept(link_id) 或 手工挂接(group_subject_id) → 置 confirmed_at → assigned（照片）
suggested ─ reject(link_id) → 置 rejected_at（照片可另挂）
assigned ─ relink → 驳回旧 link + 新建 manual link
照片存在 ≥1 confirmed link → status=assigned；家长判无效 → status=rejected
首条 confirmed link（窗口任务计数 0→1）→ 同事务 mark_in_progress（幂等）
```
挂接校验：目标 `group_subject_id` 存在（M001 `get_group`）且其归属学生=照片学生；窗口任务 `published|in_progress`（否则 409 `task_not_acceptable`）；子任务已确认挂接 < `association.max_photos_per_subject`；消费锁定校验。

### 窗口级门控（gate_service）
- 输入：学生 + `group_key`（或归属窗口）→ 取窗口内全部照片与挂接确认状态
- 输出：`GateStatusDTO{group_key, window_type, total_photos, pending_photos, satisfied}`；`satisfied = pending_photos == 0`
- **门控是分析前置**：`POST /completion-analyses` 未满足 → 409 `gate_not_satisfied`（附「待复核 N 张」）

### 完成分析（analysis_service，B4/B5）
- 生成：门控通过后，对窗口内每个聚合学科子任务，经 `ai_client` 得结论草稿（`完成/部分完成/未完成/无法判断` + `evidence_photo_ids` + `confidence`）→ 写 `completion_analyses`（`status=draft`，`run_no` = 当前最大+1）
- 确认：置 `status=confirmed` → 同事务经 M001 `commit_conclusion` 回写 `task_group_subjects` → 置相关照片 `consumed_at`（消费锁定）
- 重跑：`run_no` 递增生成新草稿（V1 仅限 `draft`；已确认须先撤销）
- 降级：AI 失败/返回不合规 → 草稿 `conclusion=无法判断` + 提示手工结论（不阻断）

### 识别消费（原 M003 语义，收窄为"分析消费锁定"）
- 分析确认后置 `photos.consumed_at` → 删除 409 `photo_consumed`；改派禁止
- 挂接建议/分析**均由 M002 经 `app/core/ai/` 生成**（不再有 M003/M004 写接口；测试注入 `MockAiClient`）

## 关键实现约束

- **同一数据库会话/事务**内完成状态变更与跨模块调用；`mark_in_progress`/`commit_conclusion` 失败 → 整体回滚
- 图片解码资源控制（尺寸/解压上限）；Pillow 版本钉死；`Image.MAX_IMAGE_PIXELS` 放宽点 + 显式上限（60MP）
- 所有查询强制双层过滤（family_id + student 主体仅本人）；文件路径仅进程内，不序列化给外部
- 审计：上传/质检被拒/挂接建议/确认/驳回/改挂/门控达成/分析草稿·确认·重跑/删除/受控取图/挂接迁移 入 audit
- 时间一律 UTC；状态变更写 `updated_at`

## 与相邻模块边界（防御）

- M002 不做 AI 模型内部实现（挂接建议/完成分析经 `app/core/ai/`）；不做任务/聚合管理（M001）
- M002 不读写 M001 的业务表——一律经 `task_client` 内部接口（v0.2.0）
- **M002 不得直写 M001 `task_group_subjects`**；结论只能经 `commit_conclusion`
- 改归属日时由 M001 在事务中回调 `PhotoLinkService.migrate_links`（挂接目标迁移）
