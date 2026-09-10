# M002 测试策略与结果 —— 作业图片采集与挂接

- **状态**：**v0.4.0（Frozen，用户批准 2026-09-10）** —— 既有实况基线 = **112 passed**（Task-002，2026-09-09：M002 单测 11 + API 12，含 M001 89）；本文件新增**用例设计**（③ 实施阶段落地 = `Task-008`，`CHANGE-003` §2.2 B9）
- **目录**：`backend/tests/`；测试随代码落地（红→绿）
- **说明**：**验收口径清单**（映射黑盒契约各段落）；合成图以确定性像素构造，**不依赖真实拍照**；AI 依赖（挂接建议/完成分析）经 **`MockAiClient`** 注入（ADR-011 降级桩）

## 测试分层与"为何需要/为何不需要"

| 层 | 覆盖 | 为何需要 | 为何不需要其他 |
| --- | --- | --- | --- |
| 单元 | 质检规则（模糊/明暗/倾斜/遮挡/裁切）、归一管线、门控计算（待复核 N）、挂接状态机守卫、分析状态机（draft/confirmed/run_no） | 确定性规则 + 状态机是正确性核心 | — |
| 集成 | Repository 双层过滤、挂接 N:N 唯一约束、分析与 `commit_conclusion` 事务、`migrate_links` 回调、失败无残留 | 跨模块一致性/事务边界 | — |
| API | 既有 001~006（修订后）+ 新增 5 端点契约断言 | 契约冻结防漂移 | — |
| 安全 | 未认证 401；跨家庭/跨主体越权 404；**双主体矩阵** | RISK-004 未成年人照片；两级主体验收 | — |
| 性能 | 单张处理预算断言（<2s） | 本地 CPU 确定性 | 不做并发压测（单家庭低并发 ASM-010） |
| E2E | 手工冒烟（拍照→复核→门控→分析→确认） | 真实可操作性 | 自动化浏览器测试价值/成本比低 |

## 既有基线（v0.3.0 实况，112 passed）

- [x] `tests/unit/test_m002_image_processing.py`（11）：质检各检测项、归一、失败无残留
- [x] `tests/api/test_m002_api.py`（12）：上传/归属状态机、in_progress 单次触发、越权矩阵、消费后不可变
- [x] 与 M001 89 用例合并运行全绿（`112 tests`）

## 新增用例设计（v0.4.0，B9；③ 实施阶段落地）

### U 单元
- [ ] **门控计算**：窗口内 K 张照片、M 张未确认挂接 → `pending_photos=M`、`satisfied=(M==0)`
- [ ] **挂接状态机守卫**：accept 未确认 link / reject 已确认 link / relink 目标非法 → 相应 4xx
- [ ] **分析状态机**：`draft → confirmed`；`confirmed` 后重跑 → 409；`run_no` 递增
- [ ] **`kind` 一致性**：批次 `kind=task_spec` 时 `photos.kind` 冗余一致（不一致 → 缺陷）

### I 集成
- [ ] **N:N 唯一约束**：同照片同子任务重复挂接 → UNIQUE 幂等；跨学科多条挂接允许
- [ ] **首确认触发**：照片首条 `confirmed_at` 使窗口任务计数 0→1 → `mark_in_progress` **恰好一次**（幂等）
- [ ] **分析确认事务**：`completion_analyses.status=confirmed` 与 M001 `commit_conclusion` 同事务；`commit_conclusion` 失败 → 整体回滚
- [ ] **消费锁定**：分析确认 → 相关照片 `consumed_at` 置位 → 删除 409 `photo_consumed`
- [ ] **`migrate_links` 回调**：M001 改归属日 → 挂接目标迁移成功；失败 → 整体回滚
- [ ] **AI 降级**：`MockAiClient` 返回超时/不合规 → 挂接建议缺失（照片留 `unassigned`）+ 手工挂接可用；分析草稿 `无法判断` 不阻断

### A API
- [ ] 新增 5 端点契约断言（挂接建议查询/门控/生成/确认/重跑，含门控未达成 409 `gate_not_satisfied`）
- [ ] 既有 001/002/003/005 修订后断言（`kind` 字段、`links` 替代 `assignment`/`suggestion`、复核动作 accept/reject/relink）

### 保留用例（不变）
- [ ] 质检 D1/D4、归一 D2、批次/页序/上限 D5~D8、受控读取与审计、双主体越权矩阵

## 执行摘要（模板）

```text
$ .venv/Scripts/python.exe -m pytest
112 passed   # v0.3.0 实况（③ 实施完成后应 ≥ 112 + 新增用例数）
```

## 手工冒烟清单（真服务，验收口径）

```text
启动：cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
1. 菜单「作业」上传多张照片（不填任何内容）→ 质检通过入库 unassigned
2. 待复核队列：查看挂接建议 → 逐张 accept/reject/改挂（含手工挂接兜底）
3. 门控：全部挂接确认 → 门控 satisfied；未确认 → 提示「待复核 N 张」
4. 完成分析：生成草稿 → 家长确认 → 判定单元回写 + 照片消费锁定
5. 观察日志：request_id 贯穿；上传/复核/门控/分析/审计记录；无路径/敏感文本明文
```
