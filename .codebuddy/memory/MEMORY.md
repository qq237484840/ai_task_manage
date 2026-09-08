# MEMORY —— 长期项目记忆

> 就地更新说明：2026-09-08（执行批 2）：**M002 契约草案 v0.3.0 用户批准 → Frozen**（MODULE.md Developing；CONTRACT/API/DATA Frozen；Task-002 签发，AGENT-M002 Active）→ **顶层同步 v0.10.0** → **CHANGE-001 立项**（合并 CR-001/CR-002/ACR-001/ACR-002 的 M001 变更执行，AGENT-M001 Task-CHG，Executing）——下一开发段=CHANGE-001 编码（group_no 数据面 + 学生子账号认证面 + reference_answer 非基准 + 测试回归 + M001 九件套回填）→ Task-002（M002 v0.3.0 实现）→ ROADMAP M-A 验收。前情（同日前两条）：批准包四项批准+ADR-010/011 Accepted → M002 v0.3.0 起草。

> 就地更新说明：2026-09-08（执行批 3，后续将批 2 覆盖）：**CHANGE-001 编码+测试+M001 九件套回填完成**（AGENT-M001）——CR-001 容器化数据面、ACR-001 两级主体认证面（student_accounts/双型会话/AuthContext/命名空间隔离爆破）、CR-002/ACR-002 语义面（reference_answer 非基准）；测试 **54→89 全绿**；新增 ACR-001 端点（子账号管理/学生 login/logout/me）代码已交付、**API ID 待 PM 收口分配**；文档按实况回填（九件套/DATA_MODEL/REQ-001/API·MODULE REGISTRY 状态注）——**当前待办=PM 复核 CHANGE-001（DoD 勾选/收口 v0.1.2/状态推进）→ Task-002（M002 v0.3.0 实现）→ ROADMAP M-A 验收**。前情：执行批 2（M002 v0.3.0 Frozen/顶层 v0.10.0/CHANGE-001 立项）。

## 项目概览
- 仓库：`c:\DevProject\AI.TaskManage`，git 分支 main。
- **业务（V1，2026-09-08 由用户提供）**：中小学生 AI 作业与学习成长综合评定系统 —— V1 MVP =「AI 每日作业智能评定系统」，闭环：创建任务→上传照片→AI识别→任务匹配→质量评价→AI教师评价→今日报告。仅 M001~M007 七模块（需求原文 M01~M07），禁止知识图谱/画像/组卷/班级管理/多租户等（ADR-002）。
- **已确认技术决策（用户 2026-09-08 答复，全部落库）**：技术栈=移动优先 H5 + FastAPI + SQLite 单体（ADR-004）；身份=纯家庭模式，家庭账号家长=布置者+学生档案=评定对象、家庭级数据隔离（ADR-005），扩展为**两级主体**（ADR-009：家长+学生子账号）；正确度判定=**内容级主客观全判 + 端到端直判，不维护参考答案字段**（ADR-006 **Superseded→ADR-010**，PD-021/022）；AI Provider=抽象 + **真实三方默认，Mock 降级测试桩/离线**（ADR-007 **Superseded→ADR-011**，PD-019/需求⑤）；部署=需联网访问三方 API + SQLite + 本地图片目录（ASM-010，2026-09-08 修订）；学科=小学语数英书面作业起步、无法判断→标记+家长复核/重拍（ASM-011）；匹配/评判=**内容级**（布置精确到题，逐题对齐判完成/对错，PD-018）；M005=六维保留但 **AI 评判为核**（PD-023）；报告=**草稿→家长复核定稿归档**（PD-024）。
- **学校基础资料（2026-09-08，M001 开发输入）**：学校字典=全局共享只读（seed 预置、后台维护暂缓），学生档案 `school_id` 必填关联，字段=名称+学段（ADR-008/REQ-009/DATA-011）；ADR-005 家庭隔离的唯一限定例外，学校管理域仍禁止。
- **M002 作业图片采集决策（2026-09-08，D1~D4 = PD-010~013，用户确认推荐项）**：① 质量检测=**本地规则先行**（模糊/过暗/过亮/倾斜/遮挡/缺页启发式可解释判定、阈值配置化、规则版本 v1.0，无外部 AI；`QualityChecker` 协议预留 Vision 接入位）；② 预处理=**仅轻量归一**（EXIF 方向归一 + 统一 JPEG 编码 + 长边 ≤2000px；透视矫正/增强归 M003 识别前链路）；③ 提交建模=懒创建/自动归属 open 提交 + 显式 complete，**任务首张质检通过入库即触发 mark_in_progress**（published→in_progress，幂等，可继续上传至 close）；④ 不合格=**不入库 + 逐图报告**（失败不留文件/行/状态；422 `image_quality_rejected` 引导重拍）。
- **M002 完整性审查重构决策（2026-09-08，PD-014~016 + D5~D8，用户逐项确认；M002 契约 v0.1.0→v0.2.0）**：① **任务粒度**：task=多学科作业登记单容器（subject 语义放宽待 CR-001）+ `task_items.group_no` 学科作业段，学科卡=`(subject,group_no)`，照片最终单归属到作业段；② **先采后认**：上传按批次不预选任务/学科→`unassigned`→AI(M003)建议`suggested`→家长/学生确认`assigned`/`rejected`；首次 assigned 触发任务 `mark_in_progress`（幂等，取代 D3 旧触发）；完成程度=作业段照片覆盖二值化；③ **两级主体**：家庭账号家长（全家+兜底）+学生子账号（完整登录、仅本人；学生自主登记/拍照、家长兜底）→ ADR-009/ACR-001；④ **补全 D5~D8**：批次≤50/任务 assigned≤200；页序服务端自增；未消费(`consumed_at IS NULL`)照片可撤销（物理删+审计）；`(family_id,batch_id)` 串行化+409。
- **主线功能域重排（2026-09-08，v0.9.0，PD-020/g4）**：主线计划与验收里程碑按 **4 功能域**组织（新建 `docs/ROADMAP.md` v0.9.0），**保留 M001~M007 模块组织与契约治理、开发顺序 M001→M007 不变**：A 学生自主采集闭环（布置登记拍照识别草稿→确认补正→生效；完成作业拍照，PD-017/g1）→ B 家长复核确认闭环（照片归属确认/纠错）→ C 大模型内容级匹配+家长兜底（逐题对齐判完成/对错，主客观全判，低置信/无法判断入复核）→ D 综合评判+每日报告定稿（草稿→复核定稿→归档）。里程碑 M-A~M-D + M-END 全链路回归。
- **变更/风险登记（2026-09-08）**：`CR-001`/`ACR-001`/`CR-002`/`ACR-002` 均 **Approved** 并**合并为 `docs/changes/CHANGE-001.md`（Executing，AGENT-M001）**；ADR-010/011 → **Accepted**（ADR-006/007 Superseded 正式生效）；**M002 契约 v0.3.0 Frozen（2026-09-08 用户批准，Task-002/AGENT-M002 Active）**；`RISK_REGISTER` RISK-006~007 + RISK-008（三方依赖）、RISK-009（照片出域合规）。
- 采用「文档驱动 + 总控 Agent 治理 + 模块 Agent 实现」多 Agent 工程模式。用户提供的 #0~#107 方法论已落实为 docs/ 体系。
- 状态 **v0.10.0（CHANGE-001 编码/回填完成，待 PM 复核收口）**：Phase 3 功能域主线 + 内容级重构 —— **M001 Stable + CHANGE-001（CR-001/CR-002/ACR-001/ACR-002）执行完成待复核（89 测试全绿，见批 3）**；**M002 Developing（契约 v0.3.0 Frozen，2026-09-08 批准，Task-002/AGENT-M002 Active，等待 CHANGE-001 收口后签发）**；主线计划=`ROADMAP.md`。REQ-001~009 Approved；PD-001~024 全部确认；跨模块开放项 O-1~O-9 见 PROJECT_STATUS。

## 用户偏好与决策（稳定事实）
- 文档语言：**中文为主**，代码/API 标识符英文。
- 文档体系分层渐进：模块九件套在模块划分时按真实模块生成，**勿建空模板文件**。
- 源码目录自 Task-001 起落地：`backend/`（含 `.venv`，Python 3.12）+ `frontend/` + `backend/tests/`；后端改动需同步回填 docs 与测试。
- ID 治理规范先行（ID_GOVERNANCE.md）；ID（M/API/REQ/ADR/CR/ACR/CHANGE/BUG/TD/RISK/ASM/AGENT）**仅由 Project Master 分配**，Agent 不得自行编号。
- 单条需求详情入 `docs/requirements/REQ-xxx.md`，需变更登记先 CR/ACR；普通增量改动记 `CHANGELOG.md`。
- README 只做入口，业务知识一律入 docs 分层，禁止知识重复/Single Source of Truth。
- 确认交互形式：一次 ask_followup 多问（≤4 题），选项带推荐标注，用户逐项答复后落库。
- **用户偏好复用**：后续项目均采用本治理模式。治理模板包位于仓库内 `ai-governance-template/`（v1.0.0，含 INSTALL.md；占位符 {{PROJECT_NAME}}/{{PROJECT_DIR}}/{{INIT_DATE}}）。新项目铺装=复制 docs/ + 按 INSTALL 替换占位符 + 确认默认假设。模板为复用资产，治理规范改进须回同步模板并递增版本。

## 关键索引
- 知识地图入口：`docs/INDEX.md`
- 状态：`docs/PROJECT_STATUS.md`（**v0.9.0** / Phase 3 功能域主线+内容级重构 / PD-001~024）；**主线计划：`docs/ROADMAP.md`（v0.9.0，功能域 A~D 里程碑）**；假设：`docs/ASSUMPTIONS.md`（ASM-001~011）；决策：`docs/adr/ADR-001~011.md`（ADR-006/007 **Superseded**，ADR-010/011 Proposed）
- 需求：`docs/REQUIREMENTS.md` + `docs/requirements/REQ-001~009.md`（Approved，REQ-001~007 随 CR-002 精校预告）；模块：`docs/MODULE_REGISTRY.md`（M001 **Stable**，M002 Designing/Draft v0.2.0，M003~M007 Planned）；API：`docs/API_REGISTRY.md`（API-M001-001~012 **Frozen**，API-M002-001~006 **Draft**，改须 CR）；数据：`docs/DATA_MODEL.md`（DATA-001~011，DATA-001 判定基准语义随 CR-002）；Agent：`docs/AGENT_REGISTRY.md`（AGENT-M001 Active/Task-001 APPROVED，AGENT-M002 待 Task-002 签发）；风险：`docs/RISK_REGISTER.md`（RISK-001~009）；变更：`docs/changes/`（CR-001/002、ACR-001/002 均 Open）
- 当前阶段：Phase 3 —— **M001 Stable + CHANGE-001 编码/回填完成待 PM 复核**：工程与 **89** 测试细节见 `docs/modules/M001/`（student_accounts/student_auth 等新文件已登记）；**M002（作业图片采集与归属）契约 v0.3.0 Frozen 落库 `docs/modules/M002/`**：先采后认归属保留 + 完成程度改由内容级判定链回写（R4~R6），API-M002-001~006（Frozen）；图片存 `<backend>/data/images` 分层、鉴权读取+访问审计；**主线按功能域重排见 `docs/ROADMAP.md`**；**待办（下一开发段）**：PM 复核 CHANGE-001（DoD 勾选/API ID 收口/顶层状态推进/M001 行定稿 v0.1.2，任务单 `docs/changes/CHANGE-001.md` §执行进度）→ Task-002（AGENT-M002 实现 M002 v0.3.0，M001 段级查询 get_task_group/can_accept_photo 已就绪）→ 按 ROADMAP M-A~M-D 验收推进 → 全系统回归（真实三方+Mock 双跑）。细节见 `docs/modules/M002/MODULE_*.md`、`docs/changes/CHANGE-001.md`、`docs/ROADMAP.md` 与 `.codebuddy/memory/2026-09-08.md`。
- 治理模板包：`ai-governance-template/`（README v1.0.0 / INSTALL.md）。
