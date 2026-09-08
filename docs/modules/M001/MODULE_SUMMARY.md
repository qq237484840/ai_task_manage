# M001 模块摘要 —— 作业任务管理（30 秒速览）

- **状态**：Developing（Task-001 编码中；契约 v0.1.1 已批准 Frozen）
- **入口文档**：`MODULE.md`（总览）→ `MODULE_CONTRACT.md`（黑盒契约）→ `MODULE_API.md` → `MODULE_DATA.md`

| 维度 | 摘要 |
| --- | --- |
| Purpose | V1 基座：家庭空间（家庭账号 + 学生档案，档案必填关联学校）与作业任务生命周期；题目逐题建模并承载客观题参考答案（评分基准） |
| Key Decisions | ADR-005 纯家庭身份、ADR-006 分科判定（题目建模依据）、ADR-008 学校基础字典=全局共享只读 + seed 预置 + 档案必填关联（REQ-009）、ASM-011 小学语数英起步（subject/stage 建议值而非硬编码） |
| Inputs | 家庭注册/登录请求、学生档案（必填 `school_id`）、任务与题目集（含可选参考答案）、状态推进动作 |
| Outputs | 登录会话 token、学校字典只读列表、学生档案列表、任务（含题目）数据、状态迁移结果 |
| Dependencies | 仅 shared/infrastructure（日志/异常/配置/DB/安全工具/认证注入） |
| APIs | REST `API-M001-001~012`（/api/v1/family\|schools\|students\|tasks）+ 内部接口 `FamilySpaceService`/`TaskQueryService`/`TaskStateService` |
| Data | `schools`（全局只读公共）、`family_accounts`、`students`、`auth_sessions`、`tasks`、`task_items`（映射 DATA-001/DATA-002/DATA-011） |
| 核心规则 | 家庭数据带 `family_id` 强制过滤（例外：`schools` 公共只读，ADR-008）；学校字典仅 seed 写入、无运行期维护 API；密码/令牌哈希存储；任务状态机 `draft→published→in_progress→closed`；发布后/开始上传后题目不可改 |
| Main Risks | 题目录入负担（RISK-002 缓解中，需轻量录入）；账号数据属未成年人个人信息（RISK-004）；seed 学校覆盖不足（REQ-009 风险，按变更流程补录） |
| Status | Developing（Task-001 编码中；契约 v0.1.1 Frozen） |

## 进入本模块前建议阅读

1. `ADR-005`（家庭账号 + 学生档案 = 唯一身份对象）
2. `ADR-006`（题目建模必须支持学科/题型/参考答案三要素）
3. `ADR-008` + `REQ-009`（学校基础字典：全局共享只读、档案必填关联）
4. `REQ-001`（作业任务管理需求）
5. `DATA_MODEL.md`（DATA-001/002/011）
