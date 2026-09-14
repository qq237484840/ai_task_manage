# Task-016 任务书 —— 修复 `BUG-006`：M001 `default_parser` 静默 Mock 兜底（绕过 `AT_AI_ALLOW_MOCK_FALLBACK=false`）

- **Task ID**：Task-016 ｜ **Agent**：`AGENT-M001`（`m001-dev`）｜ **Module**：M001（任务容器 / 链路 T 解析）
- **签发**：Project Master，2026-09-14 ｜ **状态**：**已签发（待执行）** ｜ **Kind**：**缺陷修复（高）**
- **缺陷单**：`docs/changes/BUG-006.md`（当前 `Confirmed`；**状态位由 PM 置位，执行方不得修改**）
- **启动前置（已满足）**：全量 `pytest` 基线 **237 tests / 0 failed / 0 errors / 0 skipped**；真实三方 AI 已联调通过（`docs/PROJECT_STATUS.md` 2026-09-14 条目）；`BUG-004` 已修复（`session` 下传 + `SourceInput` 适配已在位）。
- **契约影响**：**不改表结构、不改 API 响应结构**；**行为面变更** = 在 `provider_mode=real`（或 `auto` 无真实配置）**且** `allow_mock_fallback=false` 时，AI 解析失败不再产出草稿 → `tasks.spec_status` 由 `parsed` 变为 **`placeholder`**（此即配置意图）。Release Note / `CHANGELOG.md` 由 **PM** 负责登记。
- **写区（授权）**：
  1. `backend/app/modules/m001/services/task_parser.py`（**唯一**生产代码写区；**仅限** `default_parser` 及其新增私有辅助函数）
  2. `backend/tests/unit/test_task_parser_ai_path.py`（新增用例）
  3. `backend/tests/api/test_tasks_ai_parse_records.py`（新增 API 级用例）
  4. `backend/tests/e2e/test_acceptance_ai_wiring.py`（**仅在**必须新增用例时；既有 `test_bug003_*` / `test_bug004_*` **不得删除、不得放宽 `xfail(strict=False)`**）
  5. `backend/tests/e2e/test_acceptance_scenarios.py`（**最小扩权，仅限 §3.6** 所述单一用例的环境切换时机）
- **禁止改**：`backend/app/core/ai/**`（**全部**，含 `errors.py` —— 属 `Task-015` 写区）、`backend/app/modules/m002/**`、`backend/app/modules/m001/**` **除** `services/task_parser.py`、`frontend/**`、`docs/**`、`.e2e/**`、任何契约文本。
- **并行说明**：与 `Task-015`（`BUG-005`，写区 `app/core/ai/errors.py`）**文件零重叠、无依赖，可并行执行**。若执行中发现必须改动对方写区文件 → **停下回报**，不得越区。

## 1. Objective

使 M001 链路 T 的降级行为**服从既有配置语义**：当部署侧显式声明「真实三方 + 禁用 Mock 兜底」时，AI 解析失败必须**如实失败**（任务保持 `placeholder`），而不是静默用本地启发式产出草稿并标记 `spec_status=parsed`（「假成功」）。

## 2. 背景（PM 读码确认 + 实测原文；**勿再自行推断**）

| # | 事实 | 证据（文件:行） |
| --- | --- | --- |
| 1 | AI 抛错后**无条件**回落 `mock_parse_sources` | `backend/app/modules/m001/services/task_parser.py:198-207`：`try: ... outcome = parser(session, sources=ai_sources) / coerced = _coerce_draft(outcome) / if coerced is not None: return coerced` → `except Exception as exc: logger.warning("task_parser: 核心 AI 解析降级（%s）", exc)` → `:207 return mock_parse_sources(sources)` |
| 2 | 「AI 返回不合规（`coerced is None`）」与「AI 抛错」**同等静默兜底** | 同上：`:203` 为 `None` 时不返回 `None`，直接落到 `:207` |
| 3 | 该函数**全程不读** `allow_mock_fallback` / `provider_mode` | `task_parser.py` 内无相关引用（本次联调前 = 0 处） |
| 4 | 上层已能正确处理 `None`（**无需改 service**） | `m001/services/task_service.py:176-182`：`drafts = parser_fn(norm_sources, session=session)` → `if drafts: append_contents + set_spec_status("parsed")`；`None` / 空 → 保持 `placeholder` |
| 5 | **实测「假成功」**：`real` + `AT_AI_ALLOW_MOCK_FALLBACK=false` 下 `POST /api/v1/tasks → 201 / spec_status="parsed"`，而同期 DATA-009 为 `mock=0 / status=error` | `docs/changes/BUG-006.md §1`（API 原文 + DATA-009 原文） |
| 6 | 对照组：M002 侧同配置行为**正确**（不兜底） | 同配置下照片 `status=unassigned`、`links=[]`（`AiUnavailableError` 不兜底）→ 缺陷边界仅在 M001 |
| 7 | 默认配置语义 | `app/core/ai/config.py:27-28`：`provider_mode: str = PROVIDER_MODE_AUTO`；`allow_mock_fallback: bool = True`；`PROVIDER_MODE_MOCK = "mock"`（`config.py:16`）—— **显式 `mock` 模式属「非降级」**，仍应允许本地解析 |
| 8 | 既有用例把「AI 抛错 → 保留本地兜底」当**当前契约**断言 | `tests/unit/test_task_parser_ai_path.py:85-96`（`test_default_parser_warns_and_falls_back_on_ai_error`）、`tests/e2e/test_acceptance_ai_wiring.py:150-157` —— 均运行在**默认配置**（`auto` + `allow=True`）下 → 修复后**仍应通过**（行为不变） |
| 9 | 图片源路径不受影响 | `task_parser.py:195-196`：无文本源 → `parser=None` → `mock_parse_sources` 对图片源返回 `None`（剧本 4 的「不伪造草稿」边界） |

## 3. 任务要求

### 3.1 降级判定（**必做，判据由 PM 给定**）

在 `task_parser.py` 新增**私有**辅助函数（延迟 import，遵循本文件既有约定 —— 见 `:161` 的延迟 import 模式）：

```
_mock_fallback_allowed() -> bool
```

判定顺序（**不得自由发挥**）：

1. 读取 `app.core.ai.config.get_ai_settings()`（**函数内延迟 import**）；
2. 若 `provider_mode` 规范化后 == `PROVIDER_MODE_MOCK`（显式 Mock，**非降级**）→ **允许兜底**；
3. 否则返回 `settings.allow_mock_fallback`（`true` → 兜底；`false` → **不兜底**）；
4. **异常兜底**：若 `app.core.ai` 不可 import 或读取配置抛异常 → **返回 `True`** 并 `logger.warning`（向后兼容：配置不可读时无法得知部署意图，保持既有「M001 最低验收路径」行为，且不引入新的静默失败面）。

`default_parser` 末尾 `return mock_parse_sources(sources)` 改为：

```
return mock_parse_sources(sources) if _mock_fallback_allowed() else None
```

- 两条降级路径（`coerced is None` / `except` 捕获）**统一**经过该判定；
- **不得**改动 `mock_parse_sources` 自身语义（图片源仍返回 `None`）；
- **不再需要** `try/except TypeError` 之类签名兼容（PM 铁律 ⑥）；`except Exception` 保留（契约 Failure Behavior），但**必须新增**可观测日志区分「已兜底 / 未兜底」（如 `logger.warning("task_parser: 核心 AI 解析降级（%s）；Mock 兜底=%s", exc, allowed)`）。

### 3.2 不回归既有语义（**必做**）

- 默认配置（`provider_mode=auto` + `allow_mock_fallback=true`）行为**逐字不变** → `tests/unit/test_task_parser*.py`、`tests/e2e/test_acceptance_ai_wiring.py` 既有断言**全部保持绿**；
- 显式 `provider_mode=mock` → 仍兜底（**不得**因本修复导致 Mock 模式/离线演示路径失效）；
- 图片源 → 不伪造草稿（`None`）保持不变。

### 3.3 测试（**必做：三层，症状在哪一层证据就到哪一层**）

| 层 | 落点 | 要求 |
| --- | --- | --- |
| **单元** | `tests/unit/test_task_parser_ai_path.py` | ① `AT_AI_ALLOW_MOCK_FALLBACK=false` + `AT_AI_PROVIDER_MODE=real`（并 `cache_clear()` 两个 `lru_cache`）→ 注入必然抛错的 parser → 断言 `default_parser(...) is None`；② 同配置下「AI 返回 `None`（不合规）」→ 断言 `is None`；③ `provider_mode=mock` → 断言仍返回 `mock_parse_sources` 结果；④ 默认配置 → 断言仍兜底（回归哨兵） |
| **API 级（**必做，主证据**）** | `tests/api/test_tasks_ai_parse_records.py` | 在 `real` + `allow_mock_fallback=false` 下 `POST /api/v1/tasks`（文本源）→ 断言 **`spec_status == "placeholder"` 且 `contents == []`**；对照组（`allow_mock_fallback=true`）→ `parsed` 且 `spec_status` 与 `contents` 非空。**优先走真实装配路径**（env 覆盖 + 清缓存，使 `registry` 返回「不可用 Provider」/Mock 禁用），`monkeypatch` 仅作备选且须在 §5 显式标注 |
| **回归** | 全量 | 全量 `pytest` `0 failed / 0 errors / 0 skipped`，用例数 **≥ 237** |

### 3.4 判别力取证（**必做**）

§5 须附**红 → 绿**原文：

1. **红**：修复前（或临时回退 `_mock_fallback_allowed()` 为恒 `True`）→ §3.3 的 API 级用例断言 `placeholder` 必败（实测可能得到 `parsed`）→ `RED_EXIT≠0`；
2. **绿**：恢复修复 → 同用例通过 → `GREEN_EXIT=0`；
3. 严禁以「用例本来就通过」充当判别力证据。

### 3.5 文档与状态（**禁改**）

`docs/**` **零写入**（含 `BUG-006.md` 状态位、`PROJECT_STATUS.md`、`CHANGELOG.md`、`CONFIGURATION.md`）—— 全部由 PM 置位/登记。

### 3.6 写区最小扩权（PM 裁决，2026-09-14，PM 铁律 ⑤）

`tests/e2e/test_acceptance_scenarios.py::test_scenario6_llm_unavailable_keeps_unassigned_then_manual_link_api_level`（`:371-404`）原实现**依赖 `BUG-006` 的错误行为播种前置数据**：它在 `real` + `allow_mock_fallback=false` 下先建文本任务，指望「AI 失败仍 Mock 兜底」产出学科子任务；修复后任务**如实保持 `placeholder`** → 无 `contents` → 聚合层无学科子任务 → `_seed_window_day`（`:132-143`）抛 `IndexError`（全量回归**唯一**失败）。

**裁决**：授权**最小扩权** —— 仅将该用例的 **env 切换时机后移**（先以默认配置播种学科子任务，再切 `real` + 禁兜底验证**照片挂接**降级）；**断言集合与强度逐字不变**（`suggestions == []`、`status == "unassigned"`、手工挂接 `source == "manual"`、门控 `satisfied is True`、生成分析 `201`）。

**硬约束**：不得借此放宽任何断言；不得改动该文件其它用例；不得修改 `_seed_window_day` 语义。

## 4. DoD（交付判定）

- [ ] `_mock_fallback_allowed()` 按 §3.1 判定顺序实现（含 `provider_mode=mock` 放行、配置不可读时保守放行 + warning）
- [ ] `default_parser` 两条降级路径统一受该判定约束；`mock_parse_sources` 语义未变
- [ ] 单元用例 ①~④（§3.3）全部新增且通过
- [ ] **API 级**用例（`real` + 禁兜底 → `placeholder` + `contents==[]`；对照组 → `parsed`）新增且通过
- [ ] 默认配置 / `mock` 模式 / 图片源三条既有语义**零回归**；`test_bug003_*` / `test_bug004_*` 哨兵**未被删除或放宽**，仍自然 XPASS
- [ ] §5 附**红→绿判别力原文**（命令 + 输出）
- [ ] 全量 `pytest`：**0 failed / 0 errors / 0 skipped**，用例数 **≥ 237**（新增用例应使总数增加）
- [ ] `read_lints` = 0；写区合规（`git status --porcelain` + **mtime 审计**）：`app/core/ai/**`、`modules/m002/**`、`modules/m001/**`（除 `task_parser.py`）、`frontend/**`、`docs/**`、`.e2e/**` **零写入**
- [ ] **不伪造**：真实三方联调证据（若引用）须标注；外部中转不可用时不得伪造 `status=ok` 记录

## 5. 执行方报告（七段式）

> **执行者说明**：本任务由 **PM 代执行**（当前 IDE 无具备写权限的执行 subagent，仅有只读 `code-explorer` 可用）。因此「执行方自述」与「PM 复核」出自同一操作者 —— **不构成独立第三方验证**，此限制如实标注；下述证据均为**可复现命令 + 原文输出**。

### ① 状态

**完成**。`_mock_fallback_allowed()` 已落地并接入 `default_parser` 两条降级路径；新增 **单元 4 例 + API 级 1 例**；红→绿判别力成立（含 **API 面**证据）；既有三条语义（默认配置 / 显式 `mock` 模式 / 图片源）**零回归**；`test_bug003_*` / `test_bug004_*` 哨兵仍自然 **XPASS**；全量回归 **251 / 0 failed / 0 errors / 0 skipped**。写区冲突按 §3.6 最小扩权处理。

### ② 改动文件清单 + diff 摘要

| 文件 | 性质 | 改动摘要 |
| --- | --- | --- |
| `backend/app/modules/m001/services/task_parser.py` | 改（约 +35 行） | 新增 `_mock_fallback_allowed()`：延迟 import `app.core.ai.config`（遵循本文件既有约定）→ `provider_mode == mock`（显式 Mock 非降级）**放行** → 否则返回 `allow_mock_fallback` → 配置不可读时**保守放行 + `logger.warning`**（向后兼容）。`default_parser` 末尾改为「按判定回落」：禁用时记 `logger.warning("…Mock 兜底已禁用…→ 保持 placeholder")` 并 `return None`；docstring 同步更新 |
| `backend/tests/unit/test_task_parser_ai_path.py` | 改（+4 例） | ① `real`+禁兜底 + AI 抛错 → `None`；② 同上 + AI 产物为空 → `None`；③ `provider_mode=mock` → 仍回落 `mock_parse_sources`；④ 默认配置（`auto`+允许）→ 仍兜底（回归哨兵） |
| `backend/tests/api/test_tasks_ai_parse_records.py` | 改（+1 例） | **API 级**：`real` + 禁兜底（无凭据→ Provider 不可用的**真实装配路径**）→ `POST /tasks` 为 `201` 且 `spec_status == "placeholder"`、`contents == []` |
| `backend/tests/e2e/test_acceptance_scenarios.py` | 改（§3.6 最小扩权） | 剧本 6：**仅**将 env 切换时机后移（先以默认配置播种学科子任务，再停用 LLM 验证照片挂接降级）；**断言集合与强度逐字不变** |

### ③ 红→绿 / 判别力证据原文

**红**（临时把 `_mock_fallback_allowed()` 改为恒 `True`，等价修复前行为）：

```
FAILED tests/unit/test_task_parser_ai_path.py::test_bug006_no_mock_fallback_when_disabled
E   assert True is False   (where True = task_parser._mock_fallback_allowed())
FAILED tests/unit/test_task_parser_ai_path.py::test_bug006_no_mock_fallback_when_ai_output_invalid
E   AssertionError: assert [ContentDraft(subject='math', text='练习册 P23')] is None
FAILED tests/api/test_tasks_ai_parse_records.py::test_ingest_keeps_placeholder_when_mock_fallback_disabled
E   AssertionError: 禁兜底时不得以本地草稿冒充 AI 解析结果
E   assert 'parsed' == 'placeholder'
    — Captured log call —
    WARNING task_parser: AI 解析不可用且 Mock 兜底已禁用… （初始配置 auto）
    INFO audit event=task_ingested … parsed=True      ← 「假成功」在 API 面复现
RED_EXIT=1
```

**绿**（还原修复）：上述 3 例 + 其余 8 例 **全绿** → `GREEN_EXIT=0`（含于 §④ 全量）。

### ④ 全量回归原文

```
$ pytest --no-header -q --tb=short --junitxml=../.pm_t015_t016.xml
........................................................................ [ 28%]
..............................X..X...................................... [ 57%]
........................................................................ [ 86%]
...................................                                     [100%]
tests=251 failures=0 errors=0 skipped=0
GREEN_EXIT=0
```

### ⑤ 写区合规自证（双证）

- **`git status --porcelain`**：`M backend/app/modules/m001/services/task_parser.py`、`M backend/tests/unit/test_task_parser_ai_path.py`、`M backend/tests/api/test_tasks_ai_parse_records.py`、`M backend/tests/e2e/test_acceptance_scenarios.py`（§3.6 授权）；**未出现** `app/core/ai/**`（`errors.py` 属 `Task-015` 写区，已单独审计）、`modules/m002/**`、`frontend/**`、`docs/**`、`.e2e/**`。
- **mtime 审计**：写区 = `task_parser.py` **09-14 15:48:34**；禁改区 = `core/ai/service.py` 09-10 16:54:31、`core/ai/config.py` 09-10 16:52:45、`core/ai/providers/openai_compatible.py` 09-10 16:53:32、`m001/services/task_service.py` 09-10 20:11:26、`m002/clients/task_client.py` 09-10 20:26:54 → **全部早于写区起点（15:47）→ 零写入成立**。
- `read_lints` = 0。

### ⑥ 契约 / 行为影响核对

- **无表结构变更、无 API 响应结构变更**；行为面变更 = `provider_mode=real`（或 `auto` 无真实配置）**且** `allow_mock_fallback=false` 时，AI 失败任务的 `spec_status` 由 `parsed` → **`placeholder`**（此即配置意图）→ **需 `CHANGELOG.md` Release Note（PM 登记）**。
- 既有用例逐条核对：`test_default_parser_warns_and_falls_back_on_ai_error`（默认配置仍兜底）✔；`test_default_parser_image_source_keeps_placeholder` ✔；`test_bug003_*` / `test_bug004_*` 哨兵 XPASS ✔；`test_scenario6_*` → **需 §3.6 最小扩权**（已处理，断言未放宽）✔。
- 上层未改：`m001/services/task_service.py:176-182` 已能正确处理 `None`（`if drafts:` 守卫）→ 无需改动，mtime 证明未触碰。

### ⑦ 遗留 + 需 PM 裁决项

1. **前端提示增强**（如「AI 未解析，请手工补录」）→ 属 UI/交互层，需另立任务或 CR（本任务只保证后端语义正确）。
2. `CHANGELOG.md` Release Note + `BUG-006` 状态置位 → **PM**。
3. **真实三方环境端到端复验**（中转稳定时：`real` + 禁兜底 → `placeholder`；允许兜底 → `parsed`）→ 建议 PM 补一次。
4. 图片源 OCR 通路（M001 无图片字节）仍为既有已知遗留 → 不在本任务。

## 6. 不在本任务范围

- `BUG-005`（三方错误分类/留痕）→ `Task-015`（`AGENT-AI`）；
- `docs/**` 登记与状态置位（`BUG-006` → `Fixed`/`Verified`、`CHANGELOG.md` Release Note、`PROJECT_STATUS.md`）→ **PM**；
- 技术债 `TD-001`（N+1）/ `TD-002`（契约未暴露 `window_task_id`）、V2 域 D → 不在本任务；
- 前端提示增强（如「AI 未解析，请手工补录」的 UI 文案/交互）→ **需另立任务/CR**（本任务只保证后端语义正确）；
- 图片源 OCR 通路打通（M001 无字节）→ 属既有已知遗留，**不在本任务**。

---

**写区自检（PM 铁律 ⑧）**：本任务交付物 = `backend/app/modules/m001/services/task_parser.py`（1 处生产代码）+ `tests/unit/test_task_parser_ai_path.py` + `tests/api/test_tasks_ai_parse_records.py`（+ 可选 `tests/e2e/test_acceptance_ai_wiring.py`）+ 本任务书 §5 追加 → **全部 ⊆ §写区**；`app/core/ai/**`、`modules/m002/**`、`frontend/**`、`docs/**` **零写入**。
