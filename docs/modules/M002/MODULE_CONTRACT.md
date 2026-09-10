# M002 模块契约（黑盒）—— 作业图片采集与挂接

- **Module ID**：M002 ｜ **版本**：**v0.4.1（Frozen）** ｜ **日期**：2026-09-10（v0.4.1 = `CR-004` Applied，仅 `API-M002-007` 响应体）
- **状态**：**契约 v0.4.0 —— Frozen（用户批准 2026-09-10）**（前版 v0.3.0 为 Frozen 基线，2026-09-08 用户批准）；本次按 `CR-003`（Approved）/`ADR-013`（Accepted）/`ADR-014`（Accepted）作**破坏性修订**，经 PM 复核 APPROVED 后由用户批准冻结
- **适用**：黑盒约定。内部实现见 `MODULE_DESIGN.md` 与 `MODULE_DATA.md`
- **权威源**：`docs/requirements/CLARIFICATION-2026-09-10.md`（冲突时以其为准）
- **v0.4.0 变更摘要（CR-003 §2.2 B1~B10）**：① 上传入口分「**任务**」/「**作业**」，`kind` 由入口决定且权威在 `upload_batches.kind`（B1/B2）；「作业」上传**不填任何内容**。② 归属由**段级 1:N** 放开为 **照片 ↔ 聚合学科子任务 N:N**（新增 `photo_subject_links`，DATA-016）（B3）。③ 新增 `completion_analyses`（DATA-017）+ **窗口级门控**（B4）。④ 挂接与复核链路契约化（异步建议 → 逐张复核 → 门控 → 完成分析 → 家长确认）（B5）。⑤ 降级兜底（`unassigned` + 手工挂接必须保留）（B6）。⑥ `photos.subject`/`group_no`/`suggestion_json` **Deprecated**；`task_id` 降为**窗口级归属**（B1）。⑦ 清理「M003/M004」前向引用（改链路 T / 链路 H + `app/core/ai/`，B7）。⑧ 新增端点 **API ID 已由 PM 分配 = `API-M002-007~011`**（B8，Draft）。⑨ 断言基线 112 → 扩展（B9）。

## Purpose

V1 闭环第二环节（REQ-002 / 链路 H）：学生（或家长代传）把作业照片上传（可含**多学科、混合内容**，**无需预选任务/学科、不填任何内容**），M002 负责把照片**拍好收好、挂好认好**：采集 + 质检 + 归一 + 受控存储 + **N:N 挂接建议与逐张复核** + **窗口级门控** + **完成情况分析（草稿→家长确认）**。

与 v0.3.0 差异：挂接目标由「登记单内学科作业段 `(task_id, subject, group_no)`」改为 **聚合学科子任务 `task_group_subjects`（★判定单元）** 的 N:N 关系；完成情况分析成为 M002 自身职责（原 M004 后置 V2，职责并入链路 H，`ADR-014` 决议 1）。

## Responsibilities / Non-Responsibilities

见 `MODULE.md`（本契约黑盒职责与其一致，不复制）。

## Inputs / Outputs

| 类型 | 说明 |
| --- | --- |
| Inputs | 上传批次创建指令（**含 `kind`**）；作业图片文件（multipart）+ 批次标识；**挂接建议触发**；逐张复核动作（accept / reject / 改挂）；完成分析确认/重跑指令；图片读取请求 |
| Outputs | 质检报告（逐检测项）；照片记录与受控内容地址（`unassigned`）；**N:N 挂接关系与状态**（建议/已确认/驳回）；**门控状态**（待复核 N / 可分析）；**完成分析草稿与确认结果**（聚合子任务级）；照片列表/待处理队列 |

## Exposed APIs

- REST：既有 `API-M002-001~006`（前缀 `/api/v1`，其中 001/002/003/005 随本变更**修订**；完整契约 `MODULE_API.md`）
- **新增端点（`API-M002-007~011`）**：挂接建议查询、逐张复核（accept/reject/改挂）、**门控状态查询**、完成分析（生成/确认/重跑）
- 内部服务接口（进程内，供 M007（V2）与 M001 反向回调）：`PhotoQueryService`（列表/取图/挂接关系/门控状态）、`PhotoLinkService.migrate_links`（改归属日时迁移挂接目标）
- **消费的 M001 内部接口**（v0.2.0）：`get_student` / `get_task` / `list_groups` / `get_group`（聚合 + 判定单元）/ `ensure_group` / `commit_conclusion` / `mark_in_progress`
- AI 能力经 **`app/core/ai/`**（横切，`AGENT-AI`/Task-006）调用；M002 不直接调用 Provider

## 主体与授权（ADR-009/ACR-001）

- 主体类型：`family`（家长：全家 + 兜底）；`student`（学生：仅本人）
- 上传/列表/挂接/复核/删除：student 主体强制本人（不接他人 `student_id`）；family 主体须显式带本家 `student_id`
- 跨家庭/跨主体越权一律对外 404；家庭级 `family_id` 过滤为底线

## 上传入口与批次（B1/B2）

- **入口决定 `kind`**：菜单「**任务**」→ `task_spec`（布置单，链路 T，由 M001 承载解析，照片仅作布置单来源）；菜单「**作业**」→ `homework`（链路 H，本模块主链路）。`upload_batches.kind` 为**权威**，`photos.kind` 冗余
- **上传批次** = 一次"拍照/选图上传会话"，仅作组织/审计单位，无状态机、不参与挂接判定；数量上限 `upload.max_photos_per_batch`（默认 50），超限 `422 batch_photo_limit`
- 批次内页序 `seq_no`：**服务端按接收顺序自增**，不接受前端页码
- **「作业」上传不填任何内容**（B2）：不选任务、不选学科、不填文本

## 照片状态与挂接（N:N，B3）

- 照片入库即 `unassigned`（已通过质检 + 归一）
- **挂接建议（异步）**：上传成功后**异步触发**挂接建议（幂等，仅处理未挂接照片）→ 经 `app/core/ai/` 得建议（目标 **聚合学科子任务** + 置信度）→ 写 `photo_subject_links`（`source=ai`、`confirmed_at` 空）→ 照片 `status=suggested`
- **逐张复核**（家长/学生本人）：
  - `accept` → 置该 link `confirmed_at`；可一次确认多条（照片跨学科）
  - `reject` → 置 `rejected_at`（保留审计）；照片仍可另挂
  - **改挂**（manual）→ 追加 `source=manual` link 并 `confirmed_at`
  - 照片存在 ≥1 条已确认 link → `status=assigned`；家长判无效 → `status=rejected`
- **手工挂接必须保留**（B6）：AI 建议失败/家长不采纳时，家长可手动选择聚合学科子任务完成挂接（唯一依赖 M001 `get_group`/`list_groups`）
- **数量上限**：单聚合子任务已确认挂接 ≤ `association.max_photos_per_subject`（默认 200）
- **不可用状态**：任务窗口 `draft`/`closed` 不可挂接（409 `task_not_acceptable`）
- **消费锁定**：完成分析确认后置 `photos.consumed_at`；已消费照片不可改派/删除

## 窗口级门控与分析（B4/B5）

- **门控**：某**归属窗口/聚合**下**全部照片挂接确认**后，才允许触发完成分析；未满足 → 提示「**待复核 N 张**」（`N` = 未确认挂接照片数）
- **完成分析**：对窗口内每个聚合学科子任务，经 `app/core/ai/` 生成**完成情况草稿**（`完成/部分完成/未完成/无法判断` + 依据照片 + 置信度）→ 写 `completion_analyses`（`status=draft`）→ 家长**确认**（`status=confirmed`）→ 经 M001 `commit_conclusion` **回写** `task_group_subjects.conclusion`/`conclusion_status`
- **重跑**：可重跑分析（`run_no` 递增）生成新草稿覆盖当前草稿
- 结论**粒度 = 聚合学科子任务级**（ADR-013；ADR-010 逐题判定作废，端到端直判/可观察依据/置信度/`无法判断` 出口/家长复核/不武断底线原则**继承**）

## 图片质检规格（保留 v0.3.0）

> 本地确定性规则逐项判定；逐检测项 `(passed, value, threshold, severity)`；任一 reject 级未过 → **不入库**、无文件/行/状态残留、`422 image_quality_rejected`（message 拼接逐项原因）。

| 检测项 id | 含义 | 默认规则（可配置） | 级别 |
| --- | --- | --- | --- |
| `format` | 文件类型硬校验 | 仅 `image/jpeg`、`image/png`、`image/webp` | 硬校验（415） |
| `size` | 文件大小 / 像素上限 | ≤10MB；解码像素 ≤60MP | 硬校验（413/422） |
| `blur` | 模糊 | 灰度拉普拉斯方差 ≥100 | reject |
| `too_dark` / `too_bright` | 过暗 / 过亮 | 灰度均值 ≥40 / ≤215 | reject |
| `tilt` | 倾斜 | 文本主轴倾斜角 ≤12°（启发式） | reject（可配降 warn） |
| `occlusion` | 遮挡 | 中心低纹理/亮度异常块占比（启发式） | reject（可配降 warn） |
| `page_crop` | 缺页/裁切 | 内容贴边/纸张边界不完整（启发式） | reject（可配降 warn） |

- 规则版本 `quality.ruleset_version = v1.0`；每张入库照片保存 `quality_report_json` 供追溯
- 启发式检测项**诚实声明**为"可解释 + 可配置"的近似信号，不得声称像素级精确；阈值全部登记 Configuration

## 图片预处理规格（保留）

通过质检的原图产出**归一图**（原图永不修改）：EXIF 方向归一 → RGB/白底合成 → 统一 JPEG（质量 88）→ 长边 >2000px 等比缩放。不做透视矫正/去阴影/增强/切边。

## Events

- V1 单体同步架构，不引入异步事件总线（与 M001 一致）；挂接建议为**进程内异步任务**（非消息队列），幂等可重试
- 上传通过/被拒、挂接建议/确认/驳回/改挂、门控达成、分析草稿/确认/重跑、`in_progress` 推进、受控取图、挂接迁移 均写审计

## Data Ownership

- DATA-003（`upload_batches`/`photos` + 本地图片目录）、**DATA-016**（`photo_subject_links`）、**DATA-017**（`completion_analyses`）Owner = **M002**；唯一写入口
- M001 只读消费（经 `group_subject_id` 引用）；**M002 不得直写 M001 的 `task_group_subjects`**——结论经 `commit_conclusion` 回写
- 删除语义：仅未消费照片（`consumed_at IS NULL`）可删；其余无删除路径
- 详见 `MODULE_DATA.md` / `DATA_MODEL.md`

## Configuration

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `batch.kind.enum` | `task_spec,homework` | 入口类型（由菜单决定） |
| `image.accept_mime` | `image/jpeg,image/png,image/webp` | 接受类型（415） |
| `image.max_size_mb` / `image.max_pixels` | `10` / `60_000_000` | 硬校验（413/422） |
| `quality.ruleset_version` | `v1.0` | 规则版本 |
| `quality.rules.*` | 见上表 | 质检阈值与 severity |
| `upload.max_photos_per_batch` | `50` | 批次上限（422） |
| `association.max_photos_per_subject` | `200` | 单聚合子任务已确认挂接上限（409） |
| `analysis.gate.enabled` | `true` | **窗口级门控**（全部挂接确认才可分析） |
| `normalized.max_side_px` / `.jpeg_quality` | `2000` / `88` | 归一图 |
| `image_store.root` | `<backend>/data/images` | 受控目录（ASM-010） |
| `pagination.default` | `page_size=20, max=100` | 列表分页 |

## Security

- 认证：Bearer → subject（family/student）注入（shared AuthContext）
- 授权：family 级 + student 仅本人（双层）；跨家庭/跨主体统一 404；`photos.family_id` 冗余防御
- 敏感数据（未成年人作业照片）：受控目录、不挂公开静态目录、鉴权端点 + 访问审计；文件/路径不入普通日志
- 上传防护：类型/大小/像素上限；解码资源控制（防解压炸弹/超大图）
- 不可变性：已消费照片不提供删除/改派；质检被拒不留痕；未消费允许撤销（审计）

## Performance

- V1 单家庭低并发（单机 SQLite + 本地目录）；单张处理预算 < 2s（解码+质检+归一，本地 CPU）
- 挂接建议为异步（不阻塞上传响应）；门控/列表为只读查询
- 图片目录按 `family_id/batch_id` 分层；受控取图支持 `Range`；归一图作预览默认
- 索引：见 `MODULE_DATA.md`（含 `photo_subject_links(photo_id, group_subject_id)` UNIQUE）

## Failure Behavior

| 场景 | 行为 |
| --- | --- |
| 参数/模型校验失败 | 400/422，`ErrorResponse{code,message,request_id}` |
| 未登录/会话过期 | 401 |
| 跨家庭/跨主体越权 | 403（对外统一 404） |
| 资源不存在 / 伪装不存在 | 404 |
| 任务状态不允许挂接（draft/closed） | 409 `task_not_acceptable` |
| 图片类型不支持 | 415 `unsupported_media_type` |
| 图片超限（大小/像素） | 413 / 422 |
| 图片未通过质检 | 422 `image_quality_rejected`（不入库） |
| 批次照片超上限 | 422 `batch_photo_limit` |
| 子任务挂接超上限 | 409 `subject_photo_limit` |
| **门控未达成** 触发分析 | 409 `gate_not_satisfied`（附「待复核 N 张」） |
| 并发冲突 | 409 `concurrent_conflict` |
| **AI 挂接建议失败/超时** | 照片保持 `unassigned` + 提示**手工挂接**（不阻断上传；降级 B6） |
| **AI 分析失败/返回不合规** | 无草稿或 `conclusion=无法判断` + 提示手工结论；不阻断 |
| 删除已消费照片 | 409 `photo_consumed` |
| 存储写入失败 | 500 + request_id；文件与记录一致回滚/清理 |
| 一致性 | 照片入库 + 首确认触发 `mark_in_progress` 各自同事务；分析确认与 `commit_conclusion` 同事务（跨模块编排） |

## Version / Compatibility

- **破坏性变更清单（v0.3.0 → v0.4.0）**：① 挂接目标由段级 `(task_id, subject, group_no)` → **N:N 聚合子任务**；② `photos.subject`/`group_no`/`suggestion_json` **Deprecated**；③ `photos.task_id` 降为窗口级；④ 新增 `upload_batches.kind`/`photos.kind`；⑤ 新增 `photo_subject_links`/`completion_analyses`；⑥ 完成情况分析**上收为 M002 职责**（原 M004，Deferred）；⑦ 新增门控/复核/分析端点
- **兼容性**：V1 无历史生产数据，开发库直接演进（`CHANGE-003` §5）；旧列保留（不写），旧表/旧端点语义变更以 CR 授权；Task-002 已交付的质检/归一/受控存储/双主体面**保持**，仅**归属段**增量改接（`ADR-014` 决议 5）
- 冻结后基线进入 `MODULE_CHANGELOG.md`；任何后续修改走 CR/ACR

## 签署区（批准记录）

| 角色 | 结论 | 日期 | 签名 |
| --- | --- | --- | --- |
| 用户（决策者） | **批准（Frozen）** | 2026-09-10 | 用户 |
| Project Master | **复核 APPROVED**（Task-005 交付物；API ID 分配登记、`DATA_MODEL` 字段级同步） | 2026-09-10 | Project Master |

> **v0.4.0 已于 2026-09-10 由用户批准并冻结（Frozen）**；② 契约修订评审（`CHANGE-003` ②，Task-005）关闭，③ 实施（`Task-008`）依据本定稿启动（Contract First 前置已满足）。v0.3.0 为 Frozen 基线（2026-09-08 用户批准）。
>
> **v0.4.1（`CR-004` Applied，2026-09-10，用户批准）**：`API-M002-007` 响应体以**运行实现为准**修订为 `{photo_id, status, suggestions:[LinkSuggestionItem]}`（非破坏性：不改 Method/Path/错误语义；前端零返工、后端零代码改动）。本版**不涉及**数据模型 / 分层设计 / 文件面 / 测试基线 —— 四者仍以 v0.4.0 描述为准。
