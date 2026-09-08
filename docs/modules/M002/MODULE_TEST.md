# M002 模块测试计划（DoD 依据）—— 作业图片采集与归属

- **状态**：已批准基线（契约 **v0.3.0 Frozen**，2026-09-08）｜ 数量与命名以 Task-002 实测为准，DoD 验收时核对
- **目录**：`backend/tests/`（M001 先例）；测试随代码落地（红→绿）
- **说明**：以下为**验收口径清单**（映射到黑盒契约各段落），合成图以确定性像素构造（白底黑字/灰块/运动模糊/低亮度等），**不依赖真实拍照**

## 一、质检（D1/D4）—— API-M002-002 拒绝路径

1. 类型：非 jpeg/png/webp → 415；超 10MB → 413；解码像素 >60MP → 422
2. 模糊图（低于阈值）→ 422 `image_quality_rejected`，message 含逐项原因
3. 过暗 / 过亮 / 倾斜超限 / 遮挡 / 页角裁切 → 各自 422，报告含 `checks[]`（value/threshold/severity）
4. 被拒后：**无文件残留、无 `photos` 行、任务状态不变**（断言 DB + 图片目录）
5. 通过图：quality_report_json 含 `ruleset_version=v1.0` 与全部 checks；可通过配置调节阈值后再判定（阈值配置化断言）

## 二、归一与存储（D2）

6. EXIF 方向测试图 → 归一图方向正确；输出恒 JPEG；长边 >2000 → 等比缩至 ≤2000；原始文件未被修改（sha256 不变）
7. original/normalized 相对路径落 `family/batch/` 分层；行内 sha256 = 原始内容哈希

## 三、上传/批次（D5/D6/D8）

8. student 主体上传他人 batch → 404；family 主体可代传本家学生
9. seq_no 服务端自增（并发上传不重复，UNIQUE 约束 + 串行化断言）
10. 批次达 50 张后再传 → 422 `batch_photo_limit`
11. 并发上传同批次 → 无重复 seq/行，极端争用可现 409 `concurrent_conflict`（幂等重试语义）

## 四、归属状态机（R2 + D3/D5/D7）

12. 上传即 `unassigned`；Mock 写入建议 → `suggested`（suggestion_json 快照正确）
13. `confirm_suggestion` → assigned；`assign`（直接三元组）→ assigned；`reject` → rejected（不可再识别）
14. 首次 assigned（任务 0→1）→ 任务 `published→in_progress`（**恰好一次**，重复 assign 幂等不重复推进）
15. 目标任务不存在 / 学生不符 / 任务 `draft|closed` → 409 `task_not_acceptable`/404；归属段不存在 → 404/422
16. 任务已 assigned ≥200 → 409 `task_photo_limit`
17. 已 assigned 照片删除（未消费）→ 成功但不回退任务状态
18. `mark_consumed` 置 `consumed_at` 后：删除 → 409 `photo_consumed`；改派 → 禁止

## 五、受控读取与审计（Security）

19. 家长可见全家照片；学生仅本人（URL 传他人 student_id/photo_id → 404）；跨家庭 404
20. content 端点返回 correct kind（normalized 恒 JPEG / original 原 mime），支持 Range；记录访问审计
21. 删除未消费照片物理删除文件 + 行 + 审计记录

## 六、回归与越权矩阵（ACR-001 配套）

22. 双主体越权矩阵：family/student × 自身/他人/他家庭 的 list/get/associate/delete/content 全绿
23. 会话无 family_id（student 主体）查询强制本人；审计含 subject_type/id
24. 全量回归：随 M001 54 测试 + M002 新增用例同跑

## 七、性能与健壮性

25. 单张处理预算 < 2s（解码+质检+归一，本地 CPU，合成 60MP 极端用例单独标注）
26. 存储失败 → 500 无残留（文件与行一致性）；异常日志含 request_id
