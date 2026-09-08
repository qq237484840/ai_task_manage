# M001 模块摘要 —— 作业任务管理（30 秒速览）

- **状态**：Stable + CHANGE-001 编码完成回填（89 测试全绿，2026-09-08；待 PM 复核后收口 v0.1.2）
- **入口文档**：`MODULE.md`（总览）→ `MODULE_CONTRACT.md`（黑盒契约）→ `MODULE_API.md` → `MODULE_DATA.md`

| 维度 | 摘要 |
| --- | --- |
| Purpose | V1 基座：家庭空间（家庭账号 + 学生子账号**两级主体** + 学生档案，档案必填关联学校）与作业任务生命周期（**多学科登记单容器**，学科粒度 `(subject,group_no)`）；题目逐题建模，参考答案为非判定基准辅助字段 |
| Key Decisions | ADR-005 纯家庭身份 + ADR-009/ACR-001 两级主体、ADR-010/ACR-002 参考答案非基准（端到端直判）、ADR-008 学校基础字典=全局共享只读 + seed 预置 + 档案必填关联（REQ-009）、CR-001 任务容器化（group_no 学科作业段）、ASM-011 小学语数英起步 |
| Inputs | 家长注册/学生登录凭据、学生档案（必填 `school_id`）、任务与题目集（subject/group_no/辅助参考答案）、状态推进动作 |
| Outputs | 双主体会话 token、学校字典只读列表、学生档案列表、任务（含题目与段）数据、状态迁移结果 |
| Dependencies | 仅 shared/infrastructure（日志/异常/配置/DB/安全工具/双主体认证注入） |
| APIs | REST `API-M001-001~012`（Frozen 面，随 CHANGE-001 修订）+ ACR-001 新增（子账号/学生登录/me，待编号）+ 内部接口 `FamilySpaceService`/`StudentAccountService`/`TaskQueryService`（含段查询）/`TaskStateService` |
| Data | `schools`（全局只读公共）、`family_accounts`、`students`、`student_accounts`、`auth_sessions`（family/student 两型）、`tasks`、`task_items`（映射 DATA-001/DATA-002/DATA-011） |
| 核心规则 | 家庭数据带 `family_id` 强制过滤（例外：`schools` 公共只读）；student 主体仅本人（越权对外 404）；子账号管理/建档家长专属（403）；密码/令牌哈希存储；登录爆破 family/student 命名空间隔离；任务状态机 `draft→published→in_progress→closed`；发布后/开始上传后题目不可改 |
| Main Risks | 题目录入负担（RISK-002 缓解中）；账号数据属未成年人个人信息（RISK-004）；子账号口令由儿童保管风险（RISK 缓解：停用开关+家长兜底）；seed 学校覆盖不足（REQ-009） |
| Status | Stable + CHANGE-001 执行回填（编码/测试完成，待 PM 复核；历史见 `MODULE_CHANGELOG.md`） |

## 进入本模块前建议阅读

1. `ADR-005` + `ADR-009`/`ACR-001`（两级主体：家长=全家兜底，学生=仅本人）
2. `ADR-010`/`ACR-002`（参考答案非判定基准，端到端直判）+ `CR-001`（任务容器化/group_no）
3. `ADR-008` + `REQ-009`（学校基础字典：全局共享只读、档案必填关联）
4. `REQ-001`（作业任务管理需求）
5. `DATA_MODEL.md`（DATA-001/002/011）
