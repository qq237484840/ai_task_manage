# CHANGELOG —— 项目变更历史

> 维护：Project Master。语义化版本（主.次.修订）。
> 模块级变更进入各模块 `MODULE_CHANGELOG.md`；重大变更（CHANGE-nnn）另存 `docs/changes/`。

## v0.12.0 —— 2026-09-08

### 前端技术栈切换立项（ADR-012 / CHANGE-002 / Task-003）

- **用户技术方案变更**：前端采用 Vue3 生态 → PM 可行性评估（REST 契约零影响、M001 前端规模小（app.js 431 行/6 视图）、Task-002 前端 UI 未实现 = 唯一零浪费窗口、FastAPI 静态挂载点与框架解耦）→ 三决策点逐项确认：**Q1 组件库 = Vant 4 纯移动库**（用户原点名 Element Plus，PM 提示桌面密度与 ADR-004「移动优先」冲突后改选）/ **Q2 = TypeScript**（DTO 契约对齐）/ **Q3 = 独立前置任务 + Task-002 后段接轨**
- **ADR-012 Accepted（PD-025）**：Vue3 + Vite + TypeScript + Vant 4 + Vue Router(hash) + Pinia + axios 错误语义映射（400/401/403/404/409/413/415/422）；`frontend/src` 工程化，FastAPI 托管构建产物 `dist/`（单进程形态/ASM-010 不变）；零构建三文件退役；工作量基线 3.5~5.5 人日（含 TS +0.5~1 缓冲）
- **CHANGE-002 立项（Executing）+ Task-003 签发（AGENT-M001，任务书 `docs/agents/Task-003.md`）**：Vue 工程搭建 + M001 6 视图功能等价迁移 + 托管切换 + 退役清理 + 冒烟/pytest 89 回归 + M001 DESIGN/FILES/SUMMARY 与 ARCHITECTURE 回填；`frontend/**` 任务期 AGENT-M001 独占写权
- **Task-002 接轨注**：M002 前端基础 UI 段后移——Task-003 验收后按新栈（Vue 组件）实现；AGENT-M002 后端编码并行不受阻
- 同步：`PROJECT_STATUS.md` → **v0.12.0**（PD-025、O-6 关闭、下一步行动）、`AGENT_REGISTRY.md`（AGENT-M001 Task-003 Active）、`ROADMAP.md`（前端统一栈注）、`INDEX.md`
- 下一步：Task-003（前端切换）与 Task-002 后端并行执行 → Task-002 前端段新栈接轨 → M002 模块级 DoD 复核 → M-A 随 M003 全量验收

## v0.11.0 —— 2026-09-08

### CHANGE-001 完成（M001 定稿 v0.1.2）+ Task-002 正式签发（M002 编码启动）

- **CHANGE-001 PM 复核 APPROVED → Applied（AGENT-M001 完成）**：`CR-001`（任务=多学科作业登记单容器 + 学科作业段 `task_items.group_no`）/`ACR-001`（两级主体：`student_accounts` 学生子账号 + family/student 双型会话 + 命名空间隔离防爆破 + student 仅本人越权 404）/`CR-002`+`ACR-002`（`reference_answer`=非判定基准辅助字段，端到端直判 ADR-010）——代码落地 + 测试 54→**89 全绿** + M001 九件套回填定稿 + DATA_MODEL/REQ-001/Registry 同步
- **API-M001-013~017 收口登记（Active）**：开通/更新学生子账号、学生登录/登出/主体信息（ACR-001 新增端点，API ID 由 Project Master 分配）
- **M001 契约定稿 v0.1.2**（Stable + 维护态）：MODULE.md/CONTRACT/API/DATA/DESIGN/FILES/SUMMARY/TEST/CHANGELOG 状态头与 API 编号同步
- **Task-002 正式签发（AGENT-M002 → Active 编码中，任务书 `docs/agents/Task-002.md`）**：实现 M002 v0.3.0（backend `modules/m002` + 图片质检/归一/受控存储 + 先采后认归属 + tests + 回填九件套）；M001 依赖侧已就绪（`get_task_group`/`can_accept_photo`/双主体认证/`mark_in_progress`）
- 同步：`PROJECT_STATUS.md` → **v0.11.0**、`MODULE_REGISTRY.md`（M001 v0.1.2、M002 Task-002 编码中）、`API_REGISTRY.md`（API-M001-013~017 新增）、`AGENT_REGISTRY.md`（AGENT-M001 维护态、AGENT-M002 Task-002）、`ROADMAP.md`（采集链当前主线）
- 下一步：M002 编码（Task-002）→ ROADMAP M-A 里程碑 PM 验收（学生自主采集闭环）

## v0.10.0 —— 2026-09-08

### M002 契约批准冻结 + Task-002 签发 + M001 变更执行启动

- **M002 契约草案 v0.3.0 用户批准（签署区）→ Frozen**：先采后认归属保留；完成程度以内容级判定为准（M002 收敛为采集/质检/归一/归属/证据供给）；九件套状态头与 MODULE_CHANGELOG +批准冻结行
- **Task-002 签发（AGENT-M002 → Active）**：实现 M002 v0.3.0（backend `modules/m002` + tests + 回填九件套），依赖 M001 CHANGE 落地后联调
- **M001 合并 CHANGE 执行启动（AGENT-M001，Task-CHG）**：`CR-001`（登记单容器化 + `task_items.group_no`，reference_answer 降为非基准辅助字段）/`ACR-001`（两级主体：学生子账号 + 认证）/`CR-002` + `ACR-002`（内容级判定链数据面与 Provider 配置，ADR-010/011 口径）——代码落地 + 54 测试回归 + 新用例 + 回填 M001 契约
- 同步：`PROJECT_STATUS.md` → **v0.10.0**（M002 Developing、M001 变更执行中、下一步行动更新）、`MODULE_REGISTRY.md`（M002 Developing/Frozen v0.3.0、M001 变更执行中）、`API_REGISTRY.md`（API-M002-001~006 Draft → **Frozen**）、`AGENT_REGISTRY.md`（AGENT-M002 Active、AGENT-M001 Task-CHG）、`INDEX.md`
- 下一步：M001 合并 CHANGE 完成 → 回填 M001 九件套 → M002 编码（Task-002）→ ROADMAP M-A 里程碑验收（学生自主采集闭环）

## v0.9.0 —— 2026-09-08

### 主线重排 + 内容级判定重构（用户 grill 定稿 g1~g4 + 内容级四问 q2-1~q2-4，共 8 项决策 PD-017~024）

- **主线按功能域重排（PD-020/g4 → `ROADMAP.md` v0.9.0）**：保留 M001~M007 模块组织与契约治理、开发顺序不变；**主线计划与验收里程碑 = 4 功能域** A 学生自主采集闭环 → B 家长复核确认闭环 → C 大模型内容级匹配+家长兜底 → D 综合评判+每日报告定稿；每条对应用户核心需求逐条可演示验收（里程碑 M-A~M-D + M-END 回归）；横切能力=真实三方 AI/MVC/两级主体/学校字典
- **布置登记录入拍照识别为主（PD-017/g1）**：拍黑板/记事本/布置页 → 大模型识别"今日作业清单（学科+条目）"草稿 → 学生/家长确认补正后生效为登记单；**M003 增加"布置单识别"AI 环节**
- **内容级匹配与评判（PD-018/g2 + PD-021/q2-1 + PD-022/q2-2 → ADR-010）**：布置精确到题；匹配=照片内容↔布置题逐题对齐判完成/对错；**主客观全判**；判定基准=**模型端到端直接判（不维护参考答案字段）**，输出可观察依据+置信度，低置信/无法判断入家长复核；ADR-006（分科混合/参考答案对照）→ **Superseded**，ADR-003 不武断底线保留
- **真实三方 AI 为默认运行（PD-019/g3/需求⑤ → ADR-011）**：Provider 抽象保留，OCR/Vision/LLM 真实三方为默认实现，Mock 降级测试桩/离线降级（`mock-*` 标注）；ASM-010 修订=部署需联网前提；ADR-007 → **Superseded**；RISK-008（三方依赖）、RISK-009（照片出域合规）新增
- **M005 六维保留但 AI 评判为核（PD-023/q2-3）**：逐题完成/对错 + 大模型综合评判（六维质量+综合分）基于识别/匹配证据出具，权重仍配置化
- **报告草稿→家长复核定稿（PD-024/q2-4）**：大模型生草稿 → 家长复核（低置信/无法判断/对错异议逐项过）→ 确认定稿归档（保留草稿与复核记录）

### 更新 / 变更登记

- 新增：`docs/ROADMAP.md`（v0.9.0 功能域主线）、`docs/changes/CR-002.md`（内容级判定链数据面）、`docs/changes/ACR-002.md`（判定与 Provider 架构重构）、`docs/adr/ADR-010.md`（内容级主客观全判，取代 ADR-006）、`docs/adr/ADR-011.md`（真实三方默认，取代 ADR-007）——CR-002/ACR-002 均 **Open 待批准**，ADR-010/011 **Proposed**（同日已批准，见下方"批准包"）
- `ADR-006.md`/`ADR-007.md` → 状态 Superseded（附取代说明）；`ASSUMPTIONS.md`（ASM-008/010/011 修订，ASM-010 联网前提）；`RISK_REGISTER.md`（RISK-002~004/006 口径升级 + RISK-008/009）
- `DATA_MODEL.md`（DATA-001 判定基准语义 + DATA-004/005/006 内容级口径 + v0.9.0 变更预告）；`MODULE_REGISTRY.md`（M001~M007 行口径 + 状态注）
- `SYSTEM_SUMMARY.md` / `ARCHITECTURE.md`：关键技术决策/接入策略/部署架构/外部系统段加 v0.9.0 变更注记（ADR-006/007 Superseded、真实三方默认、联网前提、出域合规）
- `PROJECT_STATUS.md` → **v0.9.0**：阶段更新、PD-017~024 登记、开放项 O-1~O-4 精校 + O-9 新增、下一步行动更新
- `INDEX.md`（+ROADMAP/ADR-010/011 登记，状态同步）；`MODULE_REGISTRY.md` 状态注 v0.9.0

### 批准包（2026-09-08 用户审阅批准，四项全部批准）

- `CR-001`（登记单容器化 + `group_no` 学科作业段）→ **Approved**：批准附带条件落实——条款冲突按 ADR-010 定稿口径修订（`reference_answer` 保留为**非基准**辅助字段、"逐题对照能力"措辞作废）、组号默认语义实施时收敛回填
- `ACR-001`（两级主体认证）→ **Approved**：按验收标准纳入 M001 变更执行（54 测试回归 + 双主体越权矩阵 + family 向后兼容）
- `CR-002`（内容级判定链数据面）→ **Approved**：批准后立即起草 **M002 契约草案 v0.3.x**（下一批准点）
- `ACR-002`（判定 + Provider 架构重构）→ **Approved**：ADR-010/011 生效（**Accepted**，ADR-006/007 → Superseded 正式生效）；ADR-010 §Decision 评分消费引用勘误（依 q2-3/CR-002 语义）
- 同步：`PROJECT_STATUS.md`/`MODULE_REGISTRY.md`/`INDEX.md`/`REQUIREMENTS.md`/`AGENT_REGISTRY.md` 状态 → Approved/Accepted；开放项 O-8/O-9 转入执行前状态
- 下一步：**M002 契约草案 v0.3.x 起草 → 用户批准 → M001 合并 CHANGE 执行**（CR-001/CR-002/ACR-001/ACR-002）

## v0.8.0 —— 2026-09-08

### 变更 / 决策（M002 契约完整性审查 → 两项架构重构 + 采集补全）

- **重构一（任务语义，PD-014 → `CR-001` Open）**：task = **多学科作业登记单容器**；`task_items` 保留题目级并新增 `group_no`（学科作业段，同科多份可区隔）；学科卡 = `(subject, group_no)` 聚合；客观题参考答案逐题对照能力（ADR-006）保留；任务创建主体扩展（家长/学生本人）
- **重构二（采集与归属，PD-015 → M002 v0.2.0）**：**先采后认** —— 上传按"上传批次"不预选任务/学科；照片入库 `unassigned` → AI（M003）建议 `suggested` → 家长/学生确认 `assigned`（归属到登记单内学科作业段）或 `rejected`；首次 assigned 触发任务 `mark_in_progress`（幂等，取代 v0.1.0 D3"首张入库即触发"）；完成程度 = 学科作业段照片覆盖二值化（不猜原则）
- **重构三（身份主体，PD-016 → `ADR-009` Accepted + `ACR-001` Open）**：两级主体 = 家庭账号（家长：全家 + 兜底）+ **学生子账号**（可登录、仅本人）；学生自主登记/拍照、家长兜底；ADR-005 语义扩展（家庭级隔离不变）
- **采集补全（D5~D8）**：D5 数量上限（单批次 ≤50 / 单任务 assigned ≤200，配置化）；D6 页序服务端自增（前端不传页码）；D7 未消费（`consumed_at IS NULL`）照片可撤销（物理删 + 审计），已消费不可变；D8 服务层按 `(family_id, batch_id)` 串行化 + `409 concurrent_conflict`
- 数据：DATA-003 重构 = `upload_batches` + `photos`（归属状态机 + 归属三元组 + suggestion/quality 快照）；M001 冻结面受影响（CR-001/ACR-001 批准后执行变更）

### 更新

- 新增：`docs/adr/ADR-009.md`（Accepted）、`docs/changes/CR-001.md`、`docs/changes/ACR-001.md`（Open）；`RISK_REGISTER.md`（+RISK-006/007）
- `docs/modules/M002/` 九件套 **v0.1.0 → v0.2.0 全量重构**（总览/摘要/契约/API/数据/设计/测试/文件/变更日志；API-M002-001~006）
- `API_REGISTRY.md`（M002 v0.2.0 六接口）、`MODULE_REGISTRY.md`（M002 v0.2.0 + M001 变更预告）、`PROJECT_STATUS.md`（→ v0.8.0，+PD-014~016 与跨模块开放项）、`REQUIREMENTS.md` + REQ-001/002/003 精校、`ADR-005.md`（+ADR-009 扩展注）
- 说明：`INDEX.md`/`DATA_MODEL.md` 的字段级同步随 CR-001/ACR-001 批准后统一执行（避免二次漂移）

## v0.7.1 —— 2026-09-08

### 变更 / 决策

- **M002 四关键决策确认（用户采纳推荐项，PD-010~013）**：
  - D1/PD-010 质量检测策略 = **本地规则先行**（可解释启发式 + 阈值配置化 + 规则版本化，无外部 AI；`QualityChecker` 协议预留 Vision 接入位）
  - D2/PD-011 预处理边界 = **仅轻量归一**（EXIF 归一 + 统一 JPEG + 长边上限缩放；矫正/增强归 M003）
  - D3/PD-012 提交建模与状态触发 = **单图通过即触发**（懒创建/自动归属 open 提交 + 显式 complete；任务首张入库即 `mark_in_progress`，可继续上传至 close）
  - D4/PD-013 不合格处理 = **不入库 + 逐图报告**（失败不留文件/行/状态；`422 image_quality_rejected` 引导重拍）
- **M002 九件套契约草案 v0.1.0（Draft）产出**（`docs/modules/M002/`）：契约/API/数据/设计/文件/测试六件细化 + 总览/摘要/变更日志；API-M002-001~004（上传/提交列表/结束本组/受控取图）登记 **Draft**；DATA-003 字段级细化（submissions/submission_images + 图片存储布局）；**待用户批准（签署区）→ Frozen → 签发 Task-002**

### 更新

- 新增：`docs/modules/M002/`（九件套草案 v0.1.0）
- `MODULE_REGISTRY.md`（M002 Designing/Draft v0.1.0）、`API_REGISTRY.md`（+API-M002-001~004 Draft）、`AGENT_REGISTRY.md`、`PROJECT_STATUS.md`（→ v0.7.1，+PD-010~013）、`INDEX.md`、`MODULE_CHANGELOG.md`（M002 +v0.1.0 行）

## v0.7.0 —— 2026-09-08

### 变更 / 决策

- **M001 DoD 验收通过（用户：验收通过）**：PM 按 `AGENT_GUIDE.md` §6 对 Task-001 交付物逐项验收 → **APPROVED**；M001 Testing → **Stable**（契约 v0.1.1 Frozen 保持不变，API-M001-001~012 全程未越契约）
- 进入 **M002（作业图片采集）契约设计**（M002 → Designing）：关键决策点待用户确认，九件套草案 v0.1.0（Draft）产出后提交批准

### 更新

- `docs/modules/M001/` 九件套状态 → Stable（MODULE.md / MODULE_SUMMARY.md）
- `MODULE_REGISTRY.md`（M001 Stable、M002 Designing）、`AGENT_REGISTRY.md`（AGENT-M001 Task-001 APPROVED；AGENT-001 转入 M002 契约治理）、`PROJECT_STATUS.md`（→ v0.7.0）
- `INDEX.md`（状态同步，修复 v0.4.1~v0.6.0 期间的索引漂移）、`MODULE_CHANGELOG.md`（+验收行）

## v0.6.0 —— 2026-09-08

### 变更 / 决策

- **Task-001 完成（AGENT-M001）**：M001 全量实现落地，契约 v0.1.1（Frozen）无越契约实现
  - backend：FastAPI + SQLAlchemy 2.0 + SQLite 单体（`backend/app/`）；家庭认证（scrypt + 会话哈希 + 登录爆破退避）、学生档案、任务+题目集事务、任务状态机唯一出口、schools 只读字典（seed 幂等 + DB FK 双保险）；统一 ErrorResponse/request_id 贯穿/审计日志脱敏
  - frontend：移动优先 H5 零构建实现（`frontend/index.html` + `styles.css` + `app.js`），FastAPI 静态托管（**模块内实现决策**：本机无 Node 构建链，Vue3+Vite 为可替换壳；决策已记 `MODULE_DESIGN.md`）
  - tests：**54 项全部通过**（unit/API/集成/安全，覆盖 MODULE_TEST 清单与 DoD）
- M001 模块状态 Developing → Testing（待 PM DoD 验收）；API-M001-001~012 保持 Frozen（实现未触发契约变更，无需 CR）

### 更新

- `docs/modules/M001/` 九件套回填实现版（`MODULE_FILES.md`/`MODULE_TEST.md`/`MODULE_DESIGN.md` 状态与内容）；`MODULE_REGISTRY.md`、`AGENT_REGISTRY.md`、`PROJECT_STATUS.md`（→ v0.6.0）；新增 `.gitignore`、`backend/requirements.txt`

## v0.5.0 —— 2026-09-08

### 变更 / 决策

- **用户批准 M001 契约草案 v0.1.1**（签署区 `docs/modules/M001/MODULE_CONTRACT.md`）→ Contract/API/Data 基线 **Frozen**；M001 模块状态 Designing → Developing；API-M001-001~012 状态 Draft → Frozen（修改须走 CR）
- 向 **AGENT-M001** 签发 **Task-001**（实现 M001：backend/frontend 工程骨架 + 功能实现 + 测试 + 回填九件套实现版）→ Active；AGENT-M002~007 保持 Planned（前序验收后按序签发）

### 更新

- `docs/modules/M001/` 九件套状态/签署区同步（Frozen / Developing）；`MODULE_REGISTRY.md`、`API_REGISTRY.md`、`AGENT_REGISTRY.md`、`PROJECT_STATUS.md`（→ v0.5.0）

## v0.4.1 —— 2026-09-08

### 变更 / 决策

- M001 开发输入增补**学校基础资料**（用户确认四项：全局共享字典 + 数据库 seed 预置 + 后台维护暂缓；学生档案必填关联；字段 = 名称+学段；消费限 M001）→ 新增 **REQ-009**（Approved）、**ADR-008**（Accepted）、**DATA-011**（`schools` 全局只读字典）
- M001 契约草案 v0.1.0 → **v0.1.1**：`students.school` 自由文本 → `school_id` 必填（FK→schools）；新增 API-M001-012（GET /schools 只读列表）；schools 初始化 seed 幂等，运行期无维护 API

### 更新

- 新增：`docs/adr/ADR-008.md`、`docs/requirements/REQ-009.md`
- `docs/modules/M001/` 九件套同步 v0.1.1；`DATA_MODEL.md`（DATA-011 + ownership 例外）；`REQUIREMENTS.md`（REQ-009 登记、REQ 状态列修正 Draft→Approved）；`MODULE_REGISTRY.md`、`API_REGISTRY.md`（API-M001-012）
- `PROJECT_STATUS.md` → v0.4.1（PD-009 登记）；`PROJECT.md` / `ADR-005.md` 措辞澄清：学校管理域禁止不变，"学校基础字典"（ADR-008）为限定例外

## v0.4.0 —— 2026-09-08

### 决策

- PD-007/008 经用户复核确认：**ASM-010/011 → Confirmed**（单机/局域网 + SQLite + 本地图片目录；小学语数英书面作业起步 + "无法判断"→ 标记 + 家长复核/重拍）
- **REQ-001~008 → Approved**：V1 需求基线冻结
- 进入 **Phase 2 模块契约设计**：M001（作业任务管理）九件套契约草案产出

### 更新

- `PROJECT_STATUS.md` → v0.4.0（PD 表全部 Confirmed；M001 → Designing）；`ASSUMPTIONS.md`（ASM-010/011 Confirmed）；`MODULE_REGISTRY.md`（M001 Designing）；`REQUIREMENTS.md` + REQ-001~008（Approved）
- 新增：`docs/modules/M001/`（模块文档九件套，契约草案）

## v0.3.0 —— 2026-09-08

### 决策

- 用户确认关键设计决策（PD）并落库 ADR：
  - PD-003 → **ADR-004**：移动优先 H5 + Python FastAPI + SQLite 单体
  - PD-004 → **ADR-005**：纯家庭模式身份模型（家庭账号 + 学生档案，家庭级数据隔离）
  - PD-005 → **ADR-006**：正确度分科混合判定（客观题对照参考答案 / 主观题不判对错并注明）
  - PD-006 → **ADR-007**：AI Provider 抽象 + Mock 先行（本地无 key 跑通全链路）
- 新增默认假设 **ASM-010**（PD-007：单机部署 + SQLite + 本地图片目录）、**ASM-011**（PD-008：小学语数英书面作业起步、无法判断→标记+复核/重拍），状态 Open 待用户复核

### 更新

- `ARCHITECTURE.md` / `SYSTEM_SUMMARY.md`：技术架构、部署、数据、身份、业务流用语按 ADR-004~007 同步
- `DATA_MODEL.md`：存储选型定为 SQLite + 本地图片目录；DATA-002 收敛为家庭账号 + 学生档案（Owner M001）
- `ASSUMPTIONS.md`：ASM-007/008 转 Confirmed，新增 ASM-010/011
- `PROJECT_STATUS.md`：PD-003~006 → Confirmed；版本推进至 v0.3.0

## v0.2.0 —— 2026-09-08

### 新增

- 纳入 V1 MVP 需求（用户「V1 MVP 总控 Agent 指令」，AI 每日作业智能评定系统）：
  - `docs/REQUIREMENTS.md` 登记 REQ-001~008（Draft）；新增 `docs/requirements/REQ-001~008.md` 需求单
  - `docs/MODULE_REGISTRY.md` 登记 M001~M007（需求 M01~M07 别名映射）
  - `docs/AGENT_REGISTRY.md` 登记 AGENT-M001~M007
  - `docs/DATA_MODEL.md` 登记 DATA-001~010 核心实体草案
  - `docs/API_REGISTRY.md` 状态更新（契约阶段逐模块登记）
  - `docs/RISK_REGISTER.md` 创建（RISK-001~004）
  - `docs/PROJECT.md` / `docs/SYSTEM_SUMMARY.md` / `docs/ARCHITECTURE.md` 由骨架填充为 V1 内容

### 决策

- ADR-002：V1 范围控制（仅 7 模块闭环，禁止提前开发未来功能）
- ADR-003：AI 评价边界与原则（可观察行为/配置化权重/分级重写/允许"无法判断"）
- 模块 ID 映射：需求 `M01~M07` ↔ 正式 `M001~M007`
- 待决决策 PD-003~008 等用户确认（见 `PROJECT_STATUS.md`）

## v0.1.0 —— 2026-09-08

### 新增

- 建立文档治理骨架（文档驱动 + 总控 Agent 多 Agent 协作模式），并沉淀治理模板包 `ai-governance-template/`
