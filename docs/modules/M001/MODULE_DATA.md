# M001 模块数据（权威源）—— 作业任务管理

- **状态**：Frozen（契约基线 v0.1.1，2026-09-08 用户批准；字段级变更走 CR）
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

### `auth_sessions`（会话，DATA-002 附属，仅存哈希）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `session_id` | TEXT(UUID) | PK | 会话 ID |
| `family_id` | TEXT(UUID) | FK, NOT NULL | 归属家庭 |
| `token_hash` | TEXT | UNIQUE NOT NULL | token 单向哈希（索引） |
| `expires_at` | TEXT(ISO) | NOT NULL | 过期时间（默认 30 天） |
| `created_at` | TEXT(ISO) | NOT NULL | 登录时间 |

### `tasks`（作业任务，映射 DATA-001）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `task_id` | TEXT(UUID) | PK | 任务 ID |
| `family_id` | TEXT(UUID) | FK, NOT NULL | 归属家庭（联合索引 `(family_id,status,created_at)`） |
| `student_id` | TEXT(UUID) | FK→students, NOT NULL | 作业对象（本家庭学生） |
| `title` | TEXT | NOT NULL(≤64) | 任务标题 |
| `subject` | TEXT | NOT NULL | 学科文本；建议值 chinese/math/english，不写死（ASM-011） |
| `grade_level` | TEXT | NULL | 年级/学段 |
| `content` | TEXT | NULL(≤2000) | 作业内容描述 |
| `status` | TEXT | NOT NULL | `draft/published/in_progress/closed`（状态机契约） |
| `deadline` | TEXT(ISO) | NULL | 截止时间（展示/提示，V1 不自动执行关闭） |
| `created_at` / `updated_at` | TEXT(ISO) | NOT NULL | 审计时间 |

### `task_items`（题目集，DATA-001 附属，逐题建模 ADR-006）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `item_id` | TEXT(UUID) | PK | 题目 ID |
| `task_id` | TEXT(UUID) | FK→tasks, NOT NULL | 所属任务（索引 `(task_id, seq)`） |
| `seq` | INT | NOT NULL | 题号（任务内唯一，1 起） |
| `item_type` | TEXT | NOT NULL | `objective`（判对错）/`subjective`（只评质量，ADR-006） |
| `subject` | TEXT | NOT NULL | 该题学科（可覆盖任务学科，如英语阅读主观题） |
| `stem` | TEXT | NOT NULL(≤2000) | 题干 |
| `reference_answer` | TEXT | NULL | 仅客观题可选录入；主观题必须为空（校验） |

## 约束与规则

- **归属过滤**：家庭数据（账号/档案/会话/任务）查询强制 `family_id`；Repository 层禁止无 `family_id` 的裸查询。**例外：`schools` 为全局共享只读字典，不带 `family_id`**（ADR-008）
- **学校字典只读**：`schools` 仅在数据库初始化时以 seed 写入（幂等）；运行期不存在任何创建/更新/删除路径；`students.school_id` 必须在 `schools` 中存在（DB FK + 应用校验双保险）
- **参考答案敏感度**：客观题参考答案与作答相关，属"作业内容"敏感数据，禁止入普通日志；`include_answers` 访问必须与任务 `family_id` 一致
- **任务冻结规则**：任务存在任意已提交上传（M002 写入提交记录）后，`tasks` 与 `task_items` 不可更新题目（防评分基准漂移）；仅允许状态推进/关闭
- **写一致性**：任务+题目集在**同一事务**内写；部分失败整体回滚
- 状态迁移仅允许表内列举的合法边（契约/实现 `MODULE_DESIGN.md` 状态机）
- 学生档案删除：V1 不提供物理删除（未成年人数据留存与可追溯要求），仅可更新；删除需求按变更流程另行评估

## 与全局数据模型的关系

- DATA-001 / DATA-002 / DATA-011 的登记（Writer/Reader/敏感级别/生命周期）以 `DATA_MODEL.md` 为准，字段级以本文件为准，两者一致（若发现漂移，以 `DATA_MODEL.md` 为顶层登记、本文件为细化，矛盾时优先本文件字段并提请同步顶层）。
