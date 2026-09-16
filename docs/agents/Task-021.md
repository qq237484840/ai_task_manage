# Task-021 任务书 —— `CR-005` 验收：跨模块真机 + 浏览器级 + 全量回归

- **Task ID**：Task-021 ｜ **Agent**：`AGENT-M002`（或 Project Master 直接验收）｜ **Module**：跨 M001/M002（验收）
- **签发**：Project Master，2026-09-16 ｜ **状态**：**已签发（待执行）** ｜ **Kind**：**验收（只读 + 证据，中）**
- **上游**：`CR-005`（Approved）；`Task-018`（M002 provider）、`Task-019`（M001 槽 + 端点）、`Task-020`（前端）**均须已完成**
- **契约影响**：无（验收不改契约；若发现契约缺口 → **只登记不修**，回报 PM）
- **写区（授权）**：`backend/tests/integration/**`（必要时新增跨模块真机用例）、`.e2e/**`（浏览器级脚本/产物）、`docs/agents/Task-021.md`（§5）
- **禁止改**：所有生产代码（`backend/app/**`、`frontend/src/**`）、其余 `docs/**` —— **只读验收**

## 1. Objective

按 `CR-005 §5` 的 8 条验收要求，用**可复现命令 + 原文输出**确认「图片源解析 + 重新解析」通路在**真实装配路径**下成立，且**防伪造**约束有效。

## 2. 验收清单（逐条取证）

| # | 项 | 要求 |
| --- | --- | --- |
| 1 | 纯图片布置单 → `POST /tasks/{id}/reparse` | **真实 Vision** 下产出学科+内容项草稿 → `spec_status=parsed`；DATA-009 `capability=task_spec_parse / mock=0 / status=ok`（**API 级 + 数据级证据**） |
| 2 | **防伪造**（判别力） | `provider_mode=mock`（或 vision degraded）→ 图片源**不转发** → `placeholder` + `contents==[]`；**移除判据 → 断言立败（红→绿原文）** |
| 3 | `confirmed` 任务 reparse | `409 spec_confirmed` |
| 4 | §2.4 三情形 | `placeholder` 写入 / `parsed` 整体替换 / **失败不清空**（各 1 例，API 级） |
| 5 | M002 provider 归属校验 | 跨家庭 `photo_id` → `None`（不得越权取图）——**服务级 + 用例级** |
| 6 | 全量回归 | `pytest` **0 failed / 0 errors / 0 skipped**，用例数 **≥ 251 + 新增**（给出 junit 摘要原文） |
| 7 | 前端 | `vue-tsc -p tsconfig.app.json` **0 error**；`npm run build` **EXIT=0** |
| 8 | **浏览器级** | 任务详情页「重新解析」可达：真实 Vision 下任务由 `placeholder` → `parsed` 且内容项出现在页面；失败分支提示如实（截图 + DOM 断言原文，**分域标注**） |

## 3. 证据纪律（PM 铁律）

- **症状在哪一层，证据就到哪一层**：本 CR 症状在 **API 面**（端点行为）→ 必须有 **API 级**证据；「防伪造」在 **服务/装配面** → 须有服务级或真机集成证据；
- 桩/替身**必须** docstring 标注并报备；核心结论（防伪造 / 归属校验）**不得**仅依赖桩；
- 真实三方不可用时**如实标注**（可降级为「Mock 通路 + 防伪造双证」并显式说明未取到真实证据），**不得**伪造 `mock=0` 记录；
- 浏览器级与 API 级证据**分域标注**，不得混同。

## 4. DoD

- [ ] §2 八条逐条取证完成（命令 + 原文输出）
- [ ] 防伪造具备**红→绿**判别力原文
- [ ] 写区合规（`git status --porcelain` + mtime）：**生产代码零写入**
- [ ] `read_lints` = 0
- [ ] §5 报告（含分域证据与遗留）；发现的问题**只登记**（`BUG-*`/`TD-*` 由 PM 分配 ID）并回报

## 5. 执行方报告（七段式）

> **执行者说明**：本任务由 **PM 代执行**（当前 IDE 无具备写权限的执行 subagent）；验收对象（`Task-018`/`019`/`020`）亦为 PM 代执行 → **不构成独立第三方验收**，限制如实标注。

### ① 状态

**完成**。§2 八条清单**全部通过**；新增服务级集成用例 2 例；全量回归 **267 / 0 / 0 / 0**；防伪造**红→绿**判别力成立；生产代码**零写入**（红取证期间临时改动已还原，`git diff` 为空）。

### ② 验收清单逐条结论（证据原文）

| # | 项 | 结论 | 证据原文 |
| --- | --- | --- | --- |
| 1 | 纯图片布置单 → 真实 Vision 产草稿 | **通过** | **真机（8010）**：`[② 本家图片源建任务] status=201 / spec_status=parsed / contents=4`：`math \| 练习册 P23 第1-10题`、`math \| 1. 12 x 4 = 48`、`math \| 2. 96 / 3 = 32`、`math \| 3. 7 + 8 = 15`；**DATA-009 原文**：`capability=task_spec_parse, model=qwen3.8-flash, status=ok, mock=0, latency_ms=16223` |
| 2 | 防伪造（判别力） | **通过（红→绿）** | 见 ③ |
| 3 | `confirmed` → `409` | **通过** | **真机**：`[③ confirmed→409] confirm=200 reparse=409 body={"code":"CONFLICT","message":"任务解析已确认（spec_confirmed）"}` |
| 4 | §2.4 三情形 | **通过** | `tests/api/test_task_reparse_api.py` 全绿：`test_reparse_from_placeholder_writes_contents_and_parses`（写入）/ `test_reparse_replaces_contents_when_parsed_unconfirmed`（**整体替换**）/ `test_reparse_failure_keeps_existing_contents`（**失败不清空**） |
| 5 | provider 归属校验（服务级 + 用例级） | **通过** | **服务级真机**：家庭 B 引用家庭 A 的 `photo_id` → `[① 跨家庭引用建任务] status=201 / spec_status=placeholder / contents=0`、`[① 跨家庭 reparse] status=200 / spec_status=placeholder / contents=0`（**不转发 = 不越权取图**）；**用例级**：新增 `tests/integration/test_cr005_image_source_service.py`（2 例，**真实 provider + 真实 `PhotoRepository`/`ImageStore`**）：跨家庭 → 观测桩 `sources` 中**无 `image`**；对照（本家）→ `sources == ['image']` 且 `image.path` 位于受控根内；另 `tests/unit/test_m002_task_source_image.py` 4 例（跨家庭 / 未知 / 文件缺失 → `None`） |
| 6 | 全量回归 | **通过** | `tests=267 failures=0 errors=0 skipped=0`、`GREEN_EXIT=0`（基线 265 + 本任务 2） |
| 7 | 前端 | **通过** | `TSC_EXIT=0`（`vue-tsc -p tsconfig.app.json`）、`BUILD_EXIT=0`（`npm run build`，`✓ built in 3.31s`） |
| 8 | 浏览器级（成功 + **失败**分支） | **通过** | **成功分支**（`Task-020`，真实 Vision）：7/7 PASS —— `placeholder` → 点「重新解析」→ `parsed`、toast「已解析出 6 项内容…」、页面「内容项（6）」与接口一致；**失败分支**（本次构造：`AT_AI_PROVIDER_MODE=mock` → 图片源不转发）：7/7 PASS —— `ingest → placeholder/0`、点击后 toast **「AI 未返回解析结果（可能暂时不可用或图片无法识别），可稍后重试或手工补录」**、接口仍 `placeholder/0`、页面「内容项（0）」（**未谎报**）；截图 `01_before/02_after/03_fail_before/04_fail_after`（临时产物，已清理） |

### ③ 防伪造红→绿原文

**红**（临时把 `task_parser.py:220` 的 `if not _vision_is_real(): continue` 改为 `if False:`）：

```
FAILED tests/api/test_task_reparse_api.py::test_no_forgery_when_vision_mock_even_if_provider_registered
E   AssertionError: Mock 下不得转发图片源（防伪造草稿）
E   assert 'parsed' == 'placeholder'
    - placeholder
    + parsed
    — Captured log call —
    INFO audit event=task_reparsed family=… parsed=True replaced=True spec_status=parsed
RED_EXIT=1
```

→ **Mock Vision 产出占位草稿并冒充解析结果**（`replaced=True`），即 `BUG-004` 教训的复现；**另 3 例仍 PASS**（含本任务新增的 2 例跨家庭用例）→ 证明其判别点独立（归属校验 ≠ 真实性判据）。

**绿**（还原判据）：聚焦 **16 passed / `EXIT=0`** → 全量 `GREEN_EXIT=0`。

### ④ 全量回归 + 前端构建

```
$ pytest --no-header -q --tb=short --junitxml=../.pm_t021.xml
..............................................                             [100%]
tests=267 failures=0 errors=0 skipped=0
GREEN_EXIT=0

$ npx vue-tsc --noEmit -p tsconfig.app.json   → TSC_EXIT=0
$ npm run build                              → ✓ built in 3.31s / BUILD_EXIT=0
```

### ⑤ 写区合规（只读证明）

- **`git status --porcelain`**：仅 `?? backend/tests/integration/test_cr005_image_source_service.py`（**写区内新增**）；**无** `backend/app/**`、`frontend/src/**`、其余 `docs/**` 条目。
- **生产代码零写入**：红取证期间的 `task_parser.py` 临时改动（`if False:`）**已还原**，`git status` / `git diff` 无该文件条目。
- **mtime**：`backend/app/**` 自 `Task-019` 提交（`76c6d30`）后未再写入。
- `read_lints` = 0。
- 临时资产（`.e2e/_tmp_t021_probe.py`、`_tmp_t021_fail.mjs`、截图 4 张、`backend/data/_tmp_t021.jpg`、`.pm_t021.xml`）**已全部删除**。

### ⑥ 证据分域标注

| 域 | 覆盖清单 | 说明 |
| --- | --- | --- |
| **API 面** | #1 #3 #4 #5(服务级) | 真机 8010（真实三方 AI）+ 测试 `TestClient` |
| **数据面** | #1 | DATA-009 `ai_call_records` 原文（`mock=0 / status=ok`） |
| **浏览器面**（DOM + 截图） | #8（成功 + 失败） | Edge + `playwright-core`，真实服务 |
| **用例面** | #2 #4 #5 | pytest（含 2 例新增服务级集成） |

**桩/替身披露（PM 铁律 ①）**：新增集成用例仅两处非生产路径 —— ① `task_parser._vision_is_real` 替换为恒 `True`（测试环境**无真实凭据**，该函数是「真实性开关」而非业务逻辑）；② 捕获 `sources` 的**观测桩** parser（记录入参、返回 `None`，不参与判定）。**核心结论（防伪造 / 归属校验）另有真机证据**（②-①/#1、#5 服务级），不依赖桩。

### ⑦ 登记项 + 需 PM 裁决项

1. **`TD-006`（新登记，PM 已分配 ID，2026-09-16）**：**M001 不校验图片源 `photo_id` 归属** —— 实测家庭 B 可建出引用家庭 A 照片的任务（`201`），防越权**仅由 M002 provider 一道**保证。当前**无越权读取路径**（M001 仅透传 `photo_id` 字符串、前端只显示 ID，实测跨家庭 `reparse` 全程无内容产出）→ **风险等级：低**（纵深防御建议：`ingest`/`reparse` 增归属预校验，或明确记录「唯一防线」设计决定）。**只登记不修**（`Task-021 §6`）。
2. **真实 Vision 波动观察**：本次 5 次真实调用 `mock=0 / status=ok`（`latency_ms` 7947–16562），未捕获失败；中转可用性仍间或波动 → 由既有「如实失败 + 重试」语义兜底。
3. **`CR-005` 建议置 `Applied`**（8 条验收全通过）；`API-M001-022` 已 `Active`。
4. **执行过程失误（如实记录）**：切 `mock` 模式构造失败分支时，用于校验 `.env` 改动的 PowerShell 命令**把全部 `AT_AI_*` 行打印到对话**（含三方 `sk-` 密钥）→ 密钥已出现在会话上下文中（`.env` 本身 `gitignore`，未入库）。**建议 PM/用户轮换该中转密钥**。后续同类操作**只打印目标行**（本次恢复 `real` 时已改为仅打印 `AT_AI_PROVIDER_MODE` / `AT_AI_ALLOW_MOCK_FALLBACK`）。
5. 环境已恢复：`.env` → `AT_AI_PROVIDER_MODE=real` + `AT_AI_ALLOW_MOCK_FALLBACK=false`；服务 8010 已重启（Health 200）。

## 6. 不在本任务范围

- 修复任何缺陷（只登记）；`CR-006`（A/B/C）；V2 域 D。
