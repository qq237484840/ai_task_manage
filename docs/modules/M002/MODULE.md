# M002 模块总览 —— 作业图片采集与挂接

- **Module ID**：M002（对应需求原文 M02）
- **状态**：Developing（代码基线已按 **契约 v0.4.1** 实施完成）→ **契约 v0.4.0 Frozen（用户批准 2026-09-10）→ v0.4.1 Frozen（`CR-004` Applied：`API-M002-007` 响应体）**（`Task-005`/`CR-004` 交付并经 PM 复核 APPROVED；依据 `CR-003`/`ADR-013`/`ADR-014`；③ 实施 = **`Task-008`**，另 `Task-009` 前端「作业」域、`Task-010` 门控链路修复，与 Task-002 增量改接）
- **版本**：**v0.4.1（Frozen）**（v0.4.0 按 CR-003 修订：入口 `kind` + **N:N 挂接** + 窗口级门控 + 完成分析上收，取代 v0.3.0 的「段级 1:N 归属 + 完成程度外置」语义；v0.4.1 按 `CR-004` 修订 `API-M002-007` 响应体）
- **Domain**：作业评定 ｜ **Owner Agent**：AGENT-M002 ｜ **文档目录**：`docs/modules/M002/`
- **权威源**：`docs/requirements/CLARIFICATION-2026-09-10.md`（冲突时以其为准）、`REQ-002`、`ADR-013`、`ADR-014`、`CONFIGURATION.md`

## Purpose

V1 闭环第二环节（REQ-002 / **链路 H**）：学生（或家长代传）把作业照片（可一次性包含**多门学科、混合内容**，**无需预选任务/学科、不填任何内容**）上传，M002 负责把照片**拍好收好挂好认好**：

1. **图片采集与质检**：按"上传批次"组织；本地规则质检（模糊/过暗过亮/倾斜/遮挡/缺页，可解释 + 阈值配置化），不合格**不入库**并逐图报告原因引导重拍
2. **轻量归一**：EXIF 方向归一 + 统一 JPEG 编码 + 长边缩放
3. **先采后认 · N:N 挂接（ADR-013）**：照片入库 `unassigned` → 经 `app/core/ai/` 得**挂接建议**（目标 = **聚合学科子任务 `task_group_subjects` ★判定单元**）→ `suggested` → 家长（或学生本人）**逐张复核**（accept / reject / 改挂）→ `assigned`；**一张照片可跨学科挂接多条**；建议失败 → **手工挂接兜底**；首次确认挂接 → 经 M001 `mark_in_progress` 推进（幂等）
4. **窗口级门控 + 完成分析（B4/B5）**：某**归属窗口**下全部照片挂接确认后才可分析；对窗口内每个聚合学科子任务经 `app/core/ai/` 生成**完成情况草稿** → 家长确认 → 经 M001 `commit_conclusion` **回写判定单元**；未满足门控 → 提示「待复核 N 张」
5. **受控存储与可追溯**：原始图 + 归一图落本地受控目录（sha256 + 质量快照）；对外仅鉴权端点读取 + 访问审计；**未被消费的照片可撤销**（物理删除 + 审计）

## Responsibilities

- 上传批次创建与照片上传（两级主体鉴权；**入口 `kind`**：菜单「任务」→ `task_spec`、「作业」→ `homework`）
- 基础校验（类型/大小/像素）与本地规则质检、轻量归一、受控存储入库（单图单事务，失败不留痕）
- **N:N 挂接**：AI 挂接建议（异步）+ 逐张复核（accept/reject/改挂）+ **手工挂接兜底**；照片状态机 `unassigned→suggested→assigned/rejected`
- **窗口级门控**与**完成情况分析**（草稿生成 / 确认 / 重跑；聚合学科子任务级）
- 首次确认挂接（同事务）调 M001 `mark_in_progress`（幂等）；分析确认经 M001 `commit_conclusion` 回写
- 消费标记（`consumed_at`）与消费后不可变保障
- 经鉴权内容端点受控取图 + 访问审计；照片列表/待复核队列（供 UI 与兜底）

## Non-Responsibilities

- 不做 AI 模型内部实现（挂接建议/完成分析经 **`app/core/ai/`**（执行方 `AGENT-AI`/Task-006）；Provider 按 ADR-011：真实三方默认，Mock 测试桩/离线降级）
- 不做任务/聚合的创建与状态管理（M001 所有；M002 只消费状态约束与挂接目标校验）
- V1 质检不接外部 AI（本地规则先行；`QualityChecker` 协议保留 Vision 接入位）
- 不做评分（M005，V2）、评语（M006，V2）、报告（M007，V2）
- 不做逐题对齐/内容项级判定（V2）；不维护参考答案基准（端到端直判）
- 不做班级/学校/多租户与家长之外的角色（ADR-002/ADR-009）
- 视频/PDF/HEIC 原始上传不支持（浏览器端转码策略，非后端新增能力）
- 不提供免鉴权公开图片 URL / 静态目录直出
- 不做像素级矫正/增强/切边

## Dependencies

- **M001（内部服务接口 v0.2.0，ADR-013）**：`get_student` / `get_task` / `list_groups` / `get_group`（聚合 + 判定单元）/ `ensure_group` / `commit_conclusion` / `mark_in_progress`；归属窗口与聚合由 M001 计算
- **`app/core/ai/`（横切 LLM 接入层，AGENT-AI/Task-006）**：挂接建议 + 完成情况分析（进程内接口引用，不分配 API ID）
- **共享/基础设施**：认证/双主体上下文、日志/审计、异常与错误体、配置、数据库、图片存储抽象（shared/storage，M002 首次落地）

## Consumers

| 消费者 | 用途 | 消费方式 |
| --- | --- | --- |
| M001（反向回调） | 改归属日时迁移挂接目标（`PhotoLinkService.migrate_links`）；读取已确认挂接数（计数） | 内部服务接口 |
| （V2）M007 报告 | 读取已确认挂接照片证据集与挂接/批次信息（V1 不启用，ADR-014 决议 2） | 内部服务接口 |
| H5 UI（学生/家长端） | 上传/重拍引导/待复核队列（逐张复核）/门控提示/完成分析确认 | REST API（`MODULE_API.md`） |

## Owned Data

| 数据实体 | 说明 | 权威源 |
| --- | --- | --- |
| DATA-003 作业照片与批次 | `upload_batches`（上传批次，含 `kind`）+ `photos`（照片记录，含挂接状态机） | `MODULE_DATA.md` |
| DATA-016 作业照片挂接 | `photo_subject_links`（照片 ↔ 聚合学科子任务，**N:N**，含建议/确认态） | `MODULE_DATA.md` |
| DATA-017 完成情况分析 | `completion_analyses`（聚合学科子任务级结论，草稿/确认/重跑） | `MODULE_DATA.md` |

写入规则：上列数据唯一写入口 = M002；文件与行同事务（文件先写、失败清理）；其他模块只读消费，禁止直改。**M002 不得直写 M001 的 `task_group_subjects`**——结论经 `commit_conclusion` 回写。

## Exposed Services

- **REST API**（`/api/v1`）：既有 `API-M002-001~006`（其中 001/002/003/005 随 CR-003 修订）+ **新增 5 端点**（挂接建议查询 / 门控状态 / 完成分析生成·确认·重跑；**`API-M002-007~011`**）
- **内部服务接口**（进程内，供 M001/（V2）M007）：`PhotoQueryService`（列表/详情/门控/已确认挂接）、`PhotoLinkService.migrate_links`

## Forbidden Access

- 其他模块不得直写 M002 照片/挂接/分析表或绕过 M002 接口写图片文件
- 照片读取一律双层过滤（family 级 + student 主体仅本人）；表含冗余 `family_id` 防御纵深
- 禁止图片文件路径/未成年学生信息/答题内容入普通日志
- **M002 不得直写 M001 判定单元**（`task_group_subjects`）；只能经 `commit_conclusion`
