# M002 模块总览 —— 作业图片采集与归属

- **Module ID**：M002（对应需求原文 M02）
- **状态**：Developing（契约 **v0.3.0 Frozen**，2026-09-08 用户批准 → Task-002 已签发，AGENT-M002 编码中）
- **版本**：v0.3.0（契约基线 Frozen；v0.1.0 模型废弃，v0.2.0 为上一版草案，见 `MODULE_CHANGELOG.md`）
- **Domain**：作业评定 ｜ **Owner Agent**：AGENT-M002 ｜ **文档目录**：`docs/modules/M002/`
- **依据**：REQ-002；审查决策 PD-014/PD-015（先采后认/容器化）+ PD-016（ADR-009 两级主体）+ PD-017~024（内容级重构，ADR-010/011，v0.3.0）→ `docs/changes/CR-001.md`、`docs/changes/ACR-001.md`、`docs/changes/CR-002.md`、`docs/changes/ACR-002.md`
- **v0.3.0 变更注**：前置批准包四项全批（2026-09-08）→ M002 采集/质检/归一/归属职责保留不变；**"任务完成程度 = 学科作业段照片覆盖二值化"语义移除**——完成程度改由内容级判定链（M003 识别 + M004 逐题对齐判定）按 ADR-010 回写；M002 仅供给已 assigned 照片证据集与归属信息，不再输出二值化完成度

## Purpose

V1 闭环第二环节（REQ-002）：学生（或家长代传）把作业照片（可一次性包含**多门学科、混合内容**，无需预选任务/学科）上传上来，M002 负责把照片**拍好收好认好**：

1. **图片采集与质检**：按"上传批次（一次拍摄会话）"组织；本地规则质检（D1：模糊/过暗过亮/倾斜/遮挡/缺页，可解释 + 阈值配置化），不合格**不入库**并逐图报告原因引导重拍（REQ-008"不猜"衔接）
2. **轻量归一**（D2）：EXIF 方向归一 + 统一 JPEG 编码 + 长边缩放；复杂矫正/增强归 M003 识别前链路
3. **先采后认 · 照片归属**：照片先落库为 `unassigned`，不做学科/任务选择；AI（M003）给出归属建议（写 `suggestion_json`）→ `suggested`；高置信/家长（或学生本人）确认后 `assigned` 到 **登记单内学科作业段 `(task_id, subject, group_no)`**；无法认定 → `rejected` + 删除/重拍。首次 assigned → 经 M001 `mark_in_progress` 推进任务（幂等）
4. **受控存储与可追溯**：原始图 + 归一图落本地受控目录并登记（全链第一证据起点，sha256 + 质量快照）；对外仅鉴权端点读取 + 访问审计；**未被 M003 消费的照片可撤销**（物理删除 + 审计）

## Responsibilities

- 上传批次创建与照片上传（两级主体鉴权：student 主体仅本人、family 主体可代传任一本家学生）
- 基础校验（类型/大小/像素）与本地规则质检、轻量归一、受控存储入库（单图单事务，失败不留痕）
- 照片归属状态机（`unassigned→suggested→assigned/rejected`）与家长/学生兜底 API（assign/confirm_suggestion/reject/删除）
- 首次照片 assigned 到任务时（同事务）调 M001 `mark_in_progress`（幂等，published→in_progress）
- M003 识别消费标记（`consumed_at`）与消费后不可变保障
- 经鉴权内容端点受控取图 + 访问审计；图片列表/待处理队列（供 UI 与兜底）

## Non-Responsibilities

- 不做识别/OCR/结构化/归属建议判定（**归属建议由 M003 提供**，M002 只持有状态机与人工兜底；Provider 策略按 ADR-011：真实三方默认，Mock 为测试桩/离线降级）；不做内容级对错判定（M004，ADR-010）、不做任务匹配/评分/评语/报告（M004~M007）
- V1 质检不接外部 AI（本地规则先行；`QualityChecker` 协议保留 Vision 接入位）
- 不做任务/登记单的创建与状态管理（M001 所有；M002 只消费状态约束与归属目标校验）
- 不做班级/学校/多租户与家长之外的角色（ADR-002/ADR-009）
- 视频/PDF/HEIC 原始上传不支持（浏览器端转码策略 Task-002 明确，非后端新增能力）
- 不提供免鉴权公开图片 URL / 静态目录直出
- 不做像素级矫正/增强/切边（M003 识别前链路）

## Dependencies

- **M001（内部服务接口，Frozen v0.1.1 + CR-001 扩展）**：`get_student` / `get_task` / `get_task_group(task_id, subject, group_no)`（CR-001）/ `can_accept_photo`（任务状态 + 学生匹配 + 归属上限）/ `mark_in_progress`；任务题目冻结语义随 CR-001 调整为"存在 assigned 照片"起
- **M003（Planned，契约轮对接）**：归属建议写入 `suggestion_json`（照片 → 登记单内学科作业段 + 置信度）——进程内接口，M003 契约轮定稿；Provider 执行按 ADR-011（真实三方默认，Mock 测试桩/离线降级）
- **共享/基础设施**：认证/主体上下文（AuthContext 两级主体，ACR-001）、日志/审计、异常与错误体、配置、数据库、图片存储抽象（shared/storage，M002 首次落地，M003/M007 复用）

## Consumers

| 消费者 | 用途 | 消费方式 |
| --- | --- | --- |
| M003 AI 识别 | 按"任务内已 assigned 的学科作业段照片序列"读取原/归一图（本地路径 + 元数据）进入识别；识别后置 `consumed_at` | 内部服务 `PhotoQueryService` + 本地文件直读（同机） |
| M007 今日报告 | 按学生/任务/学科作业段读取已 assigned 照片证据集与归属/批次信息（供报告证据追溯；**完成程度不在此聚合，由内容级判定链 M003/M004 回写，v0.3.0**） | 内部服务接口 |
| H5 UI（学生/家长端） | 上传/重拍引导/待处理队列（归属确认）/照片列表与预览 | REST API（`MODULE_API.md`，API-M002-001~006） |

## Owned Data

| 数据实体 | 说明 | 权威源 |
| --- | --- | --- |
| DATA-003 作业照片与批次 | `upload_batches`（上传批次）+ `photos`（照片记录，含归属状态机） | `MODULE_DATA.md` |

写入规则：DATA-003 唯一写入口 = M002；文件与行同事务（文件先写、失败清理）；其他模块只读消费/经内部接口写 suggestion（M003）与 mark_consumed，禁止直改。

## Exposed Services

- **REST API**（`/api/v1`，API-M002-001~006）：创建上传批次 / 上传照片 / 照片列表 / 受控取图 / 归属操作（associate）/ 撤销（DELETE）
- **内部服务接口**（进程内，供 M003/M007）：`PhotoQueryService`（列表/取图/识别消费/标记 consumed）

## Forbidden Access

- 其他模块不得直写 M002 照片表或绕过 M002 接口写图片文件
- 照片读取一律双层过滤（family 级 + student 主体仅本人）；表含冗余 `family_id` 防御纵深
- 禁止图片文件路径/未成年学生信息/答题内容入普通日志；suggestion 中 AI 原文仅存 `suggestion_json`
