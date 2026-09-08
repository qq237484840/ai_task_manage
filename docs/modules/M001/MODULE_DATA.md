# M001 模块数据（权威源）—— 作业任务管理

- **状态**：随 CHANGE-001 修订（2026-09-08 编码完成回填；变更经 CR-001/CR-002/ACR-001/ACR-002 批准，待 PM 收口复核后定稿 v0.1.2）
- **Owner**：M001（家庭数据唯一写入口；DATA-011 学校字典仅初始化 seed 写入，运行期无写路径）；映射全局实体 DATA-001 / DATA-002 / DATA-011（`DATA_MODEL.md` 为全局登记，本文件为字段级权威源）
- **存储**：SQLite 单文件（ADR-004/ASM-010）；ORM 抽象为 PostgreSQL 迁移预留（见 `MODULE_DESIGN.md`）

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

### `tasks`（作业任务，映射 DATA-001）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `task_id` | TEXT(UUID) | PK | 任务 ID |
| `family_id` | TEXT(UUID) | FK, NOT NULL | 归属家庭（联合索引 `(family_id,status,created_at)` / `(family_id,student_id,created_at)`） |
| `student_id` | TEXT(UUID) | FK→students, NOT NULL | 作业对象（本家庭学生） |
| `title` | TEXT | NOT NULL(≤64) | 任务标题 |
| `subject` | TEXT | NULL | 登记单主学科标注（CR-001 放宽）：单学科任务存学科小写值；**多学科登记单**存 NULL 或字面量 `'mixed'`（学科粒度见 `task_items.subject` + `group_no` 学科作业段）；建议值 chinese/math/english，不写死（ASM-011） |
| `grade_level` | TEXT | NULL | 年级/学段 |
| `content` | TEXT | NULL(≤2000) | 作业内容描述 |
| `status` | TEXT | NOT NULL | `draft/published/in_progress/closed`（状态机契约） |
| `deadline` | TEXT(ISO) | NULL | 截止时间（展示/提示，V1 不自动执行关闭） |
| `created_at` / `updated_at` | TEXT(ISO) | NOT NULL | 审计时间 |

### `task_items`（题目集，DATA-001 附属，逐题建模；多学科容器 CR-001）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `item_id` | TEXT(UUID) | PK | 题目 ID |
| `task_id` | TEXT(UUID) | FK→tasks, NOT NULL | 所属任务（联合约束 `(task_id, seq)` 唯一） |
| `seq` | INT | NOT NULL | 题号（任务内唯一，1 起连续） |
| `item_type` | TEXT | NOT NULL | 题型标注 `objective/subjective`（**仅标注，不驱动判定**；ADR-010 端到端直判） |
| `subject` | TEXT | NOT NULL | 该题学科（学科作业段第一维度） |
| `group_no` | INT | NOT NULL DEFAULT 0 | 学科作业段号（第二维度；CR-001 收敛语义：全 0=默认单段/旧数据兼容并允许跨科目，显式分组时从 1 起连续且禁止 0，段内科目一致、题目块连续不交错）；索引 `(task_id, subject, group_no)` |
| `stem` | TEXT | NOT NULL(≤2000) | 题干 |
| `reference_answer` | TEXT | NULL | **非判定基准**辅助字段（ADR-010/ACR-002）：判定链端到端直判，不依赖本字段比对；仅客观题可选录入，主观题必须为空（防误导）；`include_answers` 控制可见 |

## 约束与规则

- **归属过滤（两级主体底线）**：家庭数据（账号/档案/会话/任务）查询一律强制 `family_id`；Repository 层禁止无 `family_id` 的裸查询。**例外：`schools` 为全局共享只读字典，不带 `family_id`**（ADR-008）。student 会话在 family 底线之上**额外强制本人**（`student_id` 过滤；URL 传参他人 = 对外 404，见 `MODULE_DESIGN.md` 授权矩阵）
- **两级主体**：family 主体=本家任意学生可操作 + 家长兜底；student 主体=仅本人数据可读写。子账号开通/停用/改密、档案创建为**家长专属**（student 主体 403）。family 与 student 登录名分属独立命名空间（均可同名），登录防爆破按命名空间隔离（`shared/auth.py`）
- **口令与会话安全**：`family_accounts`/`student_accounts` 口令一律 scrypt（每账号随机盐，存储 `salt$hash$n$r$p`）；`auth_sessions` 仅存 token 单向哈希；登录失败计数 + 渐进退避（进程内）
- **学校字典只读**：`schools` 仅在数据库初始化时以 seed 写入（幂等）；运行期不存在任何创建/更新/删除路径；`students.school_id` 必须在 `schools` 中存在（DB FK + 应用校验双保险）
- **参考答案非基准**（ADR-010/ACR-002）：`reference_answer` 仅为**辅助字段**，判定链端到端直判、不以其为比对基准；敏感度同"作业内容"，禁止入普通日志；`include_answers` 访问必须与任务 `family_id` 一致
- **学科作业段结构**（CR-001）：显式分组时 group_no 从 1 起连续（无空洞、禁 0）、段内 subject 一致、同组题目连续不交错；全 0=默认单段收敛语义（旧数据/单学科兼容）
- **任务冻结规则**：任务存在任意已提交上传（M002 写入提交记录）后，`tasks` 与 `task_items` 不可更新题目（防基准漂移）；仅允许状态推进/关闭
- **写一致性**：任务+题目集在**同一事务**内写；部分失败整体回滚
- 状态迁移仅允许表内列举的合法边（契约/实现 `MODULE_DESIGN.md` 状态机）
- 学生档案删除：V1 不提供物理删除（未成年人数据留存与可追溯要求），仅可更新；删除需求按变更流程另行评估

## 与全局数据模型的关系

- DATA-001 / DATA-002 / DATA-011 的登记（Writer/Reader/敏感级别/生命周期）以 `DATA_MODEL.md` 为准，字段级以本文件为准，两者一致（若发现漂移，以 `DATA_MODEL.md` 为顶层登记、本文件为细化，矛盾时优先本文件字段并提请同步顶层）。
