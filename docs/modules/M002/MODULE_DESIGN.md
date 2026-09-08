# M002 模块设计（白盒）—— 作业图片采集与归属

- **状态**：实现中（契约 **v0.3.0 Frozen**，2026-09-08 批准）｜ 与黑盒契约（`MODULE_CONTRACT.md`）一致；实现细节随 Task-002 完成并回填
- **技术栈**：FastAPI + SQLite + Pillow（M002 质检/归一纯本地、无外部 AI 依赖，D1/D2 保留）；单体（ADR-004/ASM-010）；AI Provider 按 ADR-011（真实三方默认，Mock 测试桩/离线降级）
- **目录**：M002 归属 `backend/app/modules/m002/`（后端骨架 + M001 先例见 `docs/modules/M001/`）

## 分层与职责

```
m002/
├─ domain/
│   ├─ models.py            # upload_batches / photos ORM（字段见 MODULE_DATA.md）
│   ├─ enums.py             # PhotoStatus(unassigned|suggested|assigned|rejected)、归属错误码
│   └─ errors.py            # 统一异常（见 CONTRACT Failure Behavior）
├─ repository/
│   ├─ batch_repository.py
│   └─ photo_repository.py  # 归属/状态/计数/消费标记（全部带 family_id + student 过滤）
├─ services/
│   ├─ quality.py           # QualityChecker 协议 + LocalQualityChecker v1.0（D1）
│   ├─ normalizer.py        # 轻量归一管线（D2）
│   ├─ image_store.py       # 受控存储：相对路径读写/删除/哈希/审计
│   ├─ upload_service.py    # 批次创建 + 单张上传事务（校验→质检→归一→入库 unassigned）
│   ├─ association_service.py  # 归属状态机 + 首触发 mark_in_progress + 上限/并发控制（D5/D8）
│   ├─ undo_service.py      # 删除未消费照片（D7，审计）
│   └─ photo_query_service.py  # 供 REST/内部（list/get/recognition/mark_consumed/count_assigned）
├─ api/
│   ├─ upload_routes.py     # API-M002-001/002
│   ├─ photo_routes.py      # API-M002-003/004
│   ├─ association_routes.py# API-M002-005/006
│   └─ schemas.py           # DTO（见 MODULE_API.md）
├─ clients/
│   ├─ task_client.py       # M001 内部接口封装（get_task_group/can_accept_photo/mark_in_progress 等，CR-001）
│   └─ recognition_client.py# M003 建议写接口（契约轮对接；Provider 默认真实三方 ADR-011，Mock 仅测试桩注入 suggestion）
└─ config.py                # 配置项（见 CONTRACT Configuration）
```

## 关键流程

### 上传管线（API-M002-002）
```
Bearer → subject 上下文（family/student）
 → 校验 batch 归属 & 计数 < max_photos_per_batch
 → MIME/大小/像素硬校验（415/413/422）
 → LocalQualityChecker.run(img) 逐项（ruleset v1.0）
     └─ 任一 reject 级未过 → 422 image_quality_rejected（不入库、无残留）
 → 归一管线（exif_transpose → RGB → JPEG(88) → 长边≤2000）
 → 原图+归一图写 <image_store.root>/family/batch/
 → 单事务 INSERT photos（seq_no = batch 当前 max + 1，服务端自增；status=unassigned）
```
并发：同批次上传以 `(family_id, batch_id)` 应用级互斥（进程级锁 or 行级/唯一约束重试）串行化；冲突 `409 concurrent_conflict`（D8）。

### 归属状态机（API-M002-005）
```
unassigned ─(M003 suggestion)→ suggested
unassigned|suggested ─ assign/confirm_suggestion → assigned（写三元组+assigned_at）
unassigned|suggested ─ reject → rejected（终态，可删除）
assigned ─(消费前，家长)→ 可 delete（不回退任务）；consumed 后不可变
首张 assigned（任务计数 0→1）→ 同事务 mark_in_progress（幂等）
```
归属校验：目标段存在（`get_task_group`）且任务学生=照片学生；任务 `published|in_progress`；任务 assigned 计数 < 上限；消费锁定校验。

### 识别消费（M003 契约轮对接，v0.3.0）
- M003 经 `PhotoQueryService.get_for_recognition()` 取"任务内已 assigned（按学科作业段）"照片（本地路径直读）→ 识别 → `mark_consumed(photo_ids)` 置 `consumed_at`（**内容级识别**：布置单识别 + 作业照片逐题结构化，CR-002/ADR-010）
- `consumed_at` 置位后：删除 → 409 `photo_consumed`；改派 → 禁止
- suggestion 写入口归 M003 契约轮定稿（本模块默认注入 `MockSuggestionWriter` 测试桩：返回空建议或确定性建议；真实三方 Provider 按 ADR-011）

## 关键实现约束

- **同一数据库会话/事务**内完成状态变更与跨模块调用；`mark_in_progress` 失败 → 整体回滚
- 图片解码资源控制（尺寸/解压上限）；Pillow 版本钉死；`Image.MAX_IMAGE_PIXELS` 放宽点 + 显式上限（60MP）
- 所有查询强制双层过滤（family_id + student 主体仅本人）；文件路径仅进程内，不序列化给外部
- 审计：上传/质检被拒/归属/驳回/删除/受控取图入 audit（含 subject 类型与 id、request_id、时间）
- 时间一律 UTC；状态变更写 `updated_at`

## 与相邻模块边界（防御）

- M002 不得自行决定归属（仅状态机 + 兜底指令）；识别/建议逻辑进 M003
- M002 不读写 M001 的业务表（任务/题目/学生）——一律经 `task_client` 内部接口（Frozen + CR-001 扩展）
- M002 不执行评分/报告/评语（M004~M007）
