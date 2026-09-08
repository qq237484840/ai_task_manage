# M001 测试策略与结果 —— 作业任务管理

- **状态**：已执行（Task-001 交付：`54 passed`（8.08s，pytest）；真服务冒烟 GET / 与 /styles.css 均 200；手工 H5 冒烟清单见文末）
- **总体**：遵循 `AGENT_GUIDE.md` §6 DoD。本模块无 AI 调用 → **无 Mock Provider 测试需求**（本模块不产生 DATA-009）

## 测试分层与"为何需要/为何不需要"

| 层 | 覆盖 | 为何需要 | 为何不需要其他 |
| --- | --- | --- | --- |
| 单元 | 任务状态机（合法/非法边表驱动）、题目集校验（seq 连续、客观答案可选、主观禁答案）、档案 `school_id` 必填与存在性校验、学校 seed 幂等（重复执行结果一致）、密码/令牌哈希单向性与盐、分页边界 | 业务规则密度高，纯函数化后可快速回归 | — |
| 集成 | Repository：`family_id` 过滤隔离（A 家庭查不到 B 数据）、`schools` 全局只读共享（跨家庭可见同一字典、运行期无写方法）、任务+题目单事务（中途失败回滚）、索引行为 | 家庭数据隔离是安全基座，需在数据层验证；公共字典例外需显式断言 | — |
| API | 全部 REST（API-M001-001~012）契约断言：200/201/400/401/403/404/405/409/422 | 契约冻结后防漂移（DoD: API Test / Contract verified） | — |
| 安全 | 未认证 401；跨家庭访问学生/任务 403/404；参考答案 `include_answers` 越权拒绝；登出后 token 失效 | RISK-004 未成年人数据；家庭级隔离验收 | — |
| 并发/性能 | 不做压测 | 单家庭低并发（ASM-010） | V1 无并发需求；登录哈希为最重路径，在单测中验证参数与超时上限即可 |
| E2E/浏览器 | 手工冒烟清单（见下） | 真实用户可操作性（验收口径） | 自动化浏览器测试价值/成本比低，V1 用手工清单 |

## 测试清单执行结果（逐项对应验收断言）

- [x] 注册：成功 201；重复 login_name 409；弱密码 422
- [x] 登录：成功返回 token；错凭据 401；登出后原 token 401（含登录爆破锁定渐进退避）
- [x] 学校字典：GET /schools 登录后 200（stage/keyword 过滤正确）；未登录 401；无写路径（POST/PATCH/DELETE /schools → 404/405）；seed 幂等（独立空库 fixture 断言）
- [x] 学生档案：创建/列表/更新；`school_id` 缺失或不存在 → 422；跨家庭 student_id → 404/403
- [x] 任务创建：合法样例 201（draft）；题目集非法（空/seq 重复/主观题带答案）→ 422
- [x] 任务查询：列表分页倒序；详情 `include_answers` 归属校验（外部/内部语义分化）
- [x] 状态机：draft→publish→(mark_in_progress 幂等)→close→reopen→close 全路径成功；非法边 409（如 draft→close、未知 action）
- [x] 冻结：in_progress/closed 下 update_task → 409；draft/published 可改标题/题目（题目整体替换按 seq 规则校验）
- [x] 越权矩阵：未认证 401 / 异家庭 / 不存在三种情形响应语义正确（REST 对外 404 不泄露存在性；内部接口 403 PermissionDenied）
- [x] 事务：题目批量写中途失败 → 任务与题目均不存在（整单回滚）
- [x] 日志审计：登录取证、任务创建/状态变更有审计记录；日志不含密码/token/参考答案

## 执行摘要

```text
$ .venv/Scripts/python.exe -m pytest
54 passed, 1 warning in 8.08s        # warning 为 starlette.testclient 弃用提示，不影响断言
```

- 测试环境：`backend/.venv`（Python 3.12）；每用例独立 SQLite（tmp），双家庭 fixture（familyA/familyB）驱动越权矩阵；conftest 对 scrypt 降参加速登录用例
- 覆盖文件：unit ×3（seed/security/task_validation）、integration ×1（internal_services）、api ×5（family/schools/students/tasks/isolation）

## 手工冒烟清单（真服务，验收口径）

```text
启动：cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
1. GET  /             → 200（index.html，静态托管生效）
2. GET  /styles.css   → 200
3. 浏览器打开 http://localhost:8000：注册家庭 → 登录 → 建学生档案（学校下拉来自 GET /schools）
   → 建任务（多题含客观题答案）→ 发布 → 关闭 → 重新发布 → 关闭
4. 观察后端日志：request_id 贯穿、task_created/task_status_changed 审计记录、无密码/token/答案明文
```
