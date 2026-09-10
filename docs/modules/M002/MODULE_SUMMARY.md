# M002 模块摘要 —— 作业图片采集与挂接（30 秒速览）

- **状态**：Developing（代码基线已按契约 v0.4.1 实施完成：`Task-008` 后端 + `Task-009` 前端 + `Task-010` 门控修复，均经 PM 复核 APPROVED）＋ **契约 v0.4.1 —— Frozen（用户批准 2026-09-10；v0.4.1 = `CR-004` Applied）**（按 `CR-003`/`ADR-013`/`ADR-014`）
- **入口文档**：`MODULE.md`（总览）→ `MODULE_CONTRACT.md`（黑盒契约）→ `MODULE_API.md` → `MODULE_DATA.md`
- **前版**：v0.3.0 Frozen（2026-09-08 用户批准）—— 其"段级 1:N 归属 `(task_id, subject, group_no)` + 完成程度外置 M003/M004"语义**已作废**

| 维度 | 摘要 |
| --- | --- |
| Purpose | V1 链路 H：作业照片**采集 → 质检 → 归一 → 受控存储 → N:N 挂接（建议+逐张复核）→ 窗口级门控 → 完成分析（草稿→家长确认）** |
| Key Decisions | **ADR-013 双层模型**（挂接目标 = **聚合学科子任务 `task_group_subjects` ★判定单元**，N:N）；**ADR-014**（V1 = M001+M002+`app/core/ai/`；**M003/M004 职责并入链路 H**，ID 保留 Deferred；M005~M007 后置 V2）；ADR-011 AI Provider 默认真实三方/Mock 降级；ADR-009/ACR-001 双主体 |
| Inputs | 上传批次指令（含 **`kind`**）；图片文件（multipart）；挂接建议触发；逐张复核（accept/reject/改挂）；完成分析生成/确认/重跑 |
| Outputs | 质检报告；照片记录（`unassigned`）；**N:N 挂接关系**（建议/确认/驳回）；**门控状态**（待复核 N）；**完成分析草稿/确认**（聚合子任务级 → 回写 M001） |
| Dependencies | M001（窗口/聚合/判定单元/回写接口）+ **`app/core/ai/`**（挂接建议/完成分析） |
| APIs | 既有 `API-M002-001~006`（001/002/003/005 修订）+ **新增 5 端点**（挂接建议查询 / 门控状态 / 完成分析生成·确认·重跑，**`API-M002-007~011`**）+ 内部 `PhotoQueryService`/`PhotoLinkService` |
| Data | **Own**：DATA-003（`upload_batches` 含 `kind` + `photos`）、**DATA-016**（`photo_subject_links`，N:N）、**DATA-017**（`completion_analyses`） |
| 核心规则 | 入口决定 `kind`（权威在 `upload_batches.kind`）；上传不填任何内容；`unassigned→suggested→assigned/rejected`；**一张照片可跨学科挂接多条**；**手工挂接必须保留**；**窗口级门控**（全部挂接确认才可分析）；分析确认 → `commit_conclusion` 回写 + `consumed_at` 锁定；质检被拒不留痕；已消费不可变 |
| Main Risks | 门控与消费锁定的一致性；AI 建议/分析降级（手工兜底必须可用）；大规模照片展示性能（RISK 见 `CHANGE-003` §5）；未成年人作业照片高敏（RISK-004） |
| Status | 契约 **v0.4.1 —— Frozen（用户批准 2026-09-10；v0.4.1 = `CR-004` Applied）**（变更记录见 `MODULE_CHANGELOG.md`） |

## 进入本模块前建议阅读

1. `CLARIFICATION-2026-09-10.md` §2.C/D（照片 / 判定 / 挂接）——**权威源**
2. `ADR-013`（双层模型 + 配置锁定 + 判定落聚合层）+ `ADR-014`（M003/M004 并入、执行方收窄）
3. `REQ-002`（已精校）+ `REQ-003`/`REQ-007`（照片 / 挂接文案）
4. `CONFIGURATION.md`（门控 / 上限 / 质检阈值）
5. `DATA_MODEL.md`（DATA-003/016/017）
