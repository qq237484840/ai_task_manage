# M001 模块摘要 —— 作业任务管理（30 秒速览）

- **状态**：Stable（代码 v0.1.2）＋ **契约 v0.2.0 —— Frozen（用户批准 2026-09-10）**（`Task-004` 交付并经 PM 复核 APPROVED；按 `CR-003`/`ADR-013`/`REQ-010`；③ 实施 = `Task-007`）
- **入口文档**：`MODULE.md`（总览）→ `MODULE_CONTRACT.md`（黑盒契约）→ `MODULE_API.md` → `MODULE_DATA.md`
- **前版**：v0.1.2（2026-09-08 CHANGE-001 Applied，89 测试全绿）—— 其"多学科登记单容器 / 学科作业段 `group_no` / 逐题条目"语义**已作废**

| 维度 | 摘要 |
| --- | --- |
| Purpose | V1 基座：家庭空间（家庭账号 + 学生子账号**两级主体** + 学生档案）+ **按天作业任务**（链路 T：输入源上传 → AI 解析草稿 → 家长确认/隐式确认）+ **归属引擎** + **聚合层**（`task_groups` → `task_group_subjects` ★判定单元） |
| Key Decisions | ADR-005 纯家庭身份；ADR-009/ACR-001 两级主体；**ADR-013 双层模型（事实层按天 + 聚合层跨天，判定落聚合层）**；ADR-014（V1 = M001+M002+`app/core/ai/`，M003/M004 职责吸收、M005~M007 后置 V2）；ADR-008 学校字典全局只读 + seed；ASM-011 小学语数英起步；ADR-012 前端工程化（Vue3+Vite+TS+Vant 4，dist 由 FastAPI 托管） |
| Inputs | 家长注册/学生登录凭据；学生档案（必填 `school_id`）；**任务输入源（图片 / 粘贴文本，多段）**；解析确认动作；手工改归属日动作；状态推进动作 |
| Outputs | 双主体会话 token；学校字典只读列表；学生档案列表；**任务事实（`tasks`+内容项+输入源）**、**聚合（聚合任务 + 聚合学科子任务）**、状态迁移结果 |
| Dependencies | shared/infrastructure（日志/异常/配置/DB/安全工具/双主体认证注入）+ **`app/core/ai/`（链路 T 解析）** |
| APIs | REST `API-M001-001~017`（既有面，其中任务创建/查询随 CR-003 修订）+ **CR-003 新增**：输入源上传 / 解析草稿查询 / 解析确认（含隐式确认）/ 聚合查询 / 改归属日（**`API-M001-018~021`**）+ 内部接口 `FamilySpaceService`/`StudentAccountService`/`TaskQueryService`（事实层+聚合层）/`TaskStateService`/`WindowResolver` |
| Data | **Own**：`tasks`（DATA-001，按天唯一）、`task_contents`（DATA-014）、`task_spec_sources`（DATA-015）、`task_groups`（DATA-012）、`task_group_subjects`（DATA-013）、`family_accounts`/`students`/`student_accounts`/`auth_sessions`（DATA-002）、`schools`（DATA-011，全局只读公共）；`task_items` **Deprecated** |
| 核心规则 | 家庭数据带 `family_id` 强制过滤（例外：`schools` 公共只读）；student 主体仅本人（越权 404）；子账号管理/建档家长专属（403）；**归属日 `(ts−AT_DAY_CUTOFF).date()` 上传即固化**；**配置锁定 = 只影响未聚合对象、按 `(学生,聚合对象)` 独立锁、数据写入才触发、纯浏览不锁**；`spec_status` 状态机 `placeholder→parsed→confirmed`；手工改归属日连锁 6 条；任务状态机 `draft→published→in_progress→closed` |
| Main Risks | **聚合层一致性与 `policy_version` 锁定**（RISK 见 `CHANGE-003` §5）；AI 解析错误污染事实层（草稿必经确认 + 隐式确认展示摘要 + `无法判断` 出口 + 手工兜底）；M001 冻结面被打开（破坏性变更，走 CHANGE-003 显式授权）；账号数据属未成年人个人信息（RISK-004） |
| Status | 契约 **v0.2.0 —— Frozen（用户批准 2026-09-10）**（本 CHANGE 记录见 `MODULE_CHANGELOG.md`） |

## 进入本模块前建议阅读

1. `CLARIFICATION-2026-09-10.md` §2.A/B/D（任务输入源 / 双层归属 / 数据模型定稿）——**权威源**
2. `ADR-013`（双层模型 + 配置锁定语义）+ `ADR-010`（判定粒度 **Superseded**，原则继承）
3. `ADR-014`（V1 范围收窄 + 横切 `app/core/ai/` 执行方）
4. `REQ-010`（需求）+ `REQ-001`（已精校）
5. `CONFIGURATION.md`（4 个 `AT_*` 配置 + 生效锁定 5 条规则）
6. `DATA_MODEL.md`（DATA-001/002/011/012/013/014/015）
