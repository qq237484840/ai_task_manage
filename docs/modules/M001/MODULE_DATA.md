# M001 模块数据（权威源）—— 作业任务管理

- **状态**：**v0.2.0（Frozen，用户批准 2026-09-10）** —— 按 `CR-003`/`ADR-013`/`REQ-010` 修订：**事实层按天**（`tasks` 唯一键 `(student_id, category, belong_date)`）+ **聚合层**（新增 DATA-012/013）+ **输入源多段化**（DATA-015）+ **内容项**（DATA-014）；`task_items` **Deprecated**。〔前版 v0.1.2 定稿，2026-09-08〕
- **Owner**：M001（家庭数据唯一写入口；DATA-011 学校字典仅初始化 seed 写入，运行期无写路径）；映射全局实体 **DATA-001 / DATA-002 / DATA-011 / DATA-012 / DATA-013 / DATA-014 / DATA-015**（`DATA_MODEL.md` 为全局登记，本文件为字段级权威源）
- **存储**：SQLite 单文件（ADR-004/ASM-010）；ORM 抽象为 PostgreSQL 迁移预留（见 `MODULE_DESIGN.md`）
- **权威源**：`docs/requirements/CLARIFICATION-2026-09-10.md`（冲突时以其为准）、`docs/requirements/REQ-010.md`、`docs/adr/ADR-013.md`、`docs/CONFIGURATION.md`

## 表结构与字段

### `family_accounts`（家庭账号，映射 DATA-002）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `family_id` | TEXT(UUID) | PK | 家庭标识，全系统归属键 |
| `login_name` | TEXT | UNIQUE NOT NULL | 登录名（≤64，如邮箱/手机号） |
| `password_hash` | TEXT | NOT NULL | scrypt 哈希 `salt$hash`，禁止明文 |
| `display_name` | TEXT | NOT NULL(≤32) | 家庭显示名 |
| `created_at` / `updated_at` | TEXT(ISO) | NOT NULL | 审计时间 |

### `schools`（学校基础字典，映射 DATA-011）—— 全局共享只读

> 公共基础数据，不归属家庭（ADR-008）；仅初始化 seed 写入，运行期无写 API（后台维护预留，V1 不开发）。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `school_id` | TEXT(UUID) | PK | 学校 ID（全局唯一） |
| `name` | TEXT | NOT NULL(≤64) | 学校名称 |
| `stage` | TEXT | NOT NULL DEFAULT 'primary' | 学段建议值 `primary/junior/senior`（文本存储不写死枚举；V1 起步 primary，ASM-011 口径） |
| `created_at` / `updated_at` | TEXT(ISO) | NOT NULL | 审计时间 |

约束：`UNIQUE(name, stage)`（防重复预置）；`name` 需去首尾空白，大小写不敏感唯一判定见实现（seed 数据本身已规范）。

### `students`（学生档案，映射 DATA-002）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `student_id` | TEXT(UUID) | PK | 学生档案 ID |
| `family_id` | TEXT(UUID) | FK→family_accounts, NOT NULL | 归属家庭（索引） |
| `name` | TEXT | NOT NULL(≤32) | 学生姓名 |
| `grade_level` | TEXT | NULL | 年级/学段（自由文本） |
| `school_id` | TEXT(UUID) | FK→schools, NOT NULL | 关联学校（必填；全局字典条目，索引） |
| `relation` | TEXT | NULL(≤16) | 与账号关系（可选，如 爸爸/妈妈） |
| `created_at` / `updated_at` | TEXT(ISO) | NOT NULL | 审计时间 |

### `student_accounts`（学生子账号，映射 DATA-002；两级主体 ADR-009/ACR-001）

> 家长（family 主体）为某学生档案开通的登录凭据，供学生本人登录（仅本人数据）。与 `family_accounts` 构成两级主体：家长=全家+兜底，学生=仅本人。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `student_account_id` | TEXT(UUID) | PK | 子账号 ID |
| `family_id` | TEXT(UUID) | FK→family_accounts, NOT NULL | 归属家庭（索引） |
| `student_id` | TEXT(UUID) | FK→students, UNIQUE NOT NULL | 绑定的学生档案（一人一账号，索引） |
| `login_name` | TEXT | UNIQUE NOT NULL(≤64) | 学生登录名（**学生命名空间全局唯一**，可与 family 登录名同名——登录入口已分流） |
| `password_hash` | TEXT | NOT NULL | scrypt 哈希（同家庭账号，禁止明文） |
| `status` | TEXT | NOT NULL DEFAULT 'active' | `active/disabled`（disabled 不可登录；家长停用管控） |
| `created_at` / `updated_at` | TEXT(ISO) | NOT NULL | 审计时间 |

### `auth_sessions`（会话，DATA-002 附属，仅存哈希；两级主体）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `session_id` | TEXT(UUID) | PK | 会话 ID |
| `family_id` | TEXT(UUID) | FK, NOT NULL | 归属家庭（数据隔离底线，两类主体均非空；索引） |
| `subject_type` | TEXT | NOT NULL DEFAULT 'family' | 主体类型 `family/student`（会话语义分派） |
| `student_id` | TEXT(UUID) | FK→students, NULL | 仅 student 主体非空（绑定本人档案；索引） |
| `token_hash` | TEXT | UNIQUE NOT NULL | token 单向哈希（索引） |
| `expires_at` | TEXT(ISO) | NOT NULL | 过期时间（默认 30 天） |
| `created_at` | TEXT(ISO) | NOT NULL | 登录时间 |

### `tasks`（作业任务，映射 DATA-001 —— **事实层按天**，ADR-013）

> 只承载"哪一天（归属窗口）通过什么输入源布置了什么"，**不承载判定**；判定落聚合层 `task_group_subjects`。唯一键 = `(student_id, category, belong_date)`。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `task_id` | TEXT(UUID) | PK | 任务 ID |
| `family_id` | TEXT(UUID) | FK, NOT NULL | 归属家庭（索引 `(family_id, student_id, belong_date)`） |
| `student_id` | TEXT(UUID) | FK→students, NOT NULL | 作业对象（本家庭学生） |
| `category` | TEXT | NOT NULL DEFAULT 'school' | 任务类型，**V1 仅 `school`**（字段预留多任务类型 V2） |
| `belong_date` | TEXT(DATE) | NOT NULL | **归属日**（`AT_TIMEZONE`=Asia/Shanghai、`AT_DAY_CUTOFF` 日界；上传即固化、不回算） |
| `week_index` | INT | NOT NULL | 周次（`AT_TERM_START` 所在周的周一起算；`WindowResolver` 生成） |
| `window_type` | TEXT | NOT NULL | 归属窗口类型 `day\|weekend\|holiday` |
| `spec_status` | TEXT | NOT NULL DEFAULT 'placeholder' | 解析状态机 `placeholder\|parsed\|confirmed`（见 `MODULE_CONTRACT.md` §F1） |
| `title` | TEXT | NOT NULL(≤64) | 展示标题；**可由窗口解析器自动生成**（如「09-09 周三」），家长可改（占位主任务 B7） |
| `grade_level` | TEXT | NULL | 年级/学段 |
| `status` | TEXT | NOT NULL | `draft/published/in_progress/closed`（状态机契约） |
| `deadline` | TEXT(ISO) | NULL | 截止时间（展示/提示，V1 不自动执行关闭） |
| `created_at` / `updated_at` | TEXT(ISO) | NOT NULL | 审计时间 |
| ~~`subject`~~ | — | **Deprecated** | 原「多学科登记单主学科标注」**作废**（容器化语义取消，ADR-013）；学科标签移至 `task_contents.subject` / 聚合层 `task_group_subjects.subject` |
| ~~`content`~~ | — | **Deprecated** | 原「作业内容描述」不再由家长录入；内容项见 `task_contents` |

约束：`UNIQUE(student_id, category, belong_date)`（**事实层按天唯一**）；`belong_date`/`week_index`/`window_type` 由归属引擎于写入时计算并**固化**；旧联合索引 `(family_id,status,created_at)` 保留。

### `task_contents`（任务内容项，映射 DATA-014；FK `task_id`）

> 由 AI 解析草稿 + 家长确认产生；**V1 只读展示，不参与挂接与判定**（聚合层合并的原料）。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `content_id` | TEXT(UUID) | PK | 内容项 ID |
| `task_id` | TEXT(UUID) | FK→tasks, NOT NULL | 所属任务（索引） |
| `subject` | TEXT | NOT NULL | 学科标签（如 math/chinese/english；ASM-011 建议值，不写死） |
| `seq` | INT | NOT NULL | 任务内序号（1 起） |
| `text` | TEXT | NOT NULL(≤2000) | 内容项文本（家长可删/改） |
| `created_at` | TEXT(ISO) | NOT NULL | 审计时间 |

### `task_spec_sources`（任务输入源，映射 DATA-015；多段）

> 任务输入源：粘贴文本 / 图片（多段可混排）；上传时**无需填写任何内容**。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `source_id` | TEXT(UUID) | PK | 输入源 ID |
| `task_id` | TEXT(UUID) | FK→tasks, NOT NULL | 所属任务（索引） |
| `seq` | INT | NOT NULL | 段序号（1 起，任务内唯一） |
| `kind` | TEXT | NOT NULL | 源类型 `text\|image` |
| `text_content` | TEXT | NULL(≤4000) | 文本块内容（`kind=text`；聊天记录降级为粘贴文本 A2） |
| `photo_id` | TEXT(UUID) | NULL | 图片块引用（`kind=image`；**照片实体 Owner = M002**，本表仅存引用，不建跨模块 FK） |
| `created_at` | TEXT(ISO) | NOT NULL | 审计时间 |

### `task_groups`（聚合任务，映射 DATA-012 —— 聚合层，ADR-013）

> 聚合落库固化：成员 = 若干天 `tasks`；**展示/挂接/判定/（V2）报告走同一代码路径**，仅成员集合不同。每个 `belong_date` 至少一个聚合（最小 1 天）。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `group_id` | TEXT(UUID) | PK | 聚合 ID |
| `family_id` | TEXT(UUID) | FK, NOT NULL | 归属家庭（索引） |
| `student_id` | TEXT(UUID) | FK→students, NOT NULL | 归属学生 |
| `category` | TEXT | NOT NULL DEFAULT 'school' | 任务类型（同 `tasks.category`） |
| `group_key` | TEXT | NOT NULL | 聚合键：`belong_date`（`day`）或 周末/假期周标识（`W:2026-09-11` / `H:2026-07-01.W1`） |
| `display_name` | TEXT | NOT NULL(≤32) | 展示名（「周末作业」/「第 N 周」/ 日期） |
| `window_type` | TEXT | NOT NULL | `day\|weekend\|holiday` |
| `policy_version` | TEXT | NOT NULL | **生成时生效的配置版本**（锁定；后续**追加数据不改**该字段） |
| `created_at` / `updated_at` | TEXT(ISO) | NOT NULL | 审计时间 |

约束：`UNIQUE(student_id, category, group_key)`（同学生同窗口唯一聚合）。

### `task_group_subjects`（聚合学科子任务，映射 DATA-013 —— **★判定单元**）

> 按 `subject` 合并聚合内各天任务的内容项；**判定单元**（完成结论 + 依据 + 置信度由 M002 计算，**经 M001 内部接口回写**，见 DATA-017）。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `group_subject_id` | TEXT(UUID) | PK | 判定单元 ID |
| `group_id` | TEXT(UUID) | FK→task_groups, NOT NULL | 所属聚合（索引） |
| `subject` | TEXT | NOT NULL | 学科（合并键） |
| `content_refs` | TEXT(JSON) | NULL | 合并而来的内容项引用（`task_contents.content_id` 列表，展示用） |
| `conclusion` | TEXT | NULL | 完成结论 `完成\|部分完成\|未完成\|无法判断`（未分析时为空） |
| `conclusion_status` | TEXT | NOT NULL DEFAULT 'pending' | `pending\|draft\|confirmed`（`confirmed` 后禁改归属日，§F5④） |
| `created_at` / `updated_at` | TEXT(ISO) | NOT NULL | 审计时间 |

约束：`UNIQUE(group_id, subject)`。

### `task_items`（题目集，DATA-001 附属 —— **Deprecated**）

> **已废弃（ADR-013）**：逐题建模不再作为判定载体，V1 **不再写入**；表保留以兼容旧数据与回滚。相关实现（逐题校验、学科作业段 `group_no`、`get_task_group(s)` 段级查询）进入**移除路径**，实施阶段（③）按新契约重构，`reference_answer` 字段随表一同退役（端到端直判原则由 ADR-013 继承）。

## 约束与规则

- **归属过滤（两级主体底线）**：家庭数据（账号/档案/会话/任务）查询一律强制 `family_id`；Repository 层禁止无 `family_id` 的裸查询。**例外：`schools` 为全局共享只读字典，不带 `family_id`**（ADR-008）。student 会话在 family 底线之上**额外强制本人**（`student_id` 过滤；URL 传参他人 = 对外 404，见 `MODULE_DESIGN.md` 授权矩阵）
- **两级主体**：family 主体=本家任意学生可操作 + 家长兜底；student 主体=仅本人数据可读写。子账号开通/停用/改密、档案创建为**家长专属**（student 主体 403）。family 与 student 登录名分属独立命名空间（均可同名），登录防爆破按命名空间隔离（`shared/auth.py`）
- **口令与会话安全**：`family_accounts`/`student_accounts` 口令一律 scrypt（每账号随机盐，存储 `salt$hash$n$r$p`）；`auth_sessions` 仅存 token 单向哈希；登录失败计数 + 渐进退避（进程内）
- **学校字典只读**：`schools` 仅在数据库初始化时以 seed 写入（幂等）；运行期不存在任何创建/更新/删除路径；`students.school_id` 必须在 `schools` 中存在（DB FK + 应用校验双保险）
- **归属引擎与固化**（ADR-013/`CONFIGURATION.md`）：`belong_date = (ts − AT_DAY_CUTOFF).date()`（`AT_TIMEZONE`=Asia/Shanghai；时间戳按 UTC 存储、仅计算处转换）；`week_index` 起算 = `AT_TERM_START` 所在周的周一；写入即**固化**，配置变更**不回算历史**。`WindowResolver` 为策略接口（可替换规则）
- **事实层按天唯一**：`UNIQUE(student_id, category, belong_date)`；同日同类型重复上传按 §F1 **幂等归集**（追加内容项 / 新增学科标签），不新建 `tasks`
- **配置锁定语义**（A7/B5）：配置变更**只影响未聚合对象**；已聚合按生成时 `task_groups.policy_version` 执行；锁定**粒度** = 每个 `(学生, 聚合对象)` 独立锁；锁定**触发** = 数据写入（任务解析完成 / 作业照片上传），**纯浏览不锁**
- **解析状态机**（A4/B7）：`spec_status = placeholder → parsed → confirmed`（允许 `placeholder → confirmed`）；`title` 可自动生成占位名，家长可改
- **聚合生成**：写入时 `ensure_group`（幂等）创建/复用 `task_groups` 与 `task_group_subjects`；追加数据只新增成员，**不改 `policy_version`**；`UNIQUE(student_id, category, group_key)`、`UNIQUE(group_id, subject)`
- **判定单元只读约束**：`task_group_subjects.conclusion`/`conclusion_status` 由 **M002 计算、经 M001 内部接口回写**；M002 不得直写本表
- **内容项与输入源只读**：`task_contents` V1 不参与挂接与判定（仅展示）；`task_spec_sources.photo_id` 只存引用（照片实体 Owner = M002，不建跨模块 FK）
- **手工改归属日连锁规则**（A8/B8）：① 重算快照 ② 迁移主表 FK（目标聚合无则建）③ 源聚合变空则删 ④ **已被完成分析消费的作业禁改**（`conclusion_status=confirmed` → 直接拒绝）⑤ 记审计 ⑥ **跨聚合迁移须同步更新 `photo_subject_links` 挂接目标**（经 M002 内部接口）
- **任务冻结规则**：`tasks` 的归属字段（`belong_date`/`week_index`/`window_type`）在聚合被完成分析消费后不可改；任务状态推进不受影响
- **写一致性**：任务 + 输入源 + 内容项（+ 幂等聚合生成）在**同一事务**内写；部分失败整体回滚；唯一键冲突 → 409
- 状态迁移仅允许表内列举的合法边（契约/实现 `MODULE_DESIGN.md` 状态机）
- 学生档案删除：V1 不提供物理删除（未成年人数据留存与可追溯要求），仅可更新；删除需求按变更流程另行评估

## 与全局数据模型的关系

- **M001 Owned**：DATA-001（`tasks`；`task_items` Deprecated）、DATA-002、DATA-011、DATA-012（`task_groups`）、DATA-013（`task_group_subjects`）、DATA-014（`task_contents`）、DATA-015（`task_spec_sources`）—— 登记（Writer/Reader/敏感级别/生命周期）以 `DATA_MODEL.md` 为准，字段级以本文件为准。
- **非 M001 Owned（只读/协作）**：DATA-003（照片与批次，M002；M001 仅经 `task_spec_sources.photo_id` 引用）、DATA-016（`photo_subject_links`，M002）、DATA-017（`completion_analyses`，M002；结论经 M001 内部接口回写 DATA-013）、DATA-018（`window_policies`，共享配置，M001 只读）、DATA-009（AI 调用记录，`app/core/ai/` 写入）。
- 若发现漂移：以 `DATA_MODEL.md` 为顶层登记、本文件为细化，矛盾时优先本文件字段并提请 PM 同步顶层。
