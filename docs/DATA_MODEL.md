# DATA_MODEL —— 数据级知识（L5）

> 权威源：本文是「核心数据模型与数据所有权」的权威来源。模块私有数据可仅存在于 `MODULE_DATA.md`；核心跨模块数据必须登记于此。
>
> 状态：**V1 实体层已登记，存储选型已定**（2026-09-08）。存储 = SQLite 单文件 + 本地图片目录（ADR-004；PD-007 默认见 `ASSUMPTIONS.md` ASM-010）；字段级设计待各模块数据设计阶段细化（含主键/索引/约束/迁移方案）。
> **变更执行（v0.10.0，2026-09-08）**：内容级判定重构（ADR-010/PD-018~024）与两级主体（ADR-009）经 CR-001/CR-002/ACR-001/ACR-002 **Approved** 并随 CHANGE-001 在 M001 侧落地：DATA-001 题目保留可选字段但**不再作为判定基准**（端到端直判 ADR-010）；DATA-001/002 字段级已同步（学科作业段 `(subject,group_no)`、`student_accounts` 子账号、双型会话；权威源 `docs/modules/M001/MODULE_DATA.md`）；DATA-004/005/006 承载逐题对齐判定与"大模型综合评判（草稿→家长复核定稿）"结果；真实三方默认（ADR-011）出域面登记于 DATA-009/RISK-009。下游模块（M002~M007）字段级设计沿用本模型。
>
> **需求澄清重构（v0.13.0，2026-09-10）**：经 `CR-003`（Approved）与 `ADR-013`（双层模型 Accepted），任务语义与判定粒度修正 —— **事实层按天**（DATA-001 唯一键改为 `(student_id, category, belong_date)`，新增按天归属字段）、**聚合层跨天**（新增 DATA-012/013 承载展示与**判定单元**）、**挂接放开为 N:N**（DATA-016）、**输入源多段化**（DATA-015）、**内容项只读**（DATA-014）、**完成分析独立**（DATA-017）、**窗口策略配置**（DATA-018）。**`task_items`（逐题建模）废弃**；**ADR-010 判定粒度作废**（改为聚合子任务(学科)级，端到端直判原则保留）。权威源：`docs/requirements/CLARIFICATION-2026-09-10.md`。

## 核心实体

| DATA ID | 实体 | Owner 模块 | 数据库/存储 | Writer | Reader | 敏感级别 | 生命周期 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DATA-001 | 作业任务（**按天**的布置记录：唯一键 **`(student_id, category, belong_date)`** + `week_index`/`spec_status`；**逐题建模 `task_items` 已废弃**，内容项见 DATA-014） | M001 | SQLite | M001 | **M002（V1）**；M005/M007 属 **V2** | 中（含学生作答对象） | 长期（可为 V2 画像留数据） |
| DATA-002 | 用户档案（两级主体 ADR-009：家庭账号家长 + **学生子账号** + 学生档案，ADR-005；档案必填关联学校） | M001（家庭空间/登录基础随 M001 落地） | SQLite | M001（子账号仅家长可开通） | 认证/各模块 | 高（未成年人个人信息） | 长期 |
| DATA-003 | 上传批次与照片（原始/归一；`kind` = `task_spec` \| `homework`，**由上传入口决定**；归属由 1 照片 1 段**放开为 N:N**，见 DATA-016） | M002 | 本地图片目录 + 记录入 SQLite | M002 | **M002（V1）**；M007 属 **V2** | 高（未成年人照片） | 长期（可追溯要求） |
| DATA-004 | AI 识别结果（结构化作答 / **布置单解析**） | **M001（链路 T）/ M002（链路 H）**（`ADR-014` 定稿；原 M003 → Deferred） | SQLite | M001/M002 | **M001/M002（V1）**；M005 属 **V2** | 中 | 长期（可追溯） |
| DATA-005 | 任务匹配结果 | **M002**（`ADR-014`；原 M004 → Deferred） | SQLite | M002 | **M002（V1）**；M005 属 **V2** | 低 | 随评价链留存 |
| DATA-006 | 质量评价结果（六维+综合，含权重版本） | M005（**Deferred，V2**） | SQLite | M005 | M006, M007（**V2**） | 低–中 | 长期（报告/历史） |
| DATA-007 | AI 教师评价（评语/分级建议） | M006 | SQLite | M006 | M007 | 中 | 长期 |
| DATA-008 | 今日综合报告 | M007 | SQLite | M007 | 用户（展示） | 中 | 当日生成，可留存 |
| DATA-009 | AI 调用记录（可追溯链，含 Mock） | 共享/AI 基础设施（**V1 由 `app/core/ai/` / `AGENT-AI` 写入**） | SQLite | V1 = `app/core/ai/`（经 M001/M002 链路）；V2 = M005/M006 | 审计/可追溯查询 | 中（含 prompt 与输出，不含密钥） | 长期（审计/可追溯） |
| DATA-010 | 评分权重/维度配置 | 共享配置 + M005（**Deferred，V2**） | SQLite | M005/配置管理（V2） | M005（V2） | 低 | 随配置发布 |
| DATA-011 | 学校基础字典（全局共享只读，ADR-008） | M001（公共基础数据，无 family 隔离） | SQLite | 仅初始化 seed（运行期无写路径） | M001 建档、M007（展示学校名） | 低（公共信息） | 长期（随 seed/变更升级） |
| DATA-012 | **聚合任务** `task_groups`（成员 = 若干天任务；`policy_version` 锁定生成时的配置版本；展示名"周末作业/第 N 周/假期周"） | M001（聚合层） | SQLite | M001 | **M002（V1）**；M005/M007 属 **V2** | 中 | 长期 |
| DATA-013 | **聚合学科子任务** `task_group_subjects`（按 subject 合并；**★判定单元**，含完成结论） | M001（聚合层） | SQLite | M001 | **M002（V1）**；M005/M007 属 **V2** | 中 | 长期 |
| DATA-014 | 任务内容项 `task_contents`（带 `subject` 标签，聚合合并原料；**V1 只读展示，不参与挂接/判定**） | M001 | SQLite | M001（经 AI 解析草稿 + 家长确认） | M001, M002, M007 | 中 | 长期 |
| DATA-015 | 任务输入源 `task_spec_sources`（多段：`kind` = `text` \| `image`；承载粘贴文本/图片/聊天记录粘贴） | M001 | SQLite | M001 | M001 | 中 | 长期 |
| DATA-016 | **作业照片挂接** `photo_subject_links`（照片 ↔ 聚合子任务 **N:N**，含 `source`(ai\|manual)/`confidence`/`confirmed_at`/`rejected_at`） | M002 | SQLite | M002 | **M002（V1）**；M005/M007 属 **V2** | 高（未成年人照片关联） | 长期 |
| DATA-017 | **完成情况分析** `completion_analyses`（聚合子任务级结论 + 依据照片 + 置信度 + 草稿/确认 + 重跑版本） | M002 | SQLite | M002（AI 草稿）/ M002（家长确认） | M005, M007 | 中 | 长期（可追溯） |
| DATA-018 | 窗口与聚合策略配置 `window_policies`（`AT_TIMEZONE`/`AT_TERM_START`/`AT_TERM_END`/`AT_DAY_CUTOFF`/周末与假期聚合规则，**带生效日期**） | 共享配置 | SQLite | 配置管理 | M001（归属引擎） | 低 | 随配置发布（**变更不回溯**） |

## 数据所有权原则

> 一个核心业务数据只能有明确的数据所有者（Data Owner）。
> 其他模块原则上通过接口读取，禁止直接修改他人数据 / 直接访问他人数据库。

- 可追溯链数据由各产生环节经统一 API 写入 DATA-009，读取仅限审计/追溯场景 —— **V1 产生环节 = `app/core/ai/`（由 M001 链路 T / M002 链路 H 调用）；V2 增加 M005/M006**（`ADR-014`）
- DATA-002 用户档案（家庭账号 + 学生档案）Owner = M001（V1 家庭空间/登录基础随首个模块 M001 落地；引入真实教师/班级体系时按变更流程拆分）
- DATA-011 学校字典（`schools`）= **全局公共只读基础数据**（ADR-008）：无 `family_id`、不做家庭过滤（家庭数据隔离的限定例外）；写入仅限初始化 seed（幂等），运行期无写路径；学生档案经 `school_id` 引用

## 核心字段草案（最终字段待模块数据设计）

| 实体 | 关键属性（草案） |
| --- | --- |
| DATA-001 作业任务 | 任务ID/家庭ID/学生ID/**`category`(v1 仅 school)**/**`belong_date`（4 点边界、Asia/Shanghai）**/**`week_index`**/**`window_type`(day\|weekend\|holiday)**/**`spec_status`(placeholder\|parsed\|confirmed)**/自动生成标题/状态/截止时间 —— **唯一键 `(student_id, category, belong_date)`；只承载"哪天布置了什么"，不承载判定（ADR-013）** |
| DATA-002 用户档案 | 家庭账号(账号ID/登录凭证哈希/显示名) + **学生子账号(子账号ID/家庭ID/学生ID 唯一/登录名唯一/口令哈希/启停状态，ACR-001)** + 学生档案(档案ID/家庭ID/姓名/年级/与账号关系/关联学校 school_id→schools[必填, ADR-008]) + 会话(主体类型 family\|student + 可选学生ID，双型会话) |
| DATA-003 上传批次与照片 | `upload_batches`(batch_id/student_id/**kind**(task_spec\|homework)) + `photos`(photo_id/batch_id/student_id/kind/seq_no/status(unassigned\|suggested\|assigned\|rejected)/**task_id(窗口级)**/quality_report_json/sha256/consumed_at)；~~subject/group_no/suggestion_json~~ Deprecated → DATA-016 |
| DATA-004 识别结果 | 识别ID/提交ID/题目级或整页结构(题号/题目/作答/过程)/置信度/模型信息（含"布置单识别"清单草稿类型，CR-002） |
| DATA-005 匹配结果 | 匹配ID/提交ID/任务ID/对齐关系(题号↔题目)/判定(完成/未完成/对/部分对/错/无法判断)/依据/置信度/状态 —— **内容级逐题对齐判定（ADR-010/CR-002）** |
| DATA-006 质量评价 | 评价ID/提交ID/六维度分+权重版本/大模型综合评判(逐题结论+依据)/综合分/置信度/规则版本 —— **AI 评判为核（q2-3/PD-023）** |
| DATA-007 教师评价 | 评价ID/质量评价ID/评语文案/分级重写建议/依据/置信度/prompt 版本 |
| DATA-008 今日报告 | 报告ID/学生ID/日期/任务评价聚合/报告快照 |
| DATA-009 AI 调用记录 | 调用ID(`call_id`)/`request_id`/`family_id`/`capability`(任务解析\|挂接建议\|完成分析\|OCR)/`provider_kind`/`provider_name`/`model`/`prompt_key`/`prompt_version`/`attempt`/`latency_ms`/`token_usage`/`result`/`confidence`/`status`/`mock`/`error`/`input_ref`/`created_at`（**`Task-006` 已实施回填，物理表 `ai_call_records`**） |
| DATA-010 评分配置 | 维度/权重/版本/生效范围 |
| DATA-011 学校字典 | school_id/name/stage(学段 primary\|junior\|senior)/seed 预置；全局共享只读（ADR-008） |
| DATA-012 聚合任务 | group_id/学生ID/聚合键(`belong_date` 或 周末/假期周标识)/展示名("周末作业"/"第 N 周")/成员天任务集合/**`policy_version`**/生成时间 |
| DATA-013 聚合学科子任务 | group_subject_id/group_id/subject/合并而来的内容项引用/完成结论(完成\|部分完成\|未完成\|无法判断，未分析时为空)/结论状态(pending\|draft\|confirmed) —— **★判定单元（ADR-013；`confirmed` 后禁改归属日）** |
| DATA-014 任务内容项 | content_id/task_id(subject 标签)/seq/文本；**只读展示，不参与挂接/判定** |
| DATA-015 任务输入源 | source_id/task_id/seq/kind(text\|image)/text_content/photo_id(可空)/created_at |
| DATA-016 作业照片挂接 | link_id/photo_id/group_subject_id/source(ai\|manual)/confidence/confirmed_at/rejected_at —— **N:N** |
| DATA-017 完成情况分析 | analysis_id/group_subject_id/结论/依据照片集合/置信度/状态(draft\|confirmed)/模型与 prompt 版本/重跑版本号/确认人/确认时间 |
| DATA-018 窗口与聚合策略配置 | policy_id/配置项/值/生效日期(effective_from)/版本号 —— **变更只影响未聚合对象，已聚合按生成时版本（ADR-013）** |

## 数据来源与消费者

闭环数据来源与流向见 `SYSTEM_SUMMARY.md` 数据流；详细字段级读写映射在各模块 `MODULE_DATA.md` 定义。

## 数据敏感级别与要求

- DATA-002/DATA-003 涉及未成年人：加密存储、访问授权、审计日志、脱敏展示；禁止明文入普通日志
- DATA-009：不含 Provider 密钥；日志中禁止记录密钥/完整用户姓名等敏感字段（开发用样例数据需脱敏）
- Secret（AI Key/库口令）：走配置/环境/密钥管理，禁止硬编码（`DEVELOPMENT_GUIDE.md` §7）

## 数据 Breaking Change 要求

结构修改必须分析：现有数据 / 迁移 / 回滚 / 索引 / 性能 / 消费者 / 备份 / 兼容性（详见 `DEVELOPMENT_GUIDE.md`）。V1 无历史生产数据，但消费者（下游模块）名单需同步检查。
