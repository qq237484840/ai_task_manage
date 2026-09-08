# M002 模块契约（黑盒）—— 作业图片采集与归属

- **Module ID**：M002 ｜ **版本**：v0.3.0（契约基线，Frozen） ｜ **日期**：2026-09-08
- **状态**：Frozen —— 契约基线已由用户批准（签署区，2026-09-08）；任何修改走 CR/ACR（`ID_GOVERNANCE.md`）
- **适用**：黑盒约定。内部实现见 `MODULE_DESIGN.md` 与 `MODULE_DATA.md`
- **范围依据**：REQ-002（作业图片采集与质量检测）；v0.1.0 模型（任务直绑 + submission open/complete）**废弃**；v0.2.0"先采后认 + 归属状态机"继承；**v0.3.0 移除"完成程度=覆盖二值化"，完成程度改由内容级判定链（M003/M004，ADR-010）回写**（决策 R1~R6，见 `MODULE_SUMMARY.md`）

## Purpose

把"学生一天各科作业照片的拍摄/上传 → 质检把关 → 轻量归一 → 受控存储 → **归属到登记单内具体学科作业** → 供识别消费"做成契约化闭环。与 v0.1.0 的关键差异：**上传不需要预选任务与学科**；照片归属由 AI 建议 + 家长/学生兜底完成；任务 `in_progress` 的触发点移到"首次照片 assigned"。

## Responsibilities / Non-Responsibilities

见 `MODULE.md`（本契约黑盒职责与其一致，不复制）。

## Inputs / Outputs

| 类型 | 说明 |
| --- | --- |
| Inputs | 上传批次创建指令；作业图片文件（multipart）+ 批次标识；AI（M003）归属建议写入；归属/驳回/撤销指令；图片读取请求 |
| Outputs | 质检报告（逐检测项）；照片记录与受控内容地址（unassigned）；归属状态（assigned/rejected + 归属三元组）；任务最新状态（含首次 assigned → in_progress 推进结果）；照片列表/待处理队列 |

## Exposed APIs

- REST：`API-M002-001~006`（前缀 `/api/v1`；完整契约 `MODULE_API.md`；登记 `API_REGISTRY.md`，Draft）
- 内部服务接口（进程内，供 M003/M007）：`PhotoQueryService`（含识别消费 `mark_consumed`）
- M003 写归属建议（内部接口，M003 契约轮定稿）→ 落 `photos.suggestion_json`
- 消费的 M001 内部接口（Frozen + CR-001）：`get_student` / `get_task` / `get_task_group(task_id, subject, group_no)` / `can_accept_photo` / `mark_in_progress`

## 主体与授权（ADR-009/ACR-001）

- 主体类型：`family`（家长：全家 + 兜底）；`student`（学生：仅本人）
- 上传/列表/归属/删除：student 主体强制本人（不接他人 student_id）；family 主体须显式带本家 student_id
- 跨家庭/跨主体越权一律对外 404（既有语义）；家庭级 `family_id` 过滤为底线

## 上传批次（Batch）语义

- **上传批次** = 一次"拍照/选图上传会话"（学生本人发起，或家长代传）。仅作组织/审计单位，无状态机、不参与归属判定
- 数量上限：单批次 ≤ `upload.max_photos_per_batch`（默认 50），追加超限 → `422 batch_photo_limit`
- 批次内页序 `seq_no`：**服务端按接收顺序自增**（D6），不接受前端页码

## 照片归属（先采后认，PD-015）

- 照片入库即 `unassigned`（已通过质检+归一）
- AI（M003）识别后给出**建议**（目标 `(task_id, subject, group_no)` + 置信度等）→ 状态 `suggested`，快照存 `suggestion_json`
- 兜底确认（家长或学生本人）：
  - `assign`（直接指定三元组）或 `confirm_suggestion`（采纳建议）→ **`assigned`**：归属生效；该校验目标任务存在且绑定同一学生、任务状态 `published|in_progress`、任务已 assigned 照片数 < `association.max_photos_per_task`（默认 200）
  - `reject` → **`rejected`**：判定无效（照片不可用于识别/报告），可随后删除或重新上传
- **`mark_in_progress` 触发**（D3 新语义）：某任务 assigned 照片数由 0→1（归属事务内调 M001 `mark_in_progress`，published→in_progress，幂等）；删除已 assigned 照片**不回退**任务状态
- **不可用状态**：任务 `draft`/`closed` 不可 associate（409 `task_not_acceptable`）；任务 `closed` 后不再接受新归属
- **消费锁定**：M003 识别完成后置 `consumed_at`；已消费照片不可再改派/删除（识别与评分依据锁定）
- **撤销（D7）**：`consumed_at IS NULL` 的照片（unassigned/suggested/rejected/未消费的 assigned）均可删除（物理删文件 + 行 + 审计）——覆盖传错图、含敏感废图的即时清理

## 图片质检规格（D1/D4 保留）

> 本地确定性规则逐项判定；逐检测项 `(passed, value, threshold, severity)`；任一 reject 级未过 → **不入库**、无文件/行/状态残留、`422 image_quality_rejected`（message 拼接逐项原因，前端逐条提示重拍）。

| 检测项 id | 含义 | 默认规则（可配置） | 级别 |
| --- | --- | --- | --- |
| `format` | 文件类型硬校验 | 仅 `image/jpeg`、`image/png`、`image/webp` | 硬校验（415） |
| `size` | 文件大小 / 像素上限 | ≤10MB；解码像素 ≤60MP | 硬校验（413/422） |
| `blur` | 模糊 | 灰度拉普拉斯方差 ≥100（低于判模糊） | reject |
| `too_dark` | 过暗 | 灰度均值 ≥40 | reject |
| `too_bright` | 过亮 | 灰度均值 ≤215 | reject |
| `tilt` | 倾斜 | 文本内容主轴倾斜角 ≤12°（启发式） | reject（可配降 warn） |
| `occlusion` | 遮挡 | 中心大范围低纹理/亮度异常块占比检测（启发式） | reject（可配降 warn） |
| `page_crop` | 缺页/页角裁切 | 内容贴边/纸张边界不完整近似检测（启发式） | reject（可配降 warn） |

- 规则版本 `quality.ruleset_version = v1.0`；每条入库照片保存 `quality_report_json` 供追溯
- 启发式检测项诚实声明为"可解释 + 可配置"的近似信号；不得声称像素级精确
- 硬校验与阈值全部登记于 Configuration，实现不得硬编码散落

## 图片预处理规格（D2 保留）

通过质检的原图按以下管线产出**归一图**（原图永不修改/覆盖）：
1. EXIF 方向归一（`ImageOps.exif_transpose`）→ 2. RGB/白底合成 → 3. 统一编码 JPEG（质量 88，可配置）→ 4. 长边 >2000px 等比缩放
产出：`original`（原样）+ `normalized`（归一图，M003 识别输入与 H5 预览默认）。不执行透视矫正/去阴影/增强/切边。

## Events

- V1 单体同步架构，不引入异步事件总线（与 M001 一致）
- 上传通过/被拒、归属（assigned/rejected/删除）、任务 in_progress 推进、受控取图均写审计（audit）；suggestion 写入亦审计

## Data Ownership

- DATA-003（`upload_batches`/`photos` + 本地图片目录）Owner = **M002**；唯一写入口；M003（suggestion/mark_consumed）与 M007 只读消费
- 文件与记录同生命周期（文件先写、行失败清理）；删除语义：仅未消费照片（D7），其余无删除路径
- 详见 `MODULE_DATA.md` / `DATA_MODEL.md`

## Configuration

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `image.accept_mime` | `image/jpeg,image/png,image/webp` | 接受类型（其余 415） |
| `image.max_size_mb` | `10` | 单图大小上限（413） |
| `image.max_pixels` | `60_000_000` | 解码像素上限（422） |
| `quality.ruleset_version` | `v1.0` | 规则版本（写入照片记录） |
| `quality.rules.blur.laplacian_min` | `100` | 模糊阈值（reject） |
| `quality.rules.luma.min` / `.max` | `40` / `215` | 过暗/过亮阈值 |
| `quality.rules.tilt.max_deg` | `12` | 倾斜上限；severity 可配 |
| `quality.rules.occlusion.enabled` / `.severity` | `true` / `reject` | 遮挡启发式 |
| `quality.rules.page_crop.enabled` / `.severity` | `true` / `reject` | 缺页启发式 |
| `upload.max_photos_per_batch` | `50` | 单上传批次上限（D5，422） |
| `association.max_photos_per_task` | `200` | 单任务已 assigned 照片上限（D5，409） |
| `normalized.max_side_px` | `2000` | 归一图长边上限 |
| `normalized.jpeg_quality` | `88` | 归一图 JPEG 质量 |
| `image_store.root` | `<backend>/data/images` | 本地受控图片目录（ASM-010） |
| `pagination.default` | `page_size=20, max=100` | 列表分页（与 M001 一致） |

## Security

- 认证：Bearer token → **subject（family/student）** 注入（shared AuthContext 扩展，ACR-001）
- 授权：family 级过滤 + student 主体仅本人（双层）；跨家庭/跨主体统一 404；`photos.family_id` 冗余防御
- 敏感数据（未成年人作业照片）：受控目录、不挂公开静态目录、鉴权端点读取 + 访问审计；文件/路径不入普通日志
- 上传防护：类型/大小/像素上限、解码资源控制（防解压炸弹/超大图）
- 不可变性：已消费照片（`consumed_at` 置位）不提供删除/改派；质检被拒照片不留文件/行/状态；未消费照片允许撤销（审计记录）

## Performance

- V1 单家庭低并发（单机 SQLite + 本地目录）；单张处理预算 < 2s（解码+质检+归一，本地 CPU）
- 图片目录按 `family_id/batch_id` 分层，避免单目录文件堆积
- 受控取图支持静态 `Range`；归一图作为预览默认
- 索引：`upload_batches(family_id, student_id, created_at)`；`photos(batch_id, seq_no)` UNIQUE、`photos(family_id, status, created_at)`、`photos(family_id, task_id)`（归属过滤/计数）、`photos(student_id, created_at)`

## Failure Behavior

| 场景 | 行为 |
| --- | --- |
| 参数/模型校验失败 | 400/422，`ErrorResponse{code,message,request_id}` |
| 未登录/会话过期 | 401 |
| 跨家庭/跨主体越权 | 403（对外统一 404，不泄露存在性） |
| 资源不存在 / 伪装不存在 | 404 |
| 任务状态不允许归属（draft/closed） | 409 `task_not_acceptable`（附当前状态） |
| 学生不属于该任务/家庭 | 403/404（对外 404） |
| 图片类型不支持 | 415 `unsupported_media_type` |
| 图片超限（大小/像素） | 413 / 422 |
| 图片未通过质检 | 422 `image_quality_rejected`（不入库、状态不变） |
| 批次照片超上限 | 422 `batch_photo_limit` |
| 任务 assigned 超上限 | 409 `task_photo_limit` |
| 并发冲突（同批次上传/归属争用） | 409 `concurrent_conflict`（前端重试） |
| 删除已消费照片 | 409 `photo_consumed` |
| 存储写入失败 | 500 + 完整请求日志（含 request_id）；文件与记录一致回滚/清理 |
| 一致性 | 照片入库 + 归属/首触发 `mark_in_progress` 各自在同一事务；失败整体回滚 |

## Version / Compatibility

- v0.1.0（2026-09-08）：任务直绑 + submission(open/complete) 模型 —— **废弃**（Draft 未 Frozen，直接改版；模型差异见 `MODULE_CHANGELOG.md`）
- v0.2.0（2026-09-08）：先采后认重构 + 两级主体 + 归属到学科作业段；依赖 `CR-001`/`ACR-001`（均已批准）；完成程度=覆盖二值化（**v0.3.0 移除**）
- v0.3.0（2026-09-08，**Frozen 基线**）：在 v0.2.0 基础上随 `CR-002`/`ACR-002`（已批准，ADR-010/011 Accepted）升级——采集/质检/归一/归属不变；**完成程度以内容级判定为准**（M002 只供证据与归属，判定结果归 DATA-004/005）；AI 执行真实三方默认 + Mock 降级
- 冻结后基线进入 `MODULE_CHANGELOG.md`；任何后续修改走 CR/ACR

## 签署区（批准记录）

| 角色 | 结论 | 日期 | 签名 |
| --- | --- | --- | --- |
| 用户（决策者） | **批准**（v0.3.0 草案） | 2026-09-08 | 用户 |
| Project Master | **批准**（Frozen 基线确认） | 2026-09-08 | PM（总控） |

> 冻结：前置 `CR-001`/`ACR-001`/`CR-002`/`ACR-002`（均 2026-09-08 批准）已全部通过；用户 2026-09-08 批准本 v0.3.0 → **Frozen**，Task-002 已签发（AGENT-M002 Active），进入编码。
