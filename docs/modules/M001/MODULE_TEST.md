# M001 测试策略与结果 —— 作业任务管理

- **状态**：已执行（Task-001 交付 `54 passed`；**CHANGE-001 后 `89 passed`**（2026-09-08，pytest）；真服务冒烟 GET / 与 /styles.css 均 200；手工 H5 冒烟清单见文末）
- **总体**：遵循 `AGENT_GUIDE.md` §6 DoD。本模块无 AI 调用 → **无 Mock Provider 测试需求**（本模块不产生 DATA-009）

## 测试分层与"为何需要/为何不需要"

| 层 | 覆盖 | 为何需要 | 为何不需要其他 |
| --- | --- | --- | --- |
| 单元 | 任务状态机（合法/非法边表驱动）、题目集校验（seq 连续、**CR-001 group_no 分组结构**、客观答案可选、主观禁答案）、档案 `school_id` 必填与存在性校验、学校 seed 幂等、密码/令牌哈希单向性与盐、分页边界 | 业务规则密度高，纯函数化后可快速回归 | — |
| 集成 | Repository：`family_id` 过滤隔离（A 家庭查不到 B 数据）、`schools` 全局只读共享、任务+题目单事务（中途失败回滚）、索引行为 | 家庭数据隔离是安全基座，需在数据层验证；公共字典例外需显式断言 | — |
| API | 全部 REST（API-M001-001~012 + ACR-001 新增）契约断言：200/201/400/401/403/404/405/409/422 | 契约冻结后防漂移（DoD: API Test / Contract verified） | — |
| 安全 | 未认证 401；跨家庭/越权 404 防探测；参考答案 `include_answers` 越权拒绝；登出后 token 失效；**双主体越权矩阵（student 仅本人）** | RISK-004 未成年人数据；家庭级隔离验收；ACR-001 两级主体验收 | — |
| 并发/性能 | 不做压测 | 单家庭低并发（ASM-010） | V1 无并发需求；登录哈希为最重路径，在单测中验证参数与超时上限即可 |
| E2E/浏览器 | 手工冒烟清单（见下） | 真实用户可操作性（验收口径） | 自动化浏览器测试价值/成本比低，V1 用手工清单 |

## 测试清单执行结果（逐项对应验收断言）

- [x] 注册：成功 201；重复 login_name 409；弱密码 422
- [x] 登录：成功返回 token；错凭据 401；登出后原 token 401（含登录爆破锁定渐进退避）
- [x] 学校字典：GET /schools 登录后 200（stage/keyword 过滤正确）；未登录 401；无写路径 → 404/405；seed 幂等
- [x] 学生档案：创建/列表/更新；`school_id` 缺失或不存在 → 422；跨家庭/他人 → 404
- [x] 任务创建：合法样例 201（draft）；题目集非法（空/seq 重复/主观题带答案）→ 422
- [x] 任务查询：列表分页倒序；详情 `include_answers` 归属校验
- [x] 状态机：draft→publish→(mark_in_progress 幂等)→close→reopen→close 全路径成功；非法边 409
- [x] 冻结：in_progress/closed 下 update_task → 409；draft/published 可改标题/题目
- [x] 越权矩阵（单主体）：未认证 401 / 异家庭 / 不存在三种情形语义正确（REST 对外 404；内部接口 403 PermissionDenied）
- [x] 事务：题目批量写中途失败 → 任务与题目均不存在（整单回滚）
- [x] 日志审计：登录取证、任务创建/状态变更有审计记录；日志不含密码/token/参考答案
- [x] **CR-001 容器化**：多学科登记单（subject NULL/'mixed' + (subject,group_no) 显式分段）201；分组结构违规（混 0/不连续/交错/段内科目不一）→ 422；旧单学科默认 0 段向后兼容
- [x] **ACR-001 子账号**：开通 201（弱口令带 password_warning）/重复与登录名占用 409/跨家庭 404/学生主体 403；停用/启用/改密后登录口径正确；disabled 登录 401；登出后 token 失效；family 与 student 登录名同名字命名空间互不干扰
- [x] **ACR-001 双主体隔离矩阵**：student 登录 → /students 仅本人、/student/me 返回本人档案、改他人档案/访问他人任务/给他人建任务 → 404、学生建档与子账号管理 → 403、本人任务 CRUD 与状态推进正常

## 执行摘要

```text
$ .venv/Scripts/python.exe -m pytest
89 passed in 12s   # CHANGE-001 后；无失败。warning 为 starlette.testclient 弃用提示，不影响断言
```

- 测试环境：`backend/.venv`（Python 3.12）；每用例独立 SQLite（tmp），双家庭 fixture（familyA/familyB）驱动越权矩阵；conftest 对 scrypt 降参加速登录用例
- 覆盖文件：unit ×3（seed/security/task_validation 含 CR-001 分组校验）、integration ×1（internal_services）、api ×7（family/schools/students/tasks/isolation/student_accounts/task_container）

## 手工冒烟清单（真服务，验收口径）

```text
启动：cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
1. GET  /             → 200（index.html，静态托管生效）
2. GET  /styles.css   → 200
3. 浏览器打开 http://localhost:8000：注册家庭 → 登录 → 建学生档案（学校下拉来自 GET /schools）
   → 建任务（多题含客观题答案）→ 发布 → 关闭 → 重新发布 → 关闭
4. 观察后端日志：request_id 贯穿、task_created/task_status_changed 审计记录、无密码/token/答案明文
```
