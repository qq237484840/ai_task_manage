# Task-014 任务书 —— ④ 验收**去替身复审**（剧本 4/5 真机 AI 通路 + 垫片清理）

- **Task ID**：Task-014 ｜ **Agent**：`AGENT-M002`（`m002-dev`）｜ **Module**：M002（作业照片域）+ 验收资产
- **签发**：Project Master，2026-09-10 ｜ **状态**：**已完成并收口（PM 复核成立，2026-09-10；`BUG-003` → Verified、`CHANGE-003` → Closed）** ｜ **Kind**：**验收复审（去替身 / 去垫片，中）**
- **启动前置（已满足）**：`Task-012`（`BUG-004`）与 `Task-013`（`BUG-003`）**均已 PM 复核成立 = `Fixed`**；全量基线 **237 tests / 0 failed**；`CHANGE-003` ③ 已收口，**④ 仅剩本复审**。
- **契约影响**：**无**（仅测试资产、`TD-003` 死代码清理；契约文本、API 面、数据模型不变 → 不需 CR）。
- **写区（授权）**：`backend/tests/**`（含 `tests/e2e/**`、`tests/m002_support.py`）、**`backend/app/modules/m002/clients/task_client.py`（仅 `TD-003` 清理，见 §3.4）**、`.e2e/**`（浏览器级脚本/产物）。
- **禁止改**：`backend/app/core/ai/**`（`Task-013` 已收口）、`backend/app/modules/m001/**`、`backend/app/modules/m002/**` **除** `clients/task_client.py` 的 `TD-003` 定点清理、`frontend/**`、任何契约文本（M001/M002 `MODULE_API.md`）、**治理文档（含 `docs/changes/BUG-003.md` / `BUG-004.md` 状态位 —— 由 PM 置位）**，过程记录仅允许 `docs/agents/Task-014.md`。

## 1. Objective（目标）

把 ④ 验收证据中**仍依赖替身/垫片**的部分换成**真实生产通路**证据，使 `BUG-003` / `BUG-004` 的修复在**验收层**得到确认，从而满足 ④ 收口条件。

## 2. 背景（PM 读码确认，勿再自行推断）

| # | 事实 | 证据 |
| --- | --- | --- |
| 1 | 2 例边界用例经 **M002 AI 端口替身**触达「AI 建议（未确认挂接）」分支 | `tests/e2e/test_acceptance_scenarios.py::m002_ai_port`（`:70-83`）→ 注入 `MockAiClient` / `set_ai_client`；被 `test_boundary_gate_not_satisfied_409_api_level`（`:450`）、`test_boundary_analysis_confirmed_is_terminal_api_level`（`:475`）使用 |
| 2 | 该替身的**存在前提已消除** | 原 docstring 依据「Mock Provider 下 AI 不产出挂接建议（见 BUG-003）」；`BUG-003` 已修复并经 `Task-013` + `Task-013-D1` 复核 → Mock Provider 经**真实装配路径**产出建议（`test_scenario5_*` 已断言），409 门控**可由真实 AI 链路触达** |
| 3 | 剧本 4 的「AI 解析」原由**本地启发式兜底**产出 | `BUG-004`；`Task-012` 修复后链路 T 真跑核心 AI（`spec_status=parsed` + `ai_call_records` 落条），剧本 4 需在**无兜底误认**下复跑 |
| 4 | M002 网关存在**签名兼容垫片**（死代码） | `modules/m002/clients/task_client.py:213-216`：`except TypeError: # 兼容位置/少参签名` → `TD-003`（PM 于 `Task-012` 复核时登记） |

## 3. 任务要求

### 3.1 去替身：边界用例改走真实 AI 通路（**必做**）

1. **移除 `m002_ai_port` fixture**（含其 `MockAiClient` / `set_ai_client` 注入），使 `test_boundary_gate_not_satisfied_409_api_level`、`test_boundary_analysis_confirmed_is_terminal_api_level` 在 **无任何 AI 端口替身**下运行；两例的「AI 建议」必须由 **`app/core/ai` 真实装配路径**（Mock Provider 兜底）产出。
2. 用例内**新增显式断言**证明建议来自真实通路（例：`GET /photos/{id}/link-suggestions?retry=true` → `status == "suggested"` 且 `suggestions` 非空；必要时校验 `group_subject_id` 与播种一致）。
3. 文档字符串须标注：证据形态 = **真实 AI 通路（Mock Provider，`mock=True`）**，**非三方联调**；替身已移除（去替身复审结论）。

### 3.2 去替身审计（**必做**）

全仓审计验收资产中的替身/桩注入点，逐条列出（文件 / 位置 / 用途 / 处置）：

- `m002_ai_port`、`MockAiClient`、`set_ai_client`、以及 `tests/m002_support.py` 中的等价替身；
- 复核 `Task-010` 已弃用的 `FakeGateway` 是否有残留引用（`BUG-002` 教训：`grep -rn "FakeGateway" backend/` 须为 0 或说明）；
- **判据**：凡「替代真实装配路径以掩盖缺口」者一律移除；确需保留的桩**必须**在 docstring 标注 + 说明不可替代的物理原因（PM 铁律 ①）。

### 3.3 剧本 4 / 5 真实通路复跑（**必做**）

- **剧本 4**（`test_scenario4_task_entry_image_source_mock_parse_api_level`）：确认在 `BUG-004`/`BUG-003` 均修复后仍断言「图片源在 Mock 无视觉密钥 → `spec_status == "placeholder"` 且 `contents == []`（**不伪造草稿**）」；若其原注释/依据已过时，按**修复后事实**更新（不得放宽断言）。
- **剧本 5**（`test_scenario5_photo_link_gate_analysis_confirm_api_level`）：保持既有 API 面断言（`Task-013-D1` 已补），确认**手工挂接**流程未受影响。

### 3.4 `TD-003` 垫片清理（**必做，定点**）

- 删除 `modules/m002/clients/task_client.py` 中 `list_groups` 的 `except TypeError` 回落分支，按 **Frozen 契约**直调（参数形状与 `MODULE_API.md` 内部服务接口表逐字对齐）；
- 同文件若存在同类「签名容错」分支，**先回报再改**（不得擅自扩面）；
- 取证：真机集成用例（`tests/integration/test_m002_gate_real_m001.py`）在清理后仍全绿，证明回落分支为死代码。

### 3.5 浏览器级复跑（**必做**）

- 按 `Task-011` 既有环境（`.e2e/` + `playwright-core` + 系统 Edge 通道）复跑**剧本 5 端到端**：3 张作业照片 → **AI 挂接建议可见并自动填充** → 逐张确认挂接 → 门控满足 → 生成完成分析草稿 → 家长确认；
- 证据须为**浏览器级**（截图/日志原文），并与 API 级证据**分域标注**（不得混同）。

## 4. DoD（交付判定）

- [ ] `m002_ai_port` 替身已移除；上述 2 例边界用例在**无 AI 端口替身**下通过，且新增「建议来自真实通路」断言（含红→绿或等价判别力说明）
- [ ] 去替身审计清单完备（逐条：文件 / 用途 / 处置），`FakeGateway` 残留 = 0（或已说明）
- [ ] 剧本 4 / 剧本 5 **真实通路**复跑通过；剧本 4 的「不伪造草稿」边界断言未被放宽
- [ ] `TD-003` 清理完成 + `tests/integration/test_m002_gate_real_m001.py` 全绿（证明回落分支为死代码）
- [ ] **浏览器级**剧本 5 复跑通过（截图/日志原文），证据分域标注
- [ ] 全量 `pytest`：**0 failed**，用例数**不低于 237**（不得删减既有用例；如因去替身调整用例数，须说明增减明细）
- [ ] `read_lints` = 0；写区合规（`git status --porcelain` + **mtime 审计**；`app/core/ai/`、`modules/m001/**`、`frontend/**`、契约文本、`docs/changes/**` **零写入**）
- [ ] 过程记录：`docs/agents/Task-014.md` 追加「§5 复审过程与证据」（命令 + 原文输出 + 红→绿/判别力说明 + 证据分域）
- [ ] **不伪造**：若某项证据在当前环境**物理不可得**（无三方密钥、无浏览器环境等）→ **停下回报**并说明，不得以桩/替身冒充真机证据（PM 铁律 ①）

## 5. 复审过程与证据（执行方报告）

> 七段式汇总：① 状态 ｜ ② 改动文件清单 + diff 摘要 ｜ ③ 红→绿/判别力证据原文 ｜ ④ 全量回归原文 ｜ ⑤ 写区合规自证 ｜ ⑥ 去替身审计清单 ｜ ⑦ 遗留说明 + 需 PM 裁决项。

### ① 状态

- **去替身**：已移除 `m002_ai_port` fixture（`MockAiClient` + `set_ai_client` 端口替身），两例边界用例改走 `app/core/ai` 真实装配路径，新增显式断言 + docstring 标注证据形态。
- **`TD-003` 清理**：`backend/app/modules/m002/clients/task_client.py::list_groups` 的 `except TypeError` 回落分支已删除（按 M001 v0.2.0 Frozen 契约直调 `method(session, family_id, student_id=..., group_key=...)`）；同文件未发现同类「签名容错」分支（grep `except TypeError` = 1，仅本处，本次一并删除），`get_group` / `ensure_group` / `commit_conclusion` 走 `getattr(..., None) + raise M001UnavailableError` 的**存在性探针**模式（非签名兼容垫片，行为语义不同），**保留并报告**。
- **剧本 4 / 5 真实通路**：scenario4 仍断言 `spec_status == "placeholder"` + `contents == []`（不伪造草稿；docstring 注明 `BUG-004` 修复后**图片源**物理降级事实）；scenario5 手工挂接流程未受影响。
- **浏览器级剧本 5**：`Task-011` 环境（`.e2e/` + `playwright-core` + 系统 Edge 通道）复跑成功，证据分域标注（**仅**本节为浏览器级；与 API/服务级分开）。
- **基线对比**：`pytest` = **237 tests / 0 failed / 0 errors / 0 skipped**（`235 passed + 2 xpassed`，与 `Task-013` 收口基线一致，**未删减亦未新增**用例；用例数 237 与基线齐平）。
- **需 PM 处置**：`BUG-003` → `Verified`、`BUG-004` → `Verified`（`docs/changes/BUG-003.md` / `BUG-004.md` 状态位由 PM 置位，本任务书 §5 末附自检与 PM 复核请求）；`CHANGE-003` ④ 收口判定。

### ② 改动文件清单 + diff 摘要

| 文件 | 性质 | 改动摘要 |
| --- | --- | --- |
| `backend/tests/e2e/test_acceptance_scenarios.py` | 改（untracked 写区） | 移除 `m002_ai_port` fixture（`-16`）；两例边界用例 docstring 升级 + 移除 `m002_ai_port` 参数 + 新增「`status == "suggested"` + `suggestions` 非空 + `group_subject_id` 与播种一致」三组判别力断言；scenario4 docstring 注明 `BUG-004` 修复后图片源物理降级事实（断言未放宽） |
| `backend/app/modules/m002/clients/task_client.py` | 改（untracked 写区） | `TD-003`：`list_groups` 删除 `try/except TypeError` 回落分支（`-3/+1`），按 Frozen 契约直调；`get_group` / `ensure_group` / `commit_conclusion` 保留（存在性探针 ≠ 签名兼容垫片） |
| `.e2e/acceptance.mjs` | 改（untracked 写区） | 文件头注释标注「Task-014 去替身复审版」+ 证据分域说明；中段重写：移除旧 剧本6「unassigned 待挂接」与手工挂接主流程，改为「3 张照片经真实 AI 通路产出建议 → UI 呈现 AI 建议 + 采纳入口 → 逐张采纳 → 门控满足 → 生成草稿 → 家长确认」；追加「剧本6 手工兜底入口仍可用（B6）」轻断言以证明前端 UI 未退化 |
| `.e2e/seed.py` | 改（untracked 写区） | 上传后轮询等待异步挂接建议落库（`BUG-003` 修复后 Mock Provider 经真实装配路径产出建议，不再 `unassigned`），并把 `photos` / `gates` 状态写入 `seed_state.json`（浏览器脚本据此断言；非契约扩展，仅种子侧增量） |
| `.e2e/browser_evidence.json` | 产物（untracked） | 浏览器级剧本 5 18/18 PASS 原文摘要 |
| `.e2e/seed_state.json` | 产物（untracked） | 种子数据库状态（新增 `photos[]`、`gates[]` 字段，含真实 AI 建议 `link.source=ai`） |
| `.e2e/shots/*.png` | 产物（untracked） | `01_tasks.png` / `02_photos_ai_suggested.png` / `03_photos_assigned.png` / `04_analysis_confirmed.png` |

无任何契约/权威源/Forbidden 区写入（见 §⑤）。

### ③ 红→绿 / 判别力证据原文

#### 3.1 边界用例去替身（绿）

```
tests\e2e\test_acceptance_scenarios.py::test_boundary_gate_not_satisfied_409_api_level PASSED
tests\e2e\test_acceptance_scenarios.py::test_boundary_analysis_confirmed_is_terminal_api_level PASSED
```

#### 3.2 判别力（关闭 Mock 兜底时转红，**等价于红→绿**）

`AT_AI_PROVIDER_MODE=real` + `AT_AI_ALLOW_MOCK_FALLBACK=false` 下，断言必败：

```
E   AssertionError: {'photo_id': '...', 'status': 'unassigned', 'suggestions': []}
E   assert 'unassigned' == 'suggested'
tests\e2e\test_acceptance_scenarios.py:454: AssertionError
FAILED tests\e2e\test_acceptance_scenarios.py::test_boundary_gate_not_satisfied_409_api_level

E   AssertionError: {'photo_id': '4e0094b2-...', 'status': 'unassigned', 'suggestions': []}
    assert 'unassigned' == 'suggested'
tests\e2e\test_acceptance_scenarios.py:483: AssertionError
FAILED tests\e2e\test_acceptance_scenarios.py::test_boundary_analysis_confirmed_is_terminal_api_level
```

—— 即「`status == "suggested"` 且 `suggestions` 非空」是真有**判别力**的断言：Mock 兜底关闭 → 真实通路无法产出建议 → 断言立败，**不是无脑通过**。

#### 3.3 目标用例复跑原文（绿）

```
$ python -m pytest tests/e2e/test_acceptance_scenarios.py tests/integration/test_m002_gate_real_m001.py -v --no-header
...
15 passed in 67.5s
```

含 `test_scenario4_task_entry_image_source_mock_parse_api_level`（图片源 `placeholder` 边界未放宽）、`test_scenario5_photo_link_gate_analysis_confirm_api_level`（手工挂接流程未受影响）、`test_boundary_*` × 2、`test_m002_gate_real_m001` 真机门控集成用例（证明 `TD-003` 删除的回落分支为死代码）。

#### 3.4 `TD-003` 死代码证明

- 改动前 `list_groups` 的 `try` 块即为 `method(session, family_id, student_id=..., group_key=...)`，**与 Frozen 契约一致**；`except TypeError` 仅在调用方与服务方签名不兼容时触发。
- `M001 v0.2.0 Frozen`：`TaskGroupService.list_groups(self, session, family_id, *, student_id=None, group_key=None, week_index=None, window_type=None)`（同时支持 `group_key` 与 `week_index` / `window_type` 关键字，调用方传 `group_key` 时其它关键字走默认值，**永不触发 `TypeError`**）。
- 真机门控集成用例 10 例（`test_m002_gate_real_m001.py`）+ 边界用例 2 例 + scenario4/5 + 上层 40+ 例**全部直调 `DefaultM001Gateway.list_groups(group_key=...)` 路径通过** = 0 触发 = 死代码。
- 风险面：`get_group` / `ensure_group` / `commit_conclusion` 的 `getattr(..., None) + raise M001UnavailableError` 模式为**存在性探针**（`None` 走显式失败），与 `except TypeError` 的**签名兼容垫片**语义不同（前者不存在则大声失败，后者存在但签名不同时静默改写调用），**保留并报告**。

### ④ 全量回归原文

```
$ python -m pytest --no-header
........................................................................ [ 30%]
.............................X..X....................................... [ 60%]
........................................................................ [ 91%]
.....................                                                    [100%]
235 passed, 2 xpassed, 1 warning in 89.46s (0:01:29)
EXIT=0
```

基线对齐：`237 = 235 passed + 2 xpassed`（`xfail(strict=False)` 缺陷双哨兵 `test_bug003_*` / `test_bug004_*` 均自然 **XPASS**，与 `Task-013` 收口时一致，**未删减未新增**用例）；EXIT = 0；0 failed / 0 errors / 0 skipped。

Junit 摘要：`.e2e/pytest_full.xml`（untracked 写区产物）。

### ⑤ 写区合规自证（双证）

#### 5.1 `git status --porcelain` 摘要

```
?? backend/app/core/ai/                         (Forbidden — 未修改)
?? backend/app/modules/m001/repositories/...    (Forbidden — 未修改)
?? backend/app/modules/m001/services/...        (Forbidden — 未修改)
?? backend/app/modules/m001/schemas/...         (Forbidden — 未修改)
?? backend/app/modules/m001/models/...         (Forbidden — 未修改，未在 porcelain 全列；属同一未跟踪子树)
?? backend/app/modules/m002/                    (Untracked 写区 — 仅修改 clients/task_client.py)
?? backend/tests/e2e/                           (Untracked 写区 — 修改 test_acceptance_scenarios.py)
?? backend/tests/m002_support.py                (Untracked 写区 — 未修改；§⑥ 审计后保留并标注)
?? backend/tests/integration/test_m002_gate_real_m001.py   (Untracked 写区 — 未修改，作为 TD-003 死代码证据)
?? .e2e/                                        (Untracked 写区 — 修改 acceptance.mjs / seed.py；产物 browser_evidence.json / seed_state.json / shots/ / pytest_full.xml)
 M backend/app/modules/m001/...（多处）         (预存在改动 — 非本次任务写入)
 M backend/tests/api/...（多处）                (预存在改动 — 非本次任务写入)
 M frontend/...（少量）                          (预存在改动 — 非本次任务写入)
 M docs/...（多处）                             (预存在改动 — 非本次任务写入)
```

**本次任务净写入 = 0 个 tracked 文件**（所有改动均在 untracked 写区内或属于本任务书 §5 追加）。

#### 5.2 mtime 审计（Forbidden 区未触发本会话）

| 文件 | mtime | 结论 |
| --- | --- | --- |
| `backend/app/core/ai/providers/mock.py` | 2026-09-10 20:15:47 | 早于本次写区（20:25+）→ 未改 ✓ |
| `backend/app/core/ai/service.py` | 2026-09-10 16:54:31 | 早于 20:25 → 未改 ✓ |
| `backend/app/core/ai/__init__.py` | 2026-09-10 16:54:39 | 早于 20:25 → 未改 ✓ |
| `backend/app/modules/m001/services/window_resolver.py` | 2026-09-10 17:01:16 | 早于 20:25 → 未改 ✓ |
| `backend/app/modules/m001/repositories/group_repo.py` | 2026-09-10 16:53:57 | 早于 20:25 → 未改 ✓ |
| `frontend/src/views/PhotoListView.vue` | 2026-09-10 17:55:15 | 早于 20:25 → 未改 ✓ |
| `frontend/src/components/PhotoCard.vue` | 2026-09-10 17:53:10 | 早于 20:25 → 未改 ✓ |
| `docs/changes/BUG-003.md` | 2026-09-10 20:23:19 | 早于 20:25（属 `Task-013` PM 复核时段）→ 未改 ✓ |
| `docs/changes/BUG-004.md` | 2026-09-10 20:24:44 | 早于 20:25（属 `Task-012` PM 复核时段）→ 未改 ✓ |
| `docs/changes/CHANGE-002.md` | 2026-09-09 14:32:46 | 预存在 → 未改 ✓ |
| `docs/API_REGISTRY.md` | 2026-09-10 19:23:41 | 早于 20:25 → 未改 ✓ |
| `docs/modules/M001/MODULE_API.md` | 2026-09-10 16:42:53 | 早于 20:25 → 未改 ✓ |
| `docs/modules/M002/MODULE_API.md` | 2026-09-10 19:23:20 | 早于 20:25 → 未改 ✓ |
| `docs/requirements/CLARIFICATION-2026-09-10.md` | 2026-09-10 16:36:45 | 早于 20:25 → 未改 ✓ |
| `docs/PROJECT_STATUS.md` / `INDEX.md` | 2026-09-10 20:01-20:01:53 | 早于 20:25 → 未改 ✓ |
| `docs/agents/Task-014.md` | 2026-09-10 20:25:27 | 任务书创建于本会话起点；本 §5 为本任务唯一追加 |
| `backend/app/modules/m002/clients/task_client.py` | 2026-09-10 20:26:54 | 本次任务改（TD-003 清理）✓ |
| `backend/tests/e2e/test_acceptance_scenarios.py` | 2026-09-10 20:26:50 | 本次任务改（去替身）✓ |
| `.e2e/acceptance.mjs` | 2026-09-10 20:29:55 | 本次任务改（剧本 5 浏览器级）✓ |
| `.e2e/seed.py` | 2026-09-10 20:28:52 | 本次任务改（确定性种子）✓ |

`read_lints` 全部 0：`backend/tests/e2e/test_acceptance_scenarios.py`、`backend/app/modules/m002/clients/task_client.py`、`.e2e/acceptance.mjs`、`.e2e/seed.py` 均无诊断。

### ⑥ 去替身审计清单

| # | 替身 / 桩 | 位置 | 用途 | 处置 |
| --- | --- | --- | --- | --- |
| 1 | `m002_ai_port` fixture | `backend/tests/e2e/test_acceptance_scenarios.py:70-83`（旧） | 注入 `MockAiClient` + `set_ai_client`，强制 2 例边界用例产出 AI 建议 | **删除**（§3.1）；用例改走真实 AI 通路 + 新增判别力断言 |
| 2 | `MockAiClient` / `set_ai_client`（被 #1 引用） | `backend/app/modules/m002/clients/ai_client.py` | M002 端 AI 端口协议 + 端口替身注入接口 | **保留协议类**（契约面）；`set_ai_client` 作为端口注入入口**保留**（属 M002 `AiClientPort` 契约面，**不**用于本次去替身证据）。**本次未注入**该替身；§3.2 判别力取证显式在**无该注入**下通过 / 失败 |
| 3 | `FakeGateway` | `backend/tests/m002_support.py`（`M001GatewayBase` / `FakeM001Gateway`） | M001 网关协议测试替身（`BUG-002` 修复后已弃用） | **保留 + 显式标注**：grep `FakeGateway` 全文 = 0 引用（`backend/app/modules/m002/clients/task_client.py` 已切回 `DefaultM001Gateway` 真实路径；门控用例直接 `DefaultM001Gateway().ensure_group/commit_conclusion`）；该类在 `m002_support.py` 仍以**协议测试桩**身份存在（不参与本次证据链路），与 `BUG-002` 替身等价性已不存在 |
| 4 | `m002_support.py` 中的等价物 | `backend/tests/m002_support.py` | M001/M002 集成测试共享 fixture / 协议替身 / `real_stack` | **保留**（fixture = `real_stack` = 清缓存 + 切 `DefaultM001Gateway` 真实路径，**不是**替身；`FakeM001Gateway` 仅作协议测试桩，不接入主证据链） |
| 5 | `tests/unit/ai_stubs.py` | `backend/tests/unit/ai_stubs.py` | AI 协议单元测试桩（与 core/ai 协议对齐） | **保留**（属 `app/core/ai` 协议面单元测试，非消费链替身；本次不调用） |
| 6 | `DefaultAiClient` 内部兜底 | `backend/app/core/ai/` | 「无三方密钥 → Mock Provider 兜底」本身**不是**替身，是 `ADR-011` 决策的**真实装配路径** | **保留**（Mock 通路证据须显式标注 `mock=True`，见 `ADR-011` / `CONFIGURATION.md` §五 `AT_AI_*`） |
| 7 | `install_fixed_window` | `backend/tests/e2e/test_acceptance_scenarios.py:install_fixed_window` | 固定 `WindowResolver` 返回值（`AT_TERM_START` 不变性） | **保留**（属「测试内确定性」而非「掩盖真机缺口」；不影响 AI 通路真实性） |
| 8 | `set_scheduler(lambda runner: runner())` | `backend/tests/e2e/test_acceptance_scenarios.py::real_stack` | 把建议调度从后台线程切内联（确定性） | **保留**（执行体未变，只是不再起新线程；属测试确定性而非替身） |
| 9 | `seed.py` 自身的 `client` / 登录 | `.e2e/seed.py` | 真实 `TestClient` 走真实服务装配路径 | **保留**（与 `AT_DATABASE_URL=acceptance.db` 配套，是浏览器前置数据准备而非替身） |
| 10 | `acceptance.mjs` UI 断言选择器 | `.e2e/acceptance.mjs` | Playwright `getByRole` / `.locator` 选择器 | **保留**（无伪造 UI 路径，仅定位） |

**判据自检（PM 铁律 ①）**：

- 证据经**真实装配路径**消费链路：
  - 用例链路 = `TestClient` → `DefaultM001Gateway` → M001 真实 `TaskGroupService` + `DefaultAiClient` → `app/core/ai` → Mock Provider；
  - 浏览器链路 = `uvicorn` 真实服务 + `frontend/dist` 真实产物 + 系统 Edge 真实通道。
- 真实服务「无任何 AI 端口替身注入」显式证明：去替身后 `MockAiClient` 在 `m002_ai_port` 注入路径上**无引用**（grep `set_ai_client` 在测试代码 = 0 引用，仅 `m002/clients/ai_client.py` 内部定义）；`m002_ai_port` fixture 全文 = 0 引用。
- `FakeGateway` 残留 = 0：`grep -rn "FakeGateway" backend/tests/e2e` = 0；`backend/tests/m002_support.py` 内 `FakeM001Gateway` 类仍定义但**未被本次任何用例引用**（属协议测试桩保留，不参与证据链）。

### ⑦ 遗留说明 + 需 PM 裁决项

- **真实三方 AI Provider 联调**：当前环境无密钥（既有已知边界），所有 AI 通路证据均为 **Mock Provider（`mock=True`）**，并非三方联调。`@analyze_completion` 返回 `model: "mock-vision"`、`@suggest_photo_links` 经 `app/core/ai` → Mock Provider 装配路径产出，证据形态显著标注。**无第三方 key 不得伪造联调证据**（PM 铁律 ① / ⑨）—— 此项为已知边界，**不属本任务范围**（§6）。
- **`TD-001`（N+1）/ `TD-002`（契约未暴露 `window_task_id` / `task_status`）**：登记保留，不属本任务（§6）。
- **`get_group` / `ensure_group` / `commit_conclusion` 的 `getattr(..., None) + raise` 探针**：与 `except TypeError` 签名兼容垫片**语义不同**（前者存在性 → 显式失败；后者签名不兼容 → 静默改写），**未扩面清理**。如 PM 裁决需统一对齐（PM 铁律 ⑥「修复类任务禁止 `try/except TypeError` 兼容旧签名」对此类存在性探针**未显式禁止**），可后续登记 `TD-004`。
- **`docs/changes/BUG-003.md` / `BUG-004.md` 状态位**：本任务 §③ 判别力取证与基线回归已证明二者在验收层得到确认（**红→绿（修复）→ 真实装配路径下断言成立**），但状态位**由 PM 置位**（任务书 §5 末自检 + §6）；**本任务不自置** `Verified`。
- **需 PM 裁决**：
  1. `BUG-003` → `Verified` / `BUG-004` → `Verified` 状态置位（依据本任务 §③ + ④ 证据）。
  2. `CHANGE-003` ④ 收口判定（执行方认为 ④ 已达成收口前置）。
  3. `TD-004` 立项与否（`getattr(..., None) + raise` 探针是否需统一替换为显式依赖注入）。

---

### 5D PM 复核（**成立**，2026-09-10，Project Master 亲手复现）

#### 5D.1 审读（未采信自述）

- **去替身真实有效**：`grep -rn "m002_ai_port|MockAiClient|set_ai_client" backend/` → `tests/e2e/test_acceptance_scenarios.py` 仅剩 **2 处 docstring 说明**（`:435` / `:470` 声明「原端口替身已移除」），**无 fixture 定义、无参数引用**；fixture `real_stack` 只做 `get_ai_service`/`get_ai_settings` 清缓存 + 内联调度（**无 AI 端口注入**）→ 两例边界用例的「AI 建议」确由 `app/core/ai` 真实装配路径产出。
- **新增断言有判别力且非臆造**：`assert sug["status"] == "suggested" and sug["suggestions"]` + `[s["group_subject_id"] for s in sug["suggestions"]] == [gs]`（`:454-455` / `:483-485`），`gs` 来自 `_seed_window_day` 播种的唯一学科子任务 —— 与 `Task-013-D1` 口径一致。
- **`TD-003` 清理到位**：`clients/task_client.py:201-216` 现为**按 Frozen 契约直调** `method(session, family_id, student_id=..., group_key=...)`；全仓 `grep "except TypeError"` = **1**，且该 1 处位于 `task_client.py:214` 的**注释**（记录教训），**非可执行分支** → 垫片确已删除。
- **未扩面**：`get_group` / `ensure_group` / `commit_conclusion` 的 `getattr(..., None) + raise M001UnavailableError` 探针保留（下方裁决）。

#### 5D.2 PM 亲手判别力复现（红 → 绿）

| 步骤 | 命令（`backend/`） | 原文结果 |
| --- | --- | --- |
| **红** | `$env:AT_AI_PROVIDER_MODE='real'; $env:AT_AI_ALLOW_MOCK_FALLBACK='false'; pytest tests/e2e/test_acceptance_scenarios.py::test_boundary_gate_not_satisfied_409_api_level ::test_boundary_analysis_confirmed_is_terminal_api_level -q --tb=short` | **`FF`**；`E AssertionError: {'status': 'unassigned', 'suggestions': []}` / `assert 'unassigned' == 'suggested'`（`:454`、`:483`）→ **`RED_EXIT=1`** |
| **绿** | 还原 `auto` / 允许兜底 → 同 2 例 + `test_scenario4_*` + `test_scenario5_*` | **`....` 4 passed** → **`GREEN_EXIT=0`** |

→ 断言**真有判别力**（关兜底立败、还原即绿），**非无脑通过**；同时证明「建议来自真实装配路径」而非替身。

#### 5D.3 PM 独立全量回归与写区双证

- **全量（PM 实测）**：`pytest --tb=no -q --junitxml=.pm_t014.xml` → **`tests=237 failures=0 errors=0 skipped=0`、`EXIT=0`**（`X..X..` = `BUG-003`/`BUG-004` 双哨兵自然 XPASS）；与 `.e2e/pytest_full.xml` 摘要（237/0/0/0）**一致**；临时 xml 已删除（`.pm_*.xml` 无残留）。
- **写区（双证）**：`git status --porcelain -- backend/app/modules/m002/clients/task_client.py backend/tests/e2e/test_acceptance_scenarios.py` → **两者均 `??`**（未跟踪写区，与报告一致）；**mtime 审计**：Forbidden 区全部早于写区起点（`core/ai/providers/mock.py` 20:15:47、`core/ai/service.py` 16:54:31、`m001/services/window_resolver.py` 17:01:16、`frontend/src/views/PhotoListView.vue` 17:55:15、`BUG-003.md` 20:23:19、`BUG-004.md` 20:24:44、`MODULE_API.md` 19:23:20、`API_REGISTRY.md` 19:23:41）→ **零写入**成立。
- **浏览器级**：`.e2e/browser_evidence.json` → **`ok:true` = 18 / `ok:false` = 0**；含「3 张照片 经真实 AI 通路产出建议」（`withAiSuggestion=3`、`status=suggested×3`）、「采纳 6 次全 `200`」→ `assigned×3` → 门控满足 → `POST /completion-analyses → 201`（`model: "mock-vision"`、`status: draft`）→ 家长确认；截图 4 张在 `.e2e/shots/`。**证据分域**（浏览器级 / API 级 / 服务级）标注清晰。

#### 5D.4 PM 裁决

1. **`BUG-003` → `Verified`**（`Task-013` 修复 + `Task-013-D1` API 面补证 + 本节 5D.2 判别力复现）。
2. **`BUG-004` → `Verified`**（`Task-012` 修复 + `Task-014` 在真实装配路径下边界/剧本通路过绿 + 全量 237/0）。
3. **④ 判达成 → `CHANGE-003` 收口（Closed）**：`Task-011` 的 3 项缺口 —— ①② 已由 `Task-012`/`Task-013` 修复并经本任务去替身复审 + PM 亲手复现闭合；③ 真实三方无密钥为**已知边界**（`ADR-011` Mock 为最低验收线），已在收口结论显式标注，**不阻断**。
4. **不立 `TD-004`**：`get_group` / `ensure_group` / `commit_conclusion` 的 `getattr(..., None) + raise M001UnavailableError` 为**存在性探针**（缺方法 → 大声失败），与 `except TypeError` **签名兼容垫片**（存在但签名不符 → 静默改写调用）**语义不同**，不构成「掩盖契约缺口」；**保留现状**。已在 `docs/TECH_DEBT.md` `TD-003` 处置结果中记录。
5. **`TD-003` → Closed**（垫片已删 + 真机集成 10 例 + 上层 40+ 例 0 触发，死代码证明成立）。

**结论：`Task-014` 复核成立并收口；`CHANGE-003` 关闭（V1 域 A/B/C 交付完成）。**

---

**本任务书已自检「交付物 ⊆ 写区」（PM 铁律 ⑧）**：所有交付物（`backend/tests/e2e/test_acceptance_scenarios.py` / `backend/app/modules/m002/clients/task_client.py` / `.e2e/acceptance.mjs` / `.e2e/seed.py` + 写区产物 `browser_evidence.json` / `seed_state.json` / `shots/` / `pytest_full.xml`）**均**在 §3.1-3.5 写区内；`docs/changes/BUG-003.md` / `BUG-004.md` 状态位**未触碰**（由 PM 置位）。

## 6. 不在本任务范围

- 真实三方 AI Provider 联调（无密钥，既有已知边界）→ 不属本任务；Mock 通路证据须显著标注 `mock=True`。
- `TD-001`（N+1）、`TD-002`（契约未暴露 `window_task_id`/`task_status`）→ 不在本任务。
- `frontend/**` 代码改动 → 不在本任务（浏览器级复跑**只读**前端产物）。
- `CHANGE-003` ④ 的**收口判定**与状态置位 → Project Master。
