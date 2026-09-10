# M001 测试策略与结果 —— 作业任务管理

- **状态**：**v0.2.0（Frozen，用户批准 2026-09-10）** —— 既有实况基线 = **89 passed**（v0.1.2/CHANGE-001，2026-09-08）；本节新增**用例设计**（③ 实施阶段落地 = `Task-007`，`CHANGE-003` §2.1 A10）
- **总体**：遵循 `AGENT_GUIDE.md` §6 DoD。M001 自身**不直接调用 AI Provider**（经 `app/core/ai/`）；链路 T 解析测试通过**注入 Mock/stub Provider**（ADR-011 降级桩）验证编排，不产生真实外呼

## 测试分层与"为何需要/为何不需要"

| 层 | 覆盖 | 为何需要 | 为何不需要其他 |
| --- | --- | --- | --- |
| 单元 | 任务状态机（合法/非法边）、**归属引擎 `WindowResolver` 边界**、解析状态机 `spec_status`、聚合生成与 `policy_version` 锁定、唯一键冲突、内容项/输入源校验、档案 `school_id` 校验、学校 seed 幂等、密码/令牌哈希、分页边界 | 业务规则密度高，纯函数化后快速回归 | — |
| 集成 | Repository：`family_id` 隔离、`schools` 全局只读共享、任务+输入源+内容项+聚合单事务回滚、`ensure_group` 幂等、改归属日连锁（含挂接迁移回调 stub） | 家庭数据隔离与聚合一致性是安全/正确性基座 | — |
| API | 既有 REST（API-M001-001~017）+ 新增端点契约断言：200/201/204/400/401/403/404/409/422 | 契约冻结后防漂移 | — |
| 安全 | 未认证 401；跨家庭/越权 404 防探测；**双主体越权矩阵（student 仅本人）** | RISK-004 未成年人数据；家庭级隔离验收 | — |
| 并发/性能 | 不做压测 | 单家庭低并发（ASM-010） | V1 无并发需求 |
| E2E/浏览器 | 手工冒烟清单（见下） | 真实用户可操作性（验收口径） | 自动化浏览器测试价值/成本比低 |

## 既有基线（v0.1.2 实况，89 passed）

- [x] 注册/登录/登出、学校字典只读、学生档案 CRUD、任务 CRUD、状态机全路径、冻结规则、越权矩阵、事务回滚、日志审计
- [x] CR-001 容器化（多学科登记单 + group_no 结构校验）—— **随 v0.2.0 作废**，相关用例改由新用例替代
- [x] ACR-001 子账号 + 双主体隔离矩阵（**保留**）
- 执行摘要：`$ .venv/Scripts/python.exe -m pytest` → `89 passed`（每用例独立 SQLite tmp；双家庭 fixture familyA/familyB）

## 新增用例设计（v0.2.0，A10；③ 实施阶段落地）

### U 单元
- [ ] **归属边界 4 点**（验收剧本第 1 条）：`AT_DAY_CUTOFF=04:00` 下，9/9 20:00 与 9/10 03:00 → 均 `belong_date=2026-09-09`；9/10 04:00 → `09-10`；9/10 05:00 → `09-10`（含 cutoff 前 1 秒/整点/后 1 秒边界）
- [ ] **周次起算**：`AT_TERM_START` 为周三时，第 1 周 = 该周三 → 周日（半周），`week_index=1`；下一周周一 → `2`
- [ ] **周末聚合**：周五/周六/周日 `window_type=weekend`、同一 `group_key`；周一为独立 `day` 聚合（验收剧本第 2 条）
- [ ] **假期自然周**：`ts > AT_TERM_END` → `window_type=holiday`、`group_key=H:<周起始>.W1`
- [ ] **唯一键冲突**：同 `(student_id, category, belong_date)` 二次写入 → 归集（不新建）；并发 → 409/幂等
- [ ] **解析状态机**：`placeholder→parsed→confirmed` 合法；反向/跳过规则按契约断言

### I 集成
- [ ] **聚合生成幂等**：重复 `ensure_group` 不重复建聚合；追加内容项后 `policy_version` 不变
- [ ] **配置锁定按学生隔离**（验收剧本第 3 条）：小明周五已传（`policy_version=V1@04:00`）→ 周六改 `AT_DAY_CUTOFF=05:00` → 小明聚合仍 `V1`；小红（周五/周六未传）→ 按 `V2@05:00` 生成
- [ ] **纯浏览不锁**：仅 `GET /task-groups` 后 `policy_version` 不被写入/变更
- [ ] **改归属日连锁**：迁移 FK / 源聚合空则删 / 跨聚合迁移同步 `photo_subject_links`（stub 断言调用）/ 已被分析消费 → 409 / 审计记录
- [ ] **事务回滚**：任务+输入源+内容项+聚合写入中途失败 → 全部不存在

### A API
- [ ] 新增端点 4 个的契约断言（含隐式确认携带 digest、改归属日 409、聚合列表过滤与分页）
- [ ] 既有 007~010 修订后断言（输入源上传 201、详情无 `items`、更新不收归属字段）

### 链路 T AI 编排（Mock Provider）
- [ ] 解析成功 → `task_contents` 落库 + `spec_status=parsed`
- [ ] **降级**（Provider 超时/返回不合规）→ 保持 `placeholder` + 任务/输入源仍落库 + 返回降级提示（不阻断）

## 执行摘要（模板）

```text
$ .venv/Scripts/python.exe -m pytest
89 passed   # v0.1.2 实况（③ 实施完成后应 ≥ 89 + 新增用例数）
```

## 手工冒烟清单（真服务，验收口径）

```text
启动：cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
1. GET  /             → 200（前端静态托管生效）
2. 浏览器：菜单「任务」上传布置单照片/粘贴文本 → 查看解析草稿 → 确认
   → 菜单「作业」上传照片 → 挂接复核 → 完成分析（M002）
3. 观察后端日志：request_id 贯穿、task_created/parse_confirmed/group_ensured/audit 记录、无密码/token/敏感文本明文
```
