# PROJECT_STATUS —— 项目状态

> 维护：Project Master。每次阶段变更 / 里程碑 / 模块状态变化必须同步更新。
> 本文件是当前状态的权威源；历史沿革见 `CHANGELOG.md`。

更新日期：2026-09-10

## 当前版本

`v0.22.0`（**④ 验收收口 + `CHANGE-003` 关闭**：`Task-014`（AGENT-M002）**去替身复审**交付 → **PM 独立复现全部成立** —— ① **判别力（PM 亲手）**：`AT_AI_PROVIDER_MODE=real` + `AT_AI_ALLOW_MOCK_FALLBACK=false` 下两例边界用例 **`FF`（实测 `status='unassigned'` + `suggestions=[]`，断言立败，`RED_EXIT=1`）** → 还原默认 `auto` 后 **`....`（4 passed，`GREEN_EXIT=0`）= 真红真绿**；② **全量回归（PM 实测）**：`pytest --tb=no -q --junitxml` → **`tests=237 failures=0 errors=0 skipped=0`、`EXIT=0`**（与基线上限一致，未删减用例）；③ **浏览器级剧本 5**：`.e2e/browser_evidence.json` = **18 项全 `true` / 0 项 `false`**（3 张照片经真实 AI 通路产出建议 → UI 采纳入口 → 逐张采纳 6 次全 200 → 门控满足 → 生成草稿 `model:"mock-vision"` → 家长确认）；④ **写区双证**：两处声称改动文件 `git status --porcelain` 均为 **`??`（未跟踪写区）**、Forbidden 区 mtime **全部早于写区起点**（`mock.py` 20:15:47 / `task_parser.py` 20:11:26 / `BUG-003.md` 20:23:19 等）；⑤ **`TD-003` 死代码清理**：`list_groups` 的 `except TypeError` 垫片已删（改按 `M001 v0.2.0 Frozen` 契约直调），真机集成 10 例 + 上层 40+ 例 0 触发；⑥ 同文件 `getattr(...,None)+raise` **存在性探针**经 PM 裁决 **保留、不立 `TD-004`**（与签名兼容垫片语义不同）→ **`BUG-003` / `BUG-004` 均置 `Verified`** → **④ 判达成 → `CHANGE-003` 收口（Closed）**。**已知边界（不阻断）**：真实三方 AI 无密钥，全部 AI 通路证据为 **Mock Provider（`mock=True`，显著标注）**，非三方联调）

- **`v0.21.0` 基线**（**④ 验收已执行（`Task-011`，AGENT-M002）+ PM 独立复核 = 条件达成（不通过收口）+ 签发 `Task-012`/`Task-013` 修复 AI 通路缺陷** —— **PM 未采信自述，全部复现**：`pytest -q -rxX` → **exit 0 / 227 点（72+72+72+11）/ 2 xfail**（`BUG-003`/`BUG-004`）；`vue-tsc -p tsconfig.app.json` **TSC_EXIT=0**；`npm run build` **BUILD_EXIT=0**（`389 modules transformed`、`✓ built in 3.23s`）；**只读边界成立**（`git diff` 8 文件全属 `Task-006~010` 既有基线 + **mtime 审计 COUNT=0**，最新写入 18:02:38 / 17:55:15 均早于 ④ 起始）；**浏览器级证据采信**（`.e2e/acceptance.mjs`：Edge + `playwright-core` 驱动真实 uvicorn 托管的 `frontend/dist`，Network + 4 截图 + `browser_evidence.json` 66.6 KB）；**但 3 项缺口 → 不能收口**：① **`BUG-004`（高）** = M001 `default_parser` 以位置参数调用 keyword-only `parse_task_spec` → `TypeError` 被 `except Exception: pass` 静默吞掉 → **链路 T 核心 AI 解析不可达**（剧本 4 的 `parsed` 实为本地兜底）；② **`BUG-003`（中）** = `MockVisionProvider` 读 `candidate_subjects` 而 `AIService` 注入 `candidates` → **Mock 建议恒空**（剧本 5/6 的 AI 建议未发生，409 边界仅能经 M002 AI **端口替身**触达）；③ 真实三方**无密钥未覆盖**（已知边界，`ADR-011`）；两缺陷均经 **PM 读码逐字确认 → Confirmed**，派 **`Task-012`**（AGENT-M001）/ **`Task-013`**（AGENT-AI）并行修复，修复后由 **`Task-014`**（AGENT-M002）去替身复审 → 再判 ④）

- **`v0.20.0` 基线**（**`CR-004` 经用户批准 → Applied（M002 契约 v0.4.0 → v0.4.1）+ 签发 `Task-011`（阶段 ④ 验收 + 全系统回归）** —— `API-M002-007` 响应体以**运行实现为准**修订为 `{photo_id, status, suggestions:[LinkSuggestionItem]}`（`LinkSuggestionItem = {link_id, group_subject_id, subject|null, confidence|null, source, suggested_at}`）；**非破坏性**（不改 Method/Path/错误语义；端点状态保持 Active）；**PM 读码核实**（未采信 CR 描述）：`schemas.py`（`LinkSuggestionItemOut`/`LinkSuggestionOut`）+ `api/link_routes.py:31-65`（`retry` 缺省 `false`、`rejected_at IS NULL` 过滤、`subject` 解析失败 → `null`、`suggested_at = link.created_at`）→ 契约逐字对齐；**前端零返工、后端零代码改动**（本 CR 仅文档）；落地文档 9 处（`MODULE_API`/`MODULE_CHANGELOG`/`MODULE_CONTRACT`/`MODULE.md`/`MODULE_SUMMARY` + `API_REGISTRY`/`MODULE_REGISTRY` + `PROJECT_STATUS`/`CHANGELOG`/`INDEX`/`AGENT_REGISTRY`）；**`Task-011`（AGENT-M002）已签发并启动** = ④ **验收剧本 7 条**（含**浏览器级**）+ 全系统回归（域 A/B/C；Mock 必跑 / 真实三方双跑），**只读边界**（`backend/app/**`、`frontend/src/**` 零改动，缺陷只登记不修复））

- **`v0.19.0` 基线**（**④ 前置阻塞解除：`BUG-002` 修复交付并经 PM 复核 APPROVED → Verified、`Task-010` 关闭**：`DefaultM001Gateway.get_group_subject` 默认路径改走**契约内** `list_groups` 回填 group 上下文、**移除契约外消费**；`GET /photo-gates` 按真实 `group_key` 分桶、`409 gate_not_satisfied` **实测可达**、`API-M002-005` 的 `gate` 由 `null` → 真实 key；新增真机 `tests/integration/test_m002_gate_real_m001.py` **4 例**（弃 `FakeGateway` 桩、红→绿取证）；全量 `pytest` = **211 passed / 0 failed**；**M001 零改动 / 契约文本零改动 / 前端零改动**（diff + mtime 双重确认）；新增并启用 **`TD-001`**（全量扫描 N+1 放大）+ **`TD-002`**（契约未暴露 `window_task_id`/`task_status`）→ `docs/TECH_DEBT.md`；**`CHANGE-003` ③ 全部关闭 → ④ 验收可启动**）

- **`v0.18.0` 基线**（**③ 前端作业域完成 + 门控链路缺陷修复启动**：**`Task-009` 交付并经 PM 复核 APPROVED**（`vue-tsc -p tsconfig.app.json` **0 error** / `npm run build` **EXIT=0** / 前端 `associate`·`task_items` 命中 **0** / `backend/**` diff 为空）→ **`CHANGE-003` ③ 前端项关闭**；执行方 2 条 Request 处置 = **Request-1 → `CR-004`（Proposed，待用户批准）**、**Request-2 → `BUG-002` 已确认 + 签发 `Task-010`（AGENT-M002）修复**（根因 = M002 网关消费**契约外**且不含 group 上下文的 `get_group_subject` → `group_key` 恒空 → 门控单桶聚合、`409 gate_not_satisfied` 不可达；**M001 零改动、无需契约变更**）；**`Task-010` 为 ④ 验收必要前置**）

- **`v0.17.0` 基线**（**CR-003 ③ 实施收口 + 前端作业域任务签发**：**`Task-006` / `Task-007` / `Task-008` 三线交付并经 PM 复核 APPROVED**（横切 `app/core/ai/` 专属 39 例 / M001 实施 v0.2.0 / M002 实施 v0.4.0；`Task-002` 冻结段增量改接收口）；**`main.py` 启动期幂等自愈已接线**（`ensure_links_migration_hook_registered()`，实测自愈通过）；全量 `pytest` = **207 passed / 0 failed**；**`API-M001-018~021` / `API-M002-007~011` Draft → Active**（PM 实测路由）；治理回填 = `CONFIGURATION.md` §五（`AT_AI_*`）+ `DATA_MODEL.md` DATA-009 字段；签发 **`Task-009`**（AGENT-M002，前端「作业」域迁移）；④ 验收剧本 7 条**未启动**）

- **`v0.16.0` 基线**（**CR-003 ③ 实施阶段启动**：**契约定稿 = M001 `v0.2.0` Frozen / M002 `v0.4.0` Frozen（用户批准 2026-09-10）**；签发 **`Task-007`**（AGENT-M001，M001 实施：事实层按天 → 归属引擎 `WindowResolver` → 聚合层 → 链路 T）与 **`Task-008`**（AGENT-M002，M002 实施：入口 `kind` → N:N 挂接 → 逐张复核 → 窗口级门控 → 完成分析；**Task-002 冻结段增量改接**）；**`Task-006`**（AGENT-AI，横切 `app/core/ai/`）**并行可启动**；`CHANGE-003` §4 DoD 契约项已勾选）
- **`v0.15.0` 基线**（**CR-003 ② 契约修订评审完成**：`Task-004`（M001 → v0.2.0 草案）与 `Task-005`（M002 → v0.4.0 草案）交付并经 PM 复核 APPROVED（两任务关闭）；**API ID 已由 PM 分配登记** = `API-M001-018~021` / `API-M002-007~011`（Draft）；**`DATA_MODEL` 字段级已同步**（DATA-001/003 修订）；③ 实施可启动）
- **`v0.14.0` 基线**：**V1 范围收窄与横切 AI 层执行方定案**（`CHANGE-003` §6 阻塞项 **Q1~Q4 经用户逐项拍板并关闭** → **ADR-014 Accepted**：**M003/M004 职责并入 M001/M002**（Module ID 保留、状态 → Deferred）；**M005/M006/M007 与 `REQ-005`~`REQ-007` → Deferred（后置 V2）**；横切 `app/core/ai/` 执行方 = 新增 **`AGENT-AI`**（Task-006）；**Task-002 = 部分冻结 + 定稿后增量改接**；**V1 范围唯一清单 = `CLARIFICATION` §4.1 必做 10 项；验收 = §5 剧本 7 条**）
- **`v0.13.0` 基线**：**需求澄清定稿：作业任务语义重构 + 归属与判定双层模型**（**CR-003 Approved** + **ADR-013 Accepted**：**事实层按天** + **聚合层跨天**，**挂接与判定落聚合层**；**ADR-010 判定粒度 Superseded**；`task_items` 逐题建模**废弃**；新增 **DATA-012~018**；V1 必做 10 项 / 不做 6 项 / 验收剧本 7 条，权威源 `docs/requirements/CLARIFICATION-2026-09-10.md`）

- **验收阻塞缺陷已修复（2026-09-10，`BUG-001`）**：任务列表页空筛选（`?status=&student_id=`）→ **422**。修复 = `http.ts` 拦截器统一剔除空值 query（覆盖全部列表页）+ `TaskListView.vue` 停止回填空串枚举、补 `catch`/`toastError`；**同类隐患一并补齐**（`TaskEditorView.vue` onMounted 补 `catch`）；验证 = `vue-tsc` 通过 + 接口对照 422→200
- **门控链路缺陷已确认（2026-09-10，`BUG-002`）**：`GET /photo-gates` 无法按窗口分组（`group_key` 恒空 → 单桶聚合）+ `POST /completion-analyses` 门控前置失效（`409 gate_not_satisfied` 不可达）。根因 = M002 网关消费 M001 **契约外**且无 group 上下文的 `get_group_subject`（`TaskGroupSubjectDTO` 不含 `group_key`/`window_type`/`student_id`）；由 `Task-009` 真机前端联调暴露（单测用 `FakeGateway` 桩未覆盖）。修复 = **`Task-010`**（M002 侧消费适配，**M001 零改动**）；前端 `localGate` 仅展示层兜底，**不构成强制**
- **CR-003 变更执行（2026-09-10 同日）**：① **需求落库已完成** = 新增 `REQ-010`（承载新语义）+ `REQ-001`~`REQ-007` 精校 + 配置登记 `docs/CONFIGURATION.md` + `BUG-001` 修复；① **边界决议已完成** = `ADR-014`（V1 范围收窄 + 横切层执行方）+ PD-026~029 + 治理总表同步；② **契约修订评审已完成（2026-09-10）** = 立项 `CHANGE-003`（Executing）+ `Task-004`（M001 → v0.2.0）/`Task-005`（M002 → v0.4.0）**交付并经 PM 复核 APPROVED（两任务关闭）+ 用户批准 Frozen** + `Task-006`（AGENT-AI → `app/core/ai/`）**可启动**；**API ID 分配登记 + `DATA_MODEL` 字段级同步**；③ **实施已签发（2026-09-10）= `Task-007`（M001）/ `Task-008`（M002）**；治理总表（`MODULE_REGISTRY`/`ROADMAP`/`API_REGISTRY`/`RISK_REGISTER`/`AGENT_REGISTRY`/`ARCHITECTURE`/`SYSTEM_SUMMARY`）已同步
- **v0.12.0 基线（2026-09-08）**：前端技术栈切换立项（ADR-012：Vue3 + Vite + TypeScript + Vant 4，PD-025）+ CHANGE-002（Executing）+ Task-003 签发（AGENT-M001）；Task-002（AGENT-M002）后端编码并行、前端 UI 段后移接轨新栈

## 当前阶段

**Phase 4 —— CR-003 变更执行（2026-09-10）**：需求澄清定稿（**CR-003 Approved + ADR-013 Accepted**：事实层按天 + 聚合层跨天，**挂接与判定落聚合层**）→ ① **需求落库 / 配置登记 / 缺陷修复 / 边界决议均已完成**（**`ADR-014` Accepted**，`CHANGE-003` §6 Q1~Q4 全部关闭）→ ② **契约修订评审已完成**（**Task-004**：M001 → v0.2.0；**Task-005**：M002 → v0.4.0；**均交付并经 PM 复核 APPROVED（2026-09-10），两任务关闭**；API ID 已分配登记、`DATA_MODEL` 字段级已同步）→ **契约定稿 = M001 v0.2.0 / M002 v0.4.0 Frozen（用户批准 2026-09-10）** → ③ **后端 + 横切实施已收口（2026-09-10）**（**`Task-006`** 横切 AI 层 / **`Task-007`** M001 / **`Task-008`** M002 三线交付并经 **PM 复核 APPROVED**；`Task-002` 冻结段增量改接收口；207 passed）→ ③ **前端已完成**（**`Task-009`**，AGENT-M002，**PM 复核 APPROVED 2026-09-10** → `CHANGE-003` ③ 前端项**关闭**）→ ③ **门控链路缺陷修复已完成**（**`Task-010`**，AGENT-M002，`BUG-002` → **Verified**，PM 复核 APPROVED 2026-09-10）→ **③ 全部收口（前端 + 后端修复）** → ④ **验收已执行（`Task-011`）+ PM 独立复核 = 条件达成（不通过收口）**：主流程 / 回归 / 前端 DoD / 只读边界全部成立，但 **`BUG-004`（高，AI 解析通路不可达）** 与 **`BUG-003`（中，Mock 建议恒空）** 使剧本 4/5 的 **AI 语义未达成** → 签发 **`Task-012`**（修复 `BUG-004`）/ **`Task-013`**（修复 `BUG-003`）并行（**均已 PM 复核成立 = `Fixed`**）→ **④ 收口 = `Task-014`（AGENT-M002）去替身复审完成**（移除 `m002_ai_port` 端口替身、边界用例改走 `app/core/ai` 真实装配路径、`TD-003` 垫片清理、剧本 4/5 + 浏览器级复跑）→ **PM 独立复核 = 成立**（亲手判别力红→绿、全量 237/0、浏览器 18/18、写区双证）→ **双 BUG 置 `Verified` → ④ 判达成 → `CHANGE-003` 收口（Closed）**。**无阻塞项**（Q1~Q4 已决议；契约已定稿且 **M002 已升至 v0.4.1（`CR-004` Applied）**；`TD-001`/`TD-002` 为后置技术债，不阻断；**已知边界 = 真实三方无密钥，AI 证据均为 Mock Provider 显著标注**）

> 前序阶段（Phase 3 —— M002 编码开发，2026-09-08，Task-002/Task-003 并行）随 CR-003 调整：**M002 契约 v0.3.0 冻结面被打开**，**Task-002 = 部分冻结 + 定稿后增量改接**（PD-029，`ADR-014` 决议 5）；主线按 `ROADMAP.md` 功能域 **A + B + C**（**域 D 后置 V2**）+ CR-003 双层模型执行

- 功能域主线（`ROADMAP.md`，CR-003 + `ADR-014` 口径）：**V1 = A 学生自主采集闭环 → B 家长复核确认闭环 → C 大模型挂接建议 + 聚合子任务级完成分析 + 家长兜底**（ADR-013 双层模型）；**D 综合评判 + 每日报告 → 后置 V2**（`ADR-014` 决议 2）；横切 = 真实三方 AI（需求⑤）+ **`app/core/ai/`（`AGENT-AI`/Task-006）** + MVC + 两级主体；**M001~M007 契约治理框架保留（V1 有效模块 = M001 + M002 + 共享/基础设施）**
- V1 需求基线：**REQ-001~010 全部登记 Approved**（REQ-010 随 CR-003 新增，2026-09-10；`REQ-001`~`REQ-007` 已按 CR-003 精校）；**`REQ-005`/`REQ-006`/`REQ-007` → Deferred（后置 V2，`ADR-014` 决议 2，需求单保留）**；REQ-001/009 随 M001 验收转 Done（M001 v0.1.2 落地）
- **M001（作业任务管理）= Stable（v0.1.2）**：契约 v0.1.1 Frozen + Task-001 实现（54 passed）经 PM DoD 验收 APPROVED；**CHANGE-001（CR-001 容器化/CR-002 内容级判定链/ACR-001 两级主体/ACR-002 判定与 Provider 重构）PM 复核 APPROVED（2026-09-08）→ Applied**（编码落地，测试 54→89，九件套与 DATA_MODEL/API_REGISTRY 同步定稿；API-M001-013~017 新增登记 Active）；**2026-09-10 随 CR-003 打开冻结面**（唯一键改 `(student_id, category, belong_date)`、`task_items` **废弃**、子任务上移聚合层），契约 **v0.2.0 Frozen（用户批准 2026-09-10）**；**实施 = `Task-007`**
- **M002（作业图片采集与归属）契约 v0.3.0 Frozen → 随 CR-003 修订为 v0.4.0 Frozen（用户批准 2026-09-10）**：归属由**段级 1:N** 放开为**照片 ↔ 聚合子任务 N:N**（`photo_subject_links`）+ **窗口级门控** + `completion_analyses`；上传入口分「任务/作业」、**作业上传不填任何内容**；**Task-002 = 部分冻结 + 定稿后增量改接**（PD-029：冻结「归属/挂接」段，允许收尾与 CR-003 无关段——质检/归一/受控存储/受控取图/双主体 API）；M001 依赖侧接口已就绪；代码注释「M003」漂移已清理（**仅注释**）
- **前端技术栈切换（2026-09-08，ADR-012/CHANGE-002/Task-003）**：前端统一 **Vue3 + Vite + TypeScript + Vant 4** 工程（零构建原生 H5 退役，FastAPI 托管 `dist/`，REST 契约零影响）；AGENT-M001 等价迁移 M001 现有 6 视图 + 托管切换；Task-002 前端基础 UI 后移接轨（后端并行不受阻）；**2026-09-10**：任务列表页 422 修复 + 同类 `try/finally` 隐患补齐，`vue-tsc` 通过
- 跨模块开放项：见下方"跨模块开放项"（v0.9.0 精校 + v0.11.0 关闭 O-8；**v0.12.0 关闭 O-6** = 前端统一工程承载；**2026-09-10（CR-003）**：O-1/O-2 口径更新、O-3/O-5 收敛关闭；**2026-09-10（ADR-014）**：**O-4 → 后置 V2**、O-9 → 归 `AGENT-AI`（Task-006））

## 已完成模块

| Module ID | 名称 | 状态 |
| --- | --- | --- |
| M001 | 作业任务管理 | Stable（**v0.1.2**：Task-001 PM DoD 验收 APPROVED + **CHANGE-001 Applied**（2026-09-08；API-M001-013~017 Active））；**随 CR-003 打开冻结面 → 契约 v0.2.0 Frozen（用户批准 2026-09-10）→ ③ 实施完成（2026-09-10，`Task-007`，PM 复核 APPROVED：事实层按天 + 归属引擎 + 聚合层 + 链路 T + 前端任务域）**；`BUG-004` 修复（`Task-012`）经 `Task-014` 复审 **Verified** |
| M002 | 作业图片采集与归属 | Stable（**契约 v0.4.1 Frozen**（`CR-004` Applied））；**③ 实施完成（`Task-008`，PM 复核 APPROVED：入口 `kind` + N:N 挂接 + 逐张复核 + 窗口级门控 + 完成分析）+ 前端「作业」域（`Task-009`）+ 门控链路修复（`Task-010`，`BUG-002` → Verified）；④ 验收收口（`Task-014` 去替身复审，`BUG-003` → Verified，2026-09-10）** |

（模块按 M001→M007 顺序开发与验收的规则**在 V1 内收窄为 M001 → M002**（`ADR-014`：M003~M007 已 Deferred）；前序未验收不进入下一模块仍适用）

## 开发中模块

| Module ID | 名称 | 状态 |
| --- | --- | --- |
| （无） | — | **M001 / M002 均已 Stable**（`CHANGE-003` ④ 验收于 2026-09-10 收口，`CHANGE-003` → Closed）；V2（M005~M007）为**后置**而非开发中 |

## 规划 / 后置模块（V1 不开发）

| Module ID | 名称 | 状态 |
| --- | --- | --- |
| M003 | AI 作业识别（链路 T 布置单解析 + 链路 H 挂接建议；逐题识别作废） | **Deferred**（**职责并入 M001 + M002 + `app/core/ai/`**，`ADR-014` 决议 1；Module ID 保留不撤销） |
| M004 | 作业任务匹配（**聚合子任务级**完成结论；逐题对齐作废） | **Deferred**（**职责并入 M002**，`ADR-014` 决议 1） |
| M005 | AI 作业质量评价（六维 + 综合分，输入随 CR-003 改聚合子任务级） | **Deferred（V2）**（`ADR-014` 决议 2；`REQ-005` Deferred） |
| M006 | AI 教师评价与改进建议（按聚合子任务组织） | **Deferred（V2）**（`ADR-014` 决议 2；`REQ-006` Deferred） |
| M007 | 今日作业综合报告（「今日」= 归属日，按聚合 / 周次组织） | **Deferred（V2）**（`ADR-014` 决议 2；`REQ-007` Deferred） |

> **共享 / 基础设施（非 Module ID）**：`app/core/ai/`（LLM 接入层，ADR-011/DATA-009）= **V1 实现**，执行方 **`AGENT-AI`**（Task-006，**可启动**；前置 = ② 评审 APPROVED **已于 2026-09-10 满足**）——见 `MODULE_REGISTRY.md` §共享基础设施。**与 `Task-007`/`Task-008` 并行**；M001/M002 实施期以 **Mock** 解阻（`ADR-011`），真实三方密钥联调为后续验收项。

## 受阻模块

（无。**原阻塞项 `CHANGE-003` §6 Q1~Q4 已于 2026-09-10 全部决议关闭**（`ADR-014` + PD-026~029）；M003~M007 不属 V1 范围，非"受阻"而是"后置"）

## 跨模块开放项（记录用，随模块契约轮关闭）

> 2026-09-08 M002 完整性审查产出；不引入新 ID 前缀，逐项在对应模块契约/变更中定稿（B3 授权登记待处理项）。

| # | 开放项 | 归属处理时机 | 关联 |
| --- | --- | --- | --- |
| O-1 | 照片**挂接建议**：AI 建议（照片 ↔ **聚合子任务 N:N** + 置信度）输出契约、`suggestion_json` 写入口、识别消费与锁定时机 | **M002 契约 v0.4.0（Task-005，链路 H）** | REQ-010、RISK-006 |
| O-2 | 无法挂接 / 低置信照片的兜底路径细化（suggested 队列、**逐张** accept/reject/改挂 UI 流与重拍引导） | M002 契约 v0.4.0（Task-005）+ 前端任务 | REQ-010、RISK-006 |
| O-3 | ~~识别/匹配题目粒度与版面结构对齐~~ **口径作废（CR-003）**：判定粒度改为**聚合子任务（学科）级**，逐题对齐不再要求 | **已随 CR-003 / ADR-013 收敛**（无独立待办） | ADR-010 → ADR-013、ASM-011 |
| O-4 | **聚合子任务**评分与报告口径（判定单元 = `task_group_subjects`；无法判断 / 低置信降级 = 家长复核） | **后置 V2**（M005/M007 契约轮随 V2 回归；口径更新 = ADR-013 聚合子任务级结论 + M005 AI 评判为核 + M007 报告草稿→复核定稿）—— `ADR-014` 决议 2 | ADR-013、ADR-014、REQ-008 |
| O-5 | ~~"今日报告"时间窗与任务归属语义~~ **已随之界定（CR-003）**：归属日（凌晨 4 点日界）+ 周次分组 + 周末聚合；「今日」= 归属日 | **已收敛**；M007 报告组织形式随契约轮 | ADR-013、`CONFIGURATION.md` |
| O-6 | 两级主体前端体验（学生登录/会话切换、家长代传路径、兜底入口） | **已关闭（2026-09-08，ADR-012）**：前端统一 Vue 工程承载——Task-003 迁移 M001 页面，M002（Task-002）及后续模块 UI 以新栈组件实现；O-2 兜底 UI 流随 M002 前端段 | ADR-009/ADR-012 |
| O-7 | REQ-004~008 详情页"待确认点"残留精校（与各自模块契约轮同步） | 各模块契约轮（REQ-001~007 随 CR-002 精校内容级口径） | — |
| O-8 | `DATA_MODEL.md`/`INDEX.md` 字段级同步统一执行 | **已完成（2026-09-08）**：DATA_MODEL DATA-001/002 字段级同步、M001 九件套回填、INDEX 随 v0.11.0 更新 | 防二次漂移 |
| O-9 | 真实三方 Provider 选型与接入登记（模型/密钥/限额/超时重试降级）、照片出域三方合规口径 | **已批准（ACR-002/ADR-011）** → 由 **`AGENT-AI`（Task-006）** 落地 `app/core/ai/`；配置项由 PM 登记 `CONFIGURATION.md`、外部系统登记 `EXTERNAL_SYSTEMS.md` | ADR-011、ADR-014、RISK-004 |

## 已知风险

见 `RISK_REGISTER.md`（**RISK-001~012**）：RISK-001 已关闭（技术栈已定 ADR-004）；RISK-002 随 ADR-010 降级（参考答案录入负担消除）、RISK-003/004/006/007/008 Mitigating/Open；**RISK-006（照片挂接误判与兜底负担）扩展至聚合子任务级判定异议复核、RISK-007（学生子账号）Mitigating、RISK-008（真实三方依赖）Open、RISK-009（照片出域三方合规）Open**（2026-09-08 新增）；**2026-09-10（CR-003）新增 RISK-010（聚合层一致性）/ RISK-011（LLM 输出不合规），RISK-003/006 口径更新；2026-09-10（ADR-014）新增 `RISK-012`（V1 收窄后 M005~M007 的 V2 回归成本与"综合评定"主题交付面收窄），RISK-005（范围蔓延）因显式收窄而缓解。**

## 技术债务

（无，登记见 `TECH_DEBT.md`，首条记录时创建）

## 待决决策（Pending Decisions）

> **2026-09-10 边界决议注（ADR-014 / PD-026~029）**：`CHANGE-003` §6 阻塞项经用户逐项拍板关闭 —— PD-026（M003/M004 吸收、M005~M007 Deferred）/ PD-027（`REQ-005`~`REQ-007` 后置 V2）/ PD-028（横切 `app/core/ai/` → `AGENT-AI`）/ PD-029（Task-002 部分冻结）；PD-001「7 模块闭环」口径随 ADR-014 收窄为「M001 + M002 + 共享/基础设施」（**ADR-002 仍适用**：不新增业务模块、不提前实现 V2+）。

> **2026-09-10 语义修订注（CR-003 / ADR-013）**：`PD-014`（任务 = 多学科作业登记单容器 + `group_no`）/ `PD-018`（内容级逐题对齐）/ `PD-021` / `PD-022`（端到端逐题直判）口径**已被 CR-003 / ADR-013 覆盖**（判定粒度 → **聚合子任务级**，`task_items` 废弃）；`PD-015`（先采后认）/ `PD-017`（布置单识别）/ `PD-023`（六维 + AI 评判为核）/ `PD-024`（草稿→复核定稿）**保留**，粒度口径随之修订。权威源 = `docs/requirements/CLARIFICATION-2026-09-10.md`；下表保留历史记录，不再逐条回改。

| 编号 | 决策 | 影响 | 状态 | 决定者 |
| --- | --- | --- | --- | --- |
| PD-001 | V1 范围与开发顺序（7 模块闭环） | 已按需求指令固化（ADR-002） | 确认（用户） | 用户 |
| PD-002 | 领域划分 | V1 规模不建 Domain 层 | 关闭 | Project Master |
| PD-003 | 技术栈与平台形态：移动优先 H5 + FastAPI + SQLite 单体 | 决定 M001 起全部设计与编码 | **Confirmed**（ADR-004） | 用户 + PM |
| PD-004 | 用户与身份模型：纯家庭模式（家庭账号 + 学生档案） | DATA-002 收敛，全部 API 鉴权 = 家庭级过滤（**扩展：ADR-009 两级主体**） | **Confirmed**（ADR-005 + ADR-009/PD-016） | 用户 + PM |
| PD-005 | 正确度判定：分科混合策略（客观题对照参考答案/主观题不判对错） | M001 建模与 M005 评分算法 | **Confirmed → 被 PD-018/PD-021/PD-022 取代**（ADR-006 → Superseded by ADR-010，2026-09-08） | 用户 + PM |
| PD-006 | AI Provider：抽象 + Mock 先行（真实三方后补实现类） | "真实可运行"验证无外部依赖阻塞 | **Confirmed → 被 PD-019 取代**（ADR-007 → Superseded by ADR-011，2026-09-08） | 用户 + PM |
| PD-007 | 部署环境与存储 | 单机/局域网 + SQLite + 本地图片目录（ASM-010） | **Confirmed**（2026-09-08，ASM-010） | 用户 |
| PD-008 | 学科/作业类型范围与"无法判断"落地 | 小学语数英书面作业起步 + 标记→复核/重拍（ASM-011） | **Confirmed**（2026-09-08，ASM-011） | 用户 |
| PD-009 | 学校基础资料形态（M001 开发增补） | 全局共享只读字典（seed 预置、后台维护暂缓）+ 学生档案 `school_id` 必填 | **Confirmed**（2026-09-08，ADR-008/REQ-009） | 用户 + PM |
| PD-010 | M002 图片质量检测策略（D1） | **本地规则先行**：可解释启发式 + 阈值配置化 + 规则版本化；`QualityChecker` 协议预留 Vision 接入位 | **Confirmed**（2026-09-08，M002 v0.1/v0.2） | 用户 + PM |
| PD-011 | M002 图片预处理边界（D2） | **仅轻量归一**：EXIF 方向归一 + 统一 JPEG + 长边上限；矫正/增强归 M003 | **Confirmed**（2026-09-08，M002 v0.1/v0.2） | 用户 + PM |
| PD-012 | M002 ~~提交建模与状态触发（D3）~~ | **v0.2.0 取代**：触发点改为"首次照片 assigned 到任务"（见 PD-015）；D4 不入库+逐图报告保留 | **Confirmed→被 PD-015 取代**（2026-09-08） | 用户 + PM |
| PD-013 | M002 不合格图片处理（D4） | **不入库 + 逐图报告**：不留文件/行/状态，`422 image_quality_rejected` 逐项原因引导重拍 | **Confirmed**（2026-09-08） | 用户 + PM |
| PD-014 | 任务粒度重构（R1） | task = **多学科作业登记单容器** + `task_items.group_no` 学科作业段；学科卡 = `(subject, group_no)`；题目可录参考答案（ADR-006 保留）；照片最终**单归属**到学科作业段 | **Confirmed**（2026-09-08，→ `CR-001` **Approved**） | 用户 + PM |
| PD-015 | 先采后认采集与归属（R2 + D5~D8） | 上传批次不预选任务/学科 → `unassigned`；AI 建议 `suggested`；家长/学生确认 `assigned`/`rejected`；首次 assigned 触发任务 `mark_in_progress`（幂等）；~~完成程度=学科作业段照片覆盖二值化~~（**v0.3.0 移除**，完成程度以内容级判定为准）；D5 数量上限（批 50/任务 200）、D6 服务端页序、D7 未消费可撤销、D8 串行化+409 | **Confirmed**（2026-09-08；归属语义保留，随 CR-002/CR-001 落地 M002 v0.3.0） | 用户 + PM |
| PD-016 | 两级主体身份（R3） | **家庭账号（家长：全家+兜底）+ 学生子账号**（完整登录、仅本人）；学生自主登记/拍照、家长兜底；ADR-009 Accepted | **Confirmed**（2026-09-08，ADR-009 + `ACR-001` **Approved**） | 用户 + PM |
| PD-017 | 布置登记录入方式（g1） | **拍照识别为主**：拍黑板/记事本/布置页 → 大模型识别"今日作业清单（学科+条目）"草稿 → 学生/家长确认补正后生效为登记单；M003 增"布置单识别"AI 环节 | **Confirmed**（2026-09-08，→ CR-002/ACR-002） | 用户 + PM |
| PD-018 | 匹配与评判粒度（g2） | **内容级**：布置精确到题；匹配=照片内容↔布置题逐题对齐判完成/对错；大模型综合评分；重开 ADR-006 | **Confirmed**（2026-09-08，→ ADR-010 + CR-002） | 用户 + PM |
| PD-019 | AI Provider 默认运行（g3/需求⑤） | **真实三方默认**：Provider 抽象下 OCR/Vision/LLM 真实三方为默认实现，Mock 降级测试桩/离线降级；部署需联网；配置密钥/模型/限额 | **Confirmed**（2026-09-08，→ ADR-011 + ACR-002 + ASM-010 修订） | 用户 + PM |
| PD-020 | 主线组织（g4） | **按功能域重排**：保留 M001~M007 代码组织与契约治理；主线/里程碑 = 功能域 A~D（A 学生自主采集→B 家长复核确认→C 大模型匹配+兜底→D 综合评判+报告），ROADMAP v0.9.0 | **Confirmed**（2026-09-08，`ROADMAP.md`） | 用户 + PM |
| PD-021 | 判定基准来源（q2-1） | **模型端到端直接判**：不维护参考答案字段；大模型综合题干+作答判对错并给可观察依据（数学可验算/语文可比对原文），低置信入复核 | **Confirmed**（2026-09-08，→ ADR-010/CR-002） | 用户 + PM |
| PD-022 | 主观题判定（q2-2） | **主客观全判**：主观题也由大模型逐题判对错（全面重开 ADR-003/006 边界），以可观察证据+依据+置信度对冲误判；不武断底线保留 | **Confirmed**（2026-09-08，→ ADR-010） | 用户 + PM |
| PD-023 | M005 评分架构（q2-3） | **保留六维但 AI 评判为核**：逐题完成/对错结论 + 大模型综合评判（六维质量+综合分）基于识别/匹配证据出具；权重仍配置化；M007 聚合成稿 | **Confirmed**（2026-09-08，→ CR-002） | 用户 + PM |
| PD-024 | 报告定稿流程（q2-4） | **草稿→家长复核定稿**：大模型生草稿 → 家长复核（低置信/无法判断/对错异议逐项过）→ 确认定稿归档（保留草稿与复核记录） | **Confirmed**（2026-09-08，→ CR-002） | 用户 + PM |
| PD-025 | 前端技术栈统一（2026-09-08 用户技术方案变更） | **Vue3 + Vite + TypeScript + Vant 4** 工程化（替代零构建原生 H5）；Vue Router hash + axios 错误映射 + Pinia；FastAPI 托管 `dist/`（单进程形态不变）；M001 页面迁移 + Task-002 起全部前端 UI 按新栈 | **Confirmed**（2026-09-08，→ ADR-012/CHANGE-002/Task-003） | 用户 + PM |
| PD-026 | **M003~M007 的 V1 职责边界**（`CHANGE-003` §6 Q1） | **M003/M004 职责并入 M001（链路 T）/ M002（链路 H）**（Module ID 保留不撤销，状态 → **Deferred**）；**M005~M007 → Deferred（V2）** | **Confirmed**（2026-09-10 用户拍板，→ **ADR-014** 决议 1） | 用户 + PM |
| PD-027 | **`REQ-005`~`REQ-007` 是否 V1 必做**（§6 Q2） | **全部后置 V2**（状态 → Deferred，需求单保留不作废）；**V1 范围 = `CLARIFICATION` §4.1 必做 10 项；验收 = §5 剧本 7 条** | **Confirmed**（2026-09-10 用户拍板，→ **ADR-014** 决议 2） | 用户 + PM |
| PD-028 | **横切 `app/core/ai/` 执行方**（§6 Q3） | **新增 `AGENT-AI`（Task-006）**，写区仅 `backend/app/core/ai/**`，不设业务 Module ID；启动前置 = ② 评审 APPROVED | **Confirmed**（2026-09-10 用户拍板，→ **ADR-014** 决议 3） | 用户 + PM |
| PD-029 | **Task-002 去留**（§6 Q4） | **部分冻结 + 定稿后增量改接**（冻结「归属/挂接」段；返工面限归属段） | **Confirmed**（2026-09-10 用户拍板，→ **ADR-014** 决议 5） | 用户 + PM |

## 下一步行动

1. ~~用户批准 M001 契约草案 v0.1.1~~ → **已完成（2026-09-08）**：Contract/API/Data 基线冻结（Frozen）
2. ~~PM 签发 Task-001 并验收~~ → **已完成（2026-09-08）**：AGENT-M001 实现 M001（54 passed）；PM DoD 验收 **APPROVED**（M001 → Stable）
3. ~~用户 grill 定稿主线重排~~ → **已完成落库**：ROADMAP.md v0.9.0 + PD-017~024 + ADR-010/011（Proposed）+ ACR-002/CR-002（Open）
4. ~~用户审阅批准包~~ → **已完成（2026-09-08，四项全部批准）**：`CR-001`/`ACR-001`/`CR-002`/`ACR-002` → Approved；ADR-010/011 → Accepted（ADR-006/007 Superseded 生效）；CR-001 条款随 ADR-010 口径修订；ADR-010 引用勘误
5. ~~M002 契约草案 v0.3.0 批准~~ → **已完成（2026-09-08）**：用户批准签署区 → M002 **Frozen v0.3.0**；Task-002 签发（AGENT-M002 Active）
6. ~~M001 合并 CHANGE 执行~~ → **已完成（2026-09-08）**：CHANGE-001 PM 复核 APPROVED → Applied；M001 定稿 **v0.1.2**（89 测试全绿）；API-M001-013~017 登记；DATA_MODEL/Registry 同步
7. ~~M002 编码（Task-002）→ 前端技术栈切换（Task-003）~~ → **随 CR-003 调整**：M002 契约冻结面打开，实施改按 **CHANGE-003** 路径执行；**Task-002 = 部分冻结 + 定稿后增量改接**（PD-029）
8. ~~阶段 ② 契约修订评审~~ → **已完成（2026-09-10）**：`Task-004`（M001 → v0.2.0）与 `Task-005`（M002 → v0.4.0）交付并经 **PM 复核 APPROVED（两任务关闭）+ 用户批准 Frozen**；API ID 已分配登记（`API-M001-018~021` / `API-M002-007~011`，Draft）；`DATA_MODEL` 字段级已同步
9. ~~阻塞：`CHANGE-003` §6 Q1/Q2/Q3/Q4~~ → **已完成（2026-09-10）**：用户逐项拍板 → **PD-026~029 + `ADR-014`（Accepted）**，治理总表（`MODULE_REGISTRY`/`AGENT_REGISTRY`/`REQUIREMENTS`/`ROADMAP`/`CHANGE-003`）已同步；`Task-006`（AGENT-AI）已签发（**转可启动**）
10. ~~阶段 ③ 实施~~ → **已完成（2026-09-10，PM 复核 APPROVED）**：**`Task-007`（M001）** 事实层按天 → 归属引擎 `WindowResolver` → 聚合层 → 链路 T + **前端任务域**；**`Task-008`（M002）** 入口 `kind` → N:N 挂接 → 逐张复核 → 窗口级门控 → 完成分析（`Task-002` 冻结段增量改接收口）；**`Task-006`（横切 `app/core/ai/`）** Provider/Mock + prompt 版本化 + schema 拦截 + 降级 + `ai_call_records`；`main.py` 启动期幂等自愈接线；全量 **207 passed / 0 failed**；`API-M001-018~021` / `API-M002-007~011` → **Active**；`CONFIGURATION.md` §五 + `DATA_MODEL.md` DATA-009 已回填
11. ~~`Task-009` 前端「作业」域迁移~~ → **已完成（PM 复核 APPROVED，2026-09-10）**：交付 8 文件（含新增 `components/PhotoCard.vue`）；PM 复验 `vue-tsc -p tsconfig.app.json` **0 error** + `npm run build` **EXIT=0** + `associate` / `task_items` 命中 **0** + `backend/**` diff 为空；`CHANGE-003` ③ 前端项**关闭**
12. ~~`Task-010` 门控链路缺陷修复（`BUG-002`）~~ → **已完成（PM 复核 APPROVED，2026-09-10；`BUG-002` → Verified）**：改走契约内 `list_groups` 回填 group 上下文、移除契约外消费；**真机 M001↔M002 集成用例 4 例**（弃桩，红→绿）；全量 `pytest` **211 passed / 0 failed**；`gate_service.py` 未改（未放宽门控）
13. ~~`CR-004`（Proposed）~~ → **已完成（用户批准 2026-09-10 → Applied；M002 契约 v0.4.0 → v0.4.1）**：`API-M002-007` 响应体以运行实现为准修订为 `{photo_id, status, suggestions[]}`（**仅文档**；前端零返工、后端零代码改动）
14. ~~`Task-011`（阶段 ④ 验收）~~ → **已完成（PM 复核 2026-09-10）**：7 条剧本取证（剧本 7 **浏览器级**通过）+ 回归 `pytest` **227 passed / 0 failed** + `vue-tsc` **0 error** + `npm run build` **EXIT=0** + 只读边界成立（diff + **mtime 双重确认**）；**PM 裁决 = ④ 条件达成（不通过收口）**，缺口 = `BUG-004`（高）/ `BUG-003`（中）/ 真实三方无密钥（已知边界）
15. ~~`Task-012`/`Task-013` 修复 + `Task-014` 去替身复审~~ → **已完成（2026-09-10，PM 复核成立）**：`Task-012`（AGENT-M001，`BUG-004`：关键字传参 + `SourceInput` 转换 + 降级 `logger.warning` + `ai_call_records` 真跑取证）与 `Task-013`（AGENT-AI，`BUG-003`：Mock 读 key 对齐 `candidates` + `Task-013-D1` API 面补证）**均收口 = `Fixed`**；**`Task-014`（AGENT-M002）去替身复审**：移除 `m002_ai_port` 端口替身（0 引用）、边界 2 例 + 剧本 4/5 走 `app/core/ai` 真实装配路径、`TD-003` `except TypeError` 垫片删除（死代码证明）、浏览器级剧本 5 **18/18 PASS**、全量 **237 tests / 0 failed**；**PM 亲手判别力复现**（关 Mock 兜底 → `FF`/`RED_EXIT=1`；还原 → 4 passed/`GREEN_EXIT=0`）→ **`BUG-003`/`BUG-004` → Verified → ④ 判达成 → `CHANGE-003` 关闭**
16. **下一步（V1 收尾 / 非本 CHANGE）**：V1 剩余交付 = 真实三方 AI Provider 密钥联调（`ADR-011` 已知边界，需外部密钥）+ `TD-001`（N+1）/ `TD-002`（契约未暴露 `window_task_id`/`task_status`）按需排期；**V2 回归**：M005~M007 + `REQ-005`~`REQ-007` 恢复 Approved 状态、重评估 `ADR-014` 并走 CR/变更流程后启动（`RISK-012`）
16. **V2 回归（不属当前阶段）**：M005~M007 + `REQ-005`~`REQ-007` 恢复 Approved 状态、重评估 `ADR-014` 并走 CR/变更流程后启动（`RISK-012`）
