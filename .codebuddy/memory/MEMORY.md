# MEMORY —— 长期项目记忆

> 原则：`docs/` 为 Single Source of Truth。本文件只留**跨会话要点与指针**；执行流水/证据原文见 `.codebuddy/memory/YYYY-MM-DD.md`。

## 项目一句话

中小学生 AI 作业与学习成长综合评定系统 V1。**V1 有效模块 = M001 + M002 + 横切 `app/core/ai/`**（M003~M007 登记保留、**Deferred**，`ADR-014`）。形态：**FastAPI + SQLite 单体**（ADR-004）+ 移动优先 H5 **Vue3 + Vite + TS + Vant 4**（ADR-012，FastAPI 托管 `frontend/dist`）+ **两级主体** family/student（ADR-009/ACR-001：家庭级隔离 + 学生仅本人）+ **判定 = 聚合子任务(学科)级**（ADR-013）+ **真实三方 AI Provider 默认 / Mock 降级**（ADR-011）+ 学校字典全局只读 seed（ADR-008）。方法学：**文档驱动 + 多 Agent 治理**（ID 仅 Project Master 分配）。

## 当前状态（2026-09-10，顶层 v0.22.0）

- **`CHANGE-003`**：**已关闭（Closed，2026-09-10，PM 复核 APPROVED = ④ 判达成）**。路径 = `Task-011` 取证（条件达成，3 缺口）→ `Task-012`/`Task-013` 修复 AI 通路缺陷（均 `Fixed`）→ **`Task-014`（AGENT-M002）去替身复审**（移除 `m002_ai_port` 端口替身 + `TD-003` 垫片清理 + 剧本 4/5 真机 + 浏览器级 18/18 PASS）→ **PM 亲手判别力复现**（关兜底 → 边界 2 例 `FF`/`RED_EXIT=1`；还原 → 4 passed/`GREEN_EXIT=0`）+ 全量 237/0 + 写区双证 → 双 BUG 置 **Verified** → **④ 判达成 → CHANGE-003 关闭**。**V1 域 A/B/C 交付完成**；已知边界 = 真实三方 AI 无密钥（Mock 证据显著标注 `mock=True`，非三方联调）。
- **契约定稿**：M001 **v0.2.0 Frozen** ｜ M002 **v0.4.1 Frozen**（`CR-004` Applied：`API-M002-007` 响应体**以运行实现为准** = `{photo_id, status, suggestions[]}`；非破坏性、前端零返工、后端零代码改动）。
- **③ 交付清单（均 APPROVED）**：`Task-006` 横切 AI 层（Vision/OCR/LLM 三协议 + Mock/真实配置化 + prompt 版本化 + schema 校验拦截 + 超时重试降级 + 三能力接口 `parse_task_spec`/`suggest_photo_links`/`analyze_completion` + DATA-009 `ai_call_records`）｜`Task-007` M001 双层模型（`WindowResolver` 4 点切日/周次/周末合并 + `task_groups`/`task_group_subjects` 聚合 + 链路 T + 端点 018~021）｜`Task-008` M002 v0.4.0（入口 `kind` → N:N 挂接 → 逐张复核 → 窗口级门控 → 完成分析）｜`Task-009` 前端「作业」域（**路由 `path` 仍 `/photos`**、`name=homework`）｜`Task-010` `BUG-002` 修复 **Verified**（门控默认路径改走契约内 `list_groups`，弃 `FakeGateway` 桩，新增真机集成 4 例）。
- **实测基线**：全量 `pytest` = **237 tests / 0 failed / 0 errors / 0 skipped**（PM 实测 `--junitxml` + `EXIT=0`；`237 = 235 passed + 2 xpassed`，较 `Task-013` 首轮 236 增 1 = `Task-012` 新增用例；原 227 基线；**勿采信历史口述数字**）。缺陷双哨兵 `test_bug003_*` / `test_bug004_*`（`xfail(strict=False)`）**均已 XPASS**（回归即回落 xfailed）。
- **缺陷台账**：`BUG-001` 已修复 ｜ `BUG-002` **Verified** ｜ **`BUG-003` = Verified（`Task-013` 修复 + `Task-014` 去替身复审）**（`core/ai/providers/mock.py` 读 `candidate_subjects` → `candidates`，与 `service.py:197` 注入及 prompt `$candidates` 对齐；**PM 两次亲手红→绿**：① service 面回退键名 `4 failed/1 passed` → 还原全绿；② `Task-013-D1` API 面 `test_scenario5_*` 断言回退后 `F`（实测 `unassigned` + `suggestions == []`）→ 还原 `.`；**③ `Task-014` 判别力复核：关 Mock 兜底 → 边界 2 例 `FF`（实测 `unassigned` + `[]`，`RED_EXIT=1`）→ 还原 4 passed（`GREEN_EXIT=0`）**；2026-09-10 **Verified**）｜ **`BUG-004` = Verified（`Task-012` 修复 + `Task-014` 真实装配路径复审成立）**（keyword 调用 `parser(session, sources=...)` + `SourceInput` 适配（**只转发文本源**，图片源保持 `placeholder` 防伪造）+ `_coerce_draft` 支持 `ParsedContentItem` + `logger.warning` 可观测；`session` 经 `task_service.py:178` **单行**下传（PM 2026-09-10 裁决「采纳 A」/最小扩权）→ `ai_call_records` 落条；`xfail` 自然 **XPASS**；`BUG-004.md §7.1` 修复记录由执行方追加 + PM 复核认可（状态已置 **`Verified`**，`Task-014` 复审通过）；PM 已**更正**其 §5.8.1「`Task-013` 并发抖动」归因 —— 真因 = `get_ai_settings` + `get_ai_service` **双 `lru_cache` 跨用例泄漏**）。详见 `docs/changes/BUG-003.md §7.1`、`docs/agents/Task-012.md` §3.5、`Task-013.md §5`/§5D。
- **技术债**：`TD-001`（`get_group_subject` 全量扫描 N+1 放大）、`TD-002`（契约未暴露 `window_task_id`/`task_status`）；**`TD-003` → Closed**（`Task-014`：`clients/task_client.py` 的 `except TypeError` 签名兼容垫片删除，按 M001 v0.2.0 Frozen 契约直调；死代码证明 = 真机门控集成 10 例 + 上层 40+ 例 0 触发）；**PM 裁决不立 `TD-004`**（`getattr(...,None)+raise` 为存在性探针，与签名兼容垫片语义不同，不掩盖契约缺口）→ `docs/TECH_DEBT.md`；**无阻塞项**。
- 历史批次（v0.9.0~v0.20.0）明细见 `.codebuddy/memory/2026-09-08.md` 与 `2026-09-10.md`（含各轮 PM 裁决与证据原文）。

## 架构定稿要点（ADR-013）

- **双层模型**：**事实层按天**（`tasks` 唯一键 **`(student_id, category, belong_date)`**；`subject`/`content`/`task_items` 废弃停写）+ **聚合层跨天**（`task_groups` → `task_group_subjects` **★判定单元** → `photo_subject_links` **N:N** → `completion_analyses`）；**挂接与判定落聚合层**。
- **窗口语义**：日界 **凌晨 4 点**（`AT_DAY_CUTOFF`，`Asia/Shanghai`）；`week_index` = `AT_TERM_START` 所在周周一起算；**周五~周日合并「周末作业」**；每个 `belong_date` 至少一个聚合（最小 1 天）。
- **配置锁定**：变更只影响未聚合对象；已聚合按生成时 `policy_version`；锁定粒度 = 每个 `(学生, 聚合对象)`；**写入触发锁定，纯浏览不锁**；`belong_date` 上传即固化、不回算历史。
- **输入源**：图片 / 文本 / 聊天记录（只支持**粘贴文本**）；`kind` 由**菜单入口**决定（「任务」→ `task_spec`，「作业」→ `homework`）；作业上传**不填内容**。

## 用户偏好与稳定约定

- 中文文档、代码/API 标识符英文；README 只做入口；模块九件套按真实需要生成、勿建空模板；后端改动同步回填 docs 与测试。
- 单条需求详情入 `docs/requirements/`；需变更先 CR/ACR 登记；普通增量记 `CHANGELOG.md`；禁止知识重复；治理模板包 `ai-governance-template/` 改进须回同步并递增版本。
- 确认交互：一次 `ask_followup` ≤4 题、选项带推荐标注，用户逐项答复后落库。
- **PM 复核铁律**：不采信执行方自述 —— 须**可复现命令 + 原文输出**；「零改动」以 `git diff` + **mtime 审计**双证；用例真实性须**审读测试代码**（警惕 `FakeGateway` / 端口替身掩盖真机缺口）。
- **流程教训（`BUG-002`）**：跨模块消费链**至少一条真机集成用例**；**契约外接口不得作为唯一来源**，消费面须与 `MODULE_API.md` 内部服务接口表逐条对齐。
- **验收/复核铁律（v0.21.0 起累积）**：① 替身/桩**须在 docstring 显式标注并向 PM 报备**，PM 核验「证据是否经**真实装配路径**」；② `xfail` **不得删除或放宽**，修复后须自然 **XPASS**（**红→绿**取证，PM 应亲手复现）；③ 证据**逐条分域标注**（浏览器级 / API 级 / 服务级**不得混同**）；④ 「零改动」双证；⑤ **DoD × 写区冲突裁决判据**：先读码核实物理可行性 → 证据**可经真实生产路径获得**则**最小扩权**（限定文件/行/语义，写入任务书 §3.5 并附硬约束），否则降级口径并显式标注；⑥ 修复类任务**禁止用 `try/except TypeError` 兼容旧签名**（`BUG-004` 教训）；⑦ **症状在哪一层，证据就必须到哪一层**（症状在 API 面 → 仅 service 面证据不足）；⑧ 任务书**自检「交付物 ⊆ 写区」**（`Task-013` §5A/§8 冲突教训）。

## 关键索引

- 入口 `docs/INDEX.md`；状态 `docs/PROJECT_STATUS.md`（**v0.22.0**；M001/M002 均 **Stable**）；主线 `docs/ROADMAP.md`（**V1 域 = A+B+C 已交付完成（`CHANGE-003` Closed，2026-09-10），域 D 后置 V2**）。
- 权威源 `docs/requirements/CLARIFICATION-2026-09-10.md`；配置 `docs/CONFIGURATION.md`（`AT_*` + §五 `AT_AI_*` 全表）；数据 `docs/DATA_MODEL.md`（DATA-001/003 修订 + DATA-012~018；DATA-009 = 物理表 `ai_call_records`）。
- 决策 `docs/adr/ADR-001~014.md`（ADR-006/007/010 Superseded；关键 = ADR-013 双层模型、ADR-014 范围收窄 + AI 层执行方、ADR-011 AI Provider/Mock、ADR-012 前端栈）。
- 模块 `docs/MODULE_REGISTRY.md`（M001 v0.2.0 Frozen **Stable** / M002 **v0.4.1 Frozen Stable** / M003~M007 Deferred）；API `docs/API_REGISTRY.md`（`API-M001-018~021`、`API-M002-007~011` Active）。
- 变更 `docs/changes/`：CHANGE-001 Applied、CHANGE-002 Executing、**CHANGE-003 **Closed**（PM 复核 APPROVED = ④ 判达成，2026-09-10）**、`CR-004` **Applied**、`BUG-001` 已修复、`BUG-002` **Verified**、**`BUG-003` Verified**、**`BUG-004` Verified**；任务书 `docs/agents/Task-00x.md`（Task-006~011 已完成；**`Task-012`/`Task-013`/`Task-014` 均已完成（PM 复核成立，2026-09-10）**；**任务队列无 Active**）。
- 技术债 `docs/TECH_DEBT.md`（TD-001/TD-002；**TD-003 → Closed**；PM 裁决**不立 TD-004**）。

## 环境与实况备忘

- 后端 venv = `backend/.venv`（Python 3.12）；**pytest 基线 = 237**。代码基线：M001 v0.2.0、M002 v0.4.1、横切 `app/core/ai/` 均已实施。
- **浏览器级验收环境**（`Task-011` 固化）：`.e2e/`（`package.json` + `playwright-core`）+ 系统 Edge 通道（`channel: 'msedge'`）；种子 `.e2e/seed.py`（**会先删库重建** `backend/data/acceptance.db`）建独立库；**端口以脚本为准 = `8010`**（`.e2e/acceptance.mjs` 默认 `AT_BASE=http://127.0.0.1:8010`，非 8011 —— 2026-09-10 实机核对更正）。
- **验收 runbook（2026-09-10 实机预检通过，18/18）**：① `cd <root>; & backend/.venv/Scripts/python.exe .e2e/seed.py` → `SEED_OK`；② `cd backend; $env:AT_DATABASE_URL='sqlite:///./data/acceptance.db'; $env:AT_FRONTEND_DIR='<root>/frontend/dist'; uvicorn app.main:app --port 8010`（`GET /` 返回 dist 首页 200、`/api/v1/schools` 无 token 401 = 正常）；③ `$env:Path="C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2-2;"+$env:Path; node .e2e/acceptance.mjs` → `CHECKS total=18 pass=18 fail=0`、`EXIT=0`。**注意**：跑一次会重写 `.e2e/browser_evidence.json` 与 `shots/*.png`（已入库 → 会产生 4 条 `M`，需决定是否追加提交）；`node` **不在 PATH**，必须手动加。
- **端口 8000 被系统占用（2026-09-10 实况）**：`wslrelay.exe`（WSL 端口代理）常驻监听 8000 → 本地起 uvicorn/Vite dev 选 8000 会冲突，验收统一用 **8010**，dev proxy 指向 `127.0.0.1:8000`。
- **分层约束**：M001 **禁止 import M002**（实测 `grep -rn "modules.m002" backend/app/modules/m001` = 0）；跨模块唯一通道 = **回调注册**（`m001.services.aggregation_service.register_links_migration_hook`，M002 导入期注册；`main.py` 启动期 `ensure_links_migration_hook_registered()` 幂等自愈已接线）。
- **`tzdata` 已解决**：`backend/requirements.txt` 含 `tzdata>=2024.1`；`WindowResolver` 固定 UTC+8 回退保留为最后防线。
- 前端 `frontend/`：托管 = `backend/app/main.py` StaticFiles → `frontend/dist`（`core/config.py` `frontend_dir` 可覆盖）；dev = Vite proxy `/api/v1` → `127.0.0.1:8000`；**Vant 4 已全局注册**（`src/main.ts`）。
- **前端类型检查必须显式指定工程**：`npx vue-tsc --noEmit -p tsconfig.app.json; "EXIT=$LASTEXITCODE"`（走根 `tsconfig.json` 引用工程会漏检 `src/**`；PowerShell 管道会吞退出码）。Node 22.22.2 实机路径 = `C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2-2`（带 `-2` 后缀，PATH 需自加）。
- **git 跟踪现状**：`backend/app/core/ai/`、`backend/tests/e2e/`、`frontend/src/` 等**已在 2026-09-10 入库**（此后写区核验仍建议用 `git status --porcelain`）。**V1 基线入库提交** = `aed4db1`（「完成 V1 域 A/B/C 交付收口（CHANGE-003 关闭 / v0.22.0）」，208 files，+27892/−2814）+ `ce5057c`（刷新浏览器级验收证据）→ 工作区干净、领先 `origin/main` **4 commits**（**尚未 push**；推远端须用户显式指示）。
- **`.gitignore` 已加固（2026-09-10 收口体检）**：忽略 `.e2e/node_modules/`、`.e2e/*.xml`、`.e2e/seed_state.json`（此前 `.e2e/node_modules` **未被忽略**，误 `git add` 会引入 playwright-core 全量依赖）；`.e2e/shots/*.png` 与 `.e2e/browser_evidence.json` **保留为浏览器级证据**，故意不忽略。
