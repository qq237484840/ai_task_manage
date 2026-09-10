# Task-013 任务书 —— `BUG-003` 修复（Mock 挂接建议 context key 错位）

- **Task ID**：Task-013 ｜ **Agent**：`AGENT-AI`（`ai-dev`）｜ **范围**：横切 AI 接入层 `app/core/ai/`
- **签发**：Project Master，2026-09-10 ｜ **状态**：**已收口（PM 复核成立 + `Task-013-D1` 补证成立，`Fixed`；`BUG-003` 待 `Task-014` 后 Verified）** ｜ **Kind**：**缺陷修复（`BUG-003`，中）**
- **启动前置（已满足）**：`Task-006` 已完成（PM 复核 APPROVED）；`BUG-003` 已由 PM 复核 **Confirmed**（根因经读码确认，见 `docs/changes/BUG-003.md` §7）。
- **契约影响**：**无**（`app/core/ai/` 为内部实现层，prompt key / context key 属实现约定；不改任何模块契约）。
- **写区（授权）**：`backend/app/core/ai/**` ＋ `backend/tests/**`（AI 层 / 接线用例）。
- **禁止改**：`backend/app/modules/m001/**`、`backend/app/modules/m002/**`、`frontend/**`、契约文本、治理文档（除 `docs/agents/Task-013.md` 过程记录）。

## 1. Objective（目标）

消除 Mock 降级路径下「挂接建议恒为空」的 key 错位，使 AI 挂接建议（`CAPABILITY_PHOTO_LINK_SUGGEST`）在 Mock 下**可用**；并建立**防漂移**机制，避免同类「直调 Mock 掩盖装配路径缺口」再次发生。

## 2. Root Cause（PM 读码确认，勿再自行推断）

| # | 环节 | 证据（PM 复核原文） |
| --- | --- | --- |
| 1 | 服务注入 key = `candidates` | `backend/app/core/ai/service.py:197`：`context: dict[str, Any] = {"candidates": candidate_payload}` |
| 2 | prompt 变量同名 | `backend/app/core/ai/prompts/photo_link_suggest.v1.txt:4`：`$candidates` |
| 3 | Mock 读 key = `candidate_subjects` | `backend/app/core/ai/providers/mock.py:141`：`return _suggest_links(list(context.get("candidate_subjects", []) or []))` |
| 4 | 结果 | key 不匹配 → `_suggest_links([])` → `{"links": [], "confidence": 0.0}` → `PhotoLinkOutcome.ok=True` 但建议恒空（**静默失效**） |

**为何 `Task-006` 未发现**：AI 层测试**直接调用 Mock Provider 并手写 `context={"candidate_subjects": [...]}`**，绕过了 `AIService.suggest_photo_links` 的真实装配路径 —— 属「桩掩盖真机缺口」类问题（与 `BUG-002` 同类教训）。

## 3. 修复要求

1. **对齐 key**：`mock.py:141` 读取 `candidates`（与 `AIService` / prompt 一致）。备选方案（`AIService` 冗余注入两 key）**不推荐**，如采用须说明理由并保证 prompt/真实 Provider 路径不受影响。
2. **防漂移用例（必做）**：新增**经真实装配路径**的断言 —— `suggest_photo_links(None, family_id=..., photo=PhotoInput(...), candidates=[SubjectCandidate(group_subject_id="g1", subject="math")])` → `out.available and out.ok` 且 `[l.group_subject_id for l in out.links] == ["g1"]`。**不得**再以「直调 `MockVisionProvider.analyze` 并手写 context key」作为正确性证据。
3. **审读并整改既有 AI 层用例**：`Task-006` 交付用例中所有「直调 Provider + 手写 context」的写法，改为经服务装配路径触发（或补充装配路径断言）—— 这是本次漏检根因，须在过程记录中列出清单与处置。
4. **不得越界**：本任务**不修** `BUG-004`（M001 侧调用方式，见 `Task-012`）。

## 4. DoD（交付判定）

- [ ] `backend/tests/e2e/test_acceptance_ai_wiring.py`：
  - `test_bug003_mock_link_suggest_echoes_candidates`：**xfail → XPASS**
  - `test_bug003_evidence_context_key_mismatch`：按修复后事实改写（原用例以「`candidates` → 空、`candidate_subjects` → 有建议」锁定错位，修复后前提失效），并在过程记录说明
- [ ] 新增「装配路径」防漂移用例（§3.2），且该用例在 `BUG-003` 未修时**必然失败**（红→绿取证）
- [ ] 既有 AI 层「直调 Provider + 手写 context」用例整改清单（过程记录中逐条列出：文件 / 用例 / 处置）
- [ ] 全量 `pytest`：**0 failed**，用例数**不低于 227**
- [ ] `read_lints` = 0；`git diff --name-only` **仅限授权写区**
- [ ] 过程记录：`docs/agents/Task-013.md` 追加「§5 修复过程与证据」

## 5A. 交付物（签发时清单）

代码改动（授权写区内）、用例（新增 / 整改）、本文档 §5 过程记录、修订后 `docs/changes/BUG-003.md`（**§7 追加「修复记录」**，状态由 PM 复核后置 **Verified**）。

## 5. 修复过程与证据

- **执行**：`AGENT-AI`（`ai-dev`），2026-09-10 ｜ **状态**：已交付、待 PM 复核
- **结论**：`BUG-003` 已修复（Mock 挂接建议经**真实装配路径**回显候选）；新增防漂移用例；全量回归 `0 failed`。

### 5.1 代码修复

`backend/app/core/ai/providers/mock.py`（`_mock_payload`，`PROMPT_PHOTO_LINK_SUGGEST` 分支）：

```diff
-        return _suggest_links(list(context.get("candidate_subjects", []) or []))
+        return _suggest_links(list(context.get("candidates", []) or []))
```

与 `AIService` 注入 key（`service.py:197`）及 prompt 变量（`prompts/photo_link_suggest.v1.txt:4` 的 `$candidates`）三者对齐；真实三方 Provider 路径不含该 key，未受影响。

### 5.2 新增防漂移用例（`backend/tests/e2e/test_bug003_link_keys.py`，5 例）

一律经 `AIService.suggest_photo_links` / 模块级 `suggest_photo_links` **真实装配路径**，以输出为证据：

| 用例 | 断言 |
| --- | --- |
| `test_mock_link_suggest_via_service_assembly_echoes_candidates` | `available and ok`；`links == ["g1"]`；`mock=True` |
| `test_module_level_suggest_photo_links_assembly_echoes_candidates` | 模块级入口（与 Task-011 验收同调用面）回显候选 |
| `test_mock_link_suggest_assembly_returns_all_candidates_nn` | N:N（3 候选）全部回显且顺序一致 |
| `test_mock_link_suggest_assembly_empty_candidates_stays_empty` | 空候选仍 `ok`，但**不得编造**建议 |
| `test_service_injected_context_key_is_consumed_by_mock_provider` | **键位合同**：由捕获 Provider 记录**服务真实注入**的 context，再交 `MockVisionProvider` 消费；键值取自服务、**非手写** |

### 5.3 红 → 绿取证

修复前（`mock.py` 未改）：

```
$ .\.venv\Scripts\python.exe -m pytest tests/e2e/test_bug003_link_keys.py -v -rx
tests\e2e\test_bug003_link_keys.py FFF.F                                 [100%]
...
E       AssertionError: 服务注入 context 与 Mock 读取 key 再次漂移：{'candidates': [{'group_subject_id': 'g1', 'subject': 'math'}]}
E       assert 'g1' in '{"links": [], "confidence": 0.0}'
=================== 4 failed, 1 passed, 1 warning in 0.40s ====================
```

修复后：

```
$ .\.venv\Scripts\python.exe -m pytest tests/e2e/test_bug003_link_keys.py -v -rx
tests\e2e\test_bug003_link_keys.py .....                                 [100%]
======================== 5 passed, 1 warning in 0.13s =========================
```

`test_acceptance_ai_wiring.py`（`-ra`）：

```
tests\e2e\test_acceptance_ai_wiring.py X..X.                             [100%]
XPASS tests/e2e/test_acceptance_ai_wiring.py::test_bug003_mock_link_suggest_echoes_candidates - BUG-003（已修复，哨兵保留）...
=================== 3 passed, 2 xpassed, 1 warning in 0.10s ====================
```

- `test_bug003_mock_link_suggest_echoes_candidates`：**xfail → XPASS**（`xfail(strict=False)` 哨兵保留，回归时回落 xfailed）。
- `test_bug004_...`：由并行的 `Task-012`（`m001-dev`）修复 → 亦 XPASS（**非本任务改动**）。

### 5.4 既有用例整改清单（原「直调 Provider + 手写 context」写法）

| # | 文件 | 用例 | 处置 |
| --- | --- | --- | --- |
| 1 | `backend/tests/unit/test_ai_providers.py` | `test_mock_vision_is_deterministic_and_marked` | 手写 `candidate_subjects` → 改为 `candidates`（与装配契约对齐）；注明其为纯 Provider 级确定性测试，装配正确性不得以其替代 |
| 2 | `backend/tests/e2e/test_acceptance_ai_wiring.py` | `test_bug003_evidence_context_key_mismatch` | 原用例锁定错位（`candidates`→空 / `candidate_subjects`→有建议），修复后前提失效 → 按修复后事实改写（`candidates`→有 `g1`；旧键→空）；函数名保留以维持追溯性 |
| 3 | `backend/tests/e2e/test_acceptance_ai_wiring.py` | `test_bug003_evidence_service_yields_empty_links` | 原断言 `links == []` 随修复必然失效（DoD 未列但**必须**同步，否则回归红灯）→ 改写为回显 `["g1"]`；函数名保留 |
| 4 | `backend/tests/e2e/test_acceptance_scenarios.py` | `test_scenario5_*` | 审读：经 API + 真实 `app/core/ai` 装配（**非**直调 Provider），无需整改；其原仅断言响应**形状**、未断言建议非空 → 已于 **§5.9（`Task-013-D1`）** 按 PM 要求补齐 **API 面**断言（剧本语义/手工挂接流程未改） |

> 根因固化：`app/core/ai` 的**装配路径正确性**自此由 `test_bug003_link_keys.py` 承担，禁止再以「直调 Provider + 手写 context」作为证据。

### 5.5 全量回归

```
$ .\.venv\Scripts\python.exe -m pytest -q --junitxml=.junit_task013.xml
........................................................................ [ 30%]
............................X..X........................................ [ 61%]
........................................................................ [ 91%]
....................                                                     [100%]
EXIT=0

tests=236 failures=0 errors=0 skipped=0
```

（`.junit_task013.xml` 为临时统计文件，已删除。）

### 5.6 附加发现并修复：`test_scenario6` 测试隔离缺陷（被本修复"暴露"）

全量回归首轮出现 **1 failed**：`test_acceptance_scenarios.py::test_scenario6_llm_unavailable_...`。

- **现象**：`scenario6` 期望「`real` + 禁 Mock 兜底 → 无建议」，实测返回 1 条建议。
- **定位**：`scenario6` 单独运行 → **通过**；`scenarios` 文件内前序 `scenario1~5` 经 `real_stack` 触发 `get_ai_settings()`（`lru_cache`）缓存了 **auto（Mock 兜底）** 配置；`scenario6` 仅 `get_ai_service.cache_clear()`、**未清 settings 缓存** → 新 `AIService` 仍解析为 Mock。
- **为何原先未暴露**：BUG-003 修复前 Mock 恒返回空建议，`scenario6` 的 `suggestions == []` **因错误原因假通过**；本修复使 Mock 真正产出建议，假通过被揭穿。
- **处置（`backend/tests/**` 授权写区）**：
  - `real_stack` fixture setup/teardown 同步 `get_ai_settings.cache_clear()`（防跨用例泄漏）；
  - `scenario6` setenv 后补 `get_ai_settings.cache_clear()`（确保真正走 `real` + 禁兜底）。
- **修复后**：`scenarios` 全文件通过；全量 `0 failed`。

### 5.7 写区合规

- 改动文件：`backend/app/core/ai/providers/mock.py`、`backend/tests/e2e/test_bug003_link_keys.py`（新增）、`backend/tests/e2e/test_acceptance_ai_wiring.py`、`backend/tests/e2e/test_acceptance_scenarios.py`、`backend/tests/unit/test_ai_providers.py` —— 均在授权写区（`backend/app/core/ai/**` + `backend/tests/**`）。
- **未触碰**：`backend/app/modules/m001/**`、`backend/app/modules/m002/**`、`frontend/**`、契约文本、治理文档。
- 说明：`backend/app/core/ai/` 与 `backend/tests/e2e/` 目前**未被 git 跟踪**（`git ls-files --error-unmatch backend/app/core/ai/providers/mock.py` 报 pathspec 不匹配），故 `git diff --name-only` 不含其条目；以 `git status --porcelain` 佐证（`?? backend/app/core/ai/`、`?? backend/tests/e2e/`）。

### 5.8 待 PM 处理（越界规避）

任务书 §5 交付物列「修订 `docs/changes/BUG-003.md` §7 追加修复记录」，但 §8（禁止改治理文档，仅允许 `docs/agents/Task-013.md` 过程记录）与派单方指令相冲突。**本次未修改 `BUG-003.md`**；修复记录见本节 §5，请 PM 复核后由 PM 回填并置 `Verified`。

### 5.9 `Task-013-D1` 补证：BUG-003 的 **API 面**证据（PM 复核后追加）

**缺口**：BUG-003 的原始症状出现在 `GET /api/v1/photos/{id}/link-suggestions`（**API 面**），而 §5.1~§5.3 的证据只到 `AIService` / 模块级入口（**service 面**）；分层证据不得跨域替代。

#### 5.9.1 改动（`backend/tests/**` 授权写区，最小化，不重写剧本语义）

`backend/tests/e2e/test_acceptance_scenarios.py::test_scenario5_photo_link_gate_analysis_confirm_api_level`，在原「形状」断言之后追加（字段名与播种值**已读码确认，未臆造**）：

```python
    body = sug.json()
    assert set(body) == {"photo_id", "status", "suggestions"}
    assert body["status"] == "suggested", body
    assert body["suggestions"], f"BUG-003：Mock 挂接建议不得为空：{body}"
    assert [s["group_subject_id"] for s in body["suggestions"]] == [gs], body
```

- **字段依据**：`LinkSuggestionOut{photo_id, status, suggestions[]}`、`LinkSuggestionItemOut{link_id, group_subject_id, subject, confidence, source, suggested_at}`（`modules/m002/api/link_routes.py:31-65`、`modules/m002/schemas.py`）。
- **`gs` 依据**：`_seed_window_day(...)` 的返回值；其播种文本 = 「数学：练习册 P23 第 1-10 题」→ Mock 解析归一为 `math`，即该 day 窗口的唯一学科子任务。
- **状态依据**：`LinkService._recompute_photo_status`（`modules/m002/services/link_service.py:359-370`）—— 存在未判无效链接 → `PhotoStatus.SUGGESTED`。
- **未改**：`_accept` 手工挂接 / 门控 / 生成 / 确认全流程原样；用例函数名与语义不变。
- `m002_ai_port` fixture docstring 追加：**前提已由 BUG-003 修复消除**、本替身**不得再作长期证据**、去留由 `Task-014` 处置；**本次未删替身**（属 `Task-014` 范围）。

#### 5.9.2 红 → 绿取证

临时回退 `providers/mock.py:143` → `candidate_subjects`：

```
$ .\.venv\Scripts\python.exe -m pytest "tests/e2e/test_acceptance_scenarios.py::test_scenario5_photo_link_gate_analysis_confirm_api_level" -q
F                                                                        [100%]
>       assert body["status"] == "suggested", body
E       AssertionError: {'photo_id': 'd304214e-9bc1-4f30-a099-2d5e49...
FAILED tests/e2e/test_acceptance_scenarios.py::test_scenario5_photo_link_gate_analysis_confirm_api_level
RED_EXIT=1
```

还原（`providers/mock.py:143` = `context.get("candidates", [])`）：

```
$ .\.venv\Scripts\python.exe -m pytest "tests/e2e/test_acceptance_scenarios.py::test_scenario5_photo_link_gate_analysis_confirm_api_level" -q
.                                                                        [100%]
EXIT=0
```

相关三文件（还原后）：

```
$ .\.venv\Scripts\python.exe -m pytest tests/e2e/test_acceptance_scenarios.py tests/e2e/test_acceptance_ai_wiring.py tests/e2e/test_bug003_link_keys.py -q -ra
...........X..X......                                                    [100%]
XPASS ...::test_bug003_mock_link_suggest_echoes_candidates - BUG-003（已修复，哨兵保留）...
XPASS ...::test_bug004_m001_default_parser_reaches_core_ai - BUG-004 已由 Task-012 修复...
GREEN_EXIT=0
```

#### 5.9.3 全量回归（D1 后）

```
$ .\.venv\Scripts\python.exe -m pytest -q --junitxml=.junit_task013_d1.xml
........................................................................ [ 30%]
.............................X..X....................................... [ 60%]
........................................................................ [ 91%]
.....................                                                    [100%]
EXIT=0

tests=237 failures=0 errors=0 skipped=0
```

（较 §5.5 的 236 增 1 —— 来自并行的 `Task-012`（`m001-dev`）新增用例，**非本任务改动**；`.junit_task013_d1.xml` 临时文件已删除。`read_lints`（改动文件）= 0。）

#### 5.9.4 写区合规（D1）

- 本次（D1）改动 = `backend/tests/e2e/test_acceptance_scenarios.py`（断言 + docstring）；`backend/app/core/ai/providers/mock.py` **仅在红证期间临时回退、已还原** → 均在授权写区（`backend/app/core/ai/**` + `backend/tests/**`）。
- **未触碰**：`modules/m001/**`、`modules/m002/**`、`frontend/**`、契约文本、治理文档、`docs/changes/BUG-003.md`（该文件回填归 PM）。

## 5D. PM 复核（2026-09-10，独立复现）

**结论：修复成立（Fixed）**；`Task-013-D1`（API 面证据补强）已于 §5.9 补齐并经 §5D.3 复核成立 → **本任务收口**。

- **全量复现**：`pytest -q -rxX --junitxml=.pm_review_task013.xml` → `tests=236 failures=0 errors=0 skipped=0`、`EXIT=0`；2 例 XPASS（`BUG-003` 哨兵 + `BUG-004` 哨兵）。与执行方汇报一致。
- **红→绿 PM 亲手复现**：`mock.py:143` 临时回退为 `candidate_subjects` → `tests/e2e/test_bug003_link_keys.py` = `FFF.F`（`4 failed / 1 passed`、`RED_EXIT=1`）→ 还原后 `5 passed` + `test_acceptance_ai_wiring.py` `3 passed / 2 xpassed`（`GREEN_EXIT=0`）→ **真红真绿，采纳**（非事后补绿）。
- **测试代码审读**：5 例均经真实装配路径；键位合同用例的 context 取自捕获 Provider 的**真实注入**（非手写）→ 符合 §3.2/§3.3；`test_scenario6` 双 `lru_cache` 泄漏定位与修复合逻辑，未删用例。
- **写区核验**：实际写入面 = `backend/app/core/ai/providers/mock.py` + 4 个 `backend/tests/**` 文件 → 全部落在授权写区；`docs/changes/BUG-003.md` 由 PM 回填（见下）。

### 5D.1 张力裁决：§5A 交付物 × §8 禁改治理文档

- **事实**：§5A 交付物列「修订 `BUG-003.md` §7」，§8 又禁改治理文档 → 冲突**源于 PM 签发时自检缺失**（交付物越出写区），非执行方问题。
- **执行方处置正确**：不擅自改 + 显式报备（§5.8）= **加分行为**。
- **裁决**：`BUG-003.md` §7.1 由 **PM 回填**（已完成），执行方**不得**再改该文件；后续任务书自检「**交付物 ⊆ 写区**」。
- **文档缺陷**：本任务书原存在两个「§5」（交付物 / 修复过程）→ 交付物已改编号为 **§5A**，DoD 所述「§5 修复过程与证据」= 现 §5。

### 5D.2 `Task-013-D1`（已完成，见 §5.9；仍属授权写区，不属扩面）

**缺口**：BUG-003 症状在 **API 面**（`GET /photos/{id}/link-suggestions`），现有证据只到 **service 面**（`AIService` 装配）→ 分层证据不可跨域替代。

1. `tests/e2e/test_acceptance_scenarios.py::test_scenario5_...`：补最小断言（`status == "suggested"` + `suggestions` 非空 + `group_subject_id` 与播种一致），**不重写剧本语义**（手工挂接流程保持），并附红→绿取证。
2. `m002_ai_port` fixture docstring：注明**前提已由 BUG-003 修复消除**、不得再作长期证据、去留由 `Task-014` 决定（**不现在删**）。

### 5D.3 `Task-013-D1` 复核：**成立**（PM 亲手红→绿，2026-09-10）

- **审读断言与依据**：`test_scenario5_*` 追加的 4 行断言 + 字段依据（`LinkSuggestionOut{photo_id,status,suggestions[]}`；`_seed_window_day` 播种「数学：练习册 P23 第 1-10 题」→ 该 day 窗口**唯一**学科子任务 → `== [gs]` 成立；`_recompute_photo_status` → `SUGGESTED`）**逐条读码核对通过**，无臆造；`_accept` 手工挂接 / 门控 / 生成 / 确认链路**未被改写**（diff 审读确认）。
- **红→绿 PM 亲手复现（D1）**：`mock.py:143` 临时回退为 `candidate_subjects` → 用例 `F`（失败点 = `assert body["status"] == "suggested"`，实测 `unassigned` + `suggestions == []`，`RED_EXIT=1`）→ **还原后** `.`（`SCEN5_EXIT=0`）→ **真红真绿**，非事后补绿。
- **全量（D1 后，PM 实测）**：`pytest --tb=no -q --junitxml=.pm_check.xml` → **`tests=237 failures=0 errors=0 skipped=0`、`EXIT=0`**（较 §5.5 +1 = `Task-012` 新增用例）；2 例 XPASS 仍为 `BUG-003`/`BUG-004` 哨兵。临时 xml 已清理（`Get-ChildItem *.xml` 无残留）。
- **还原核验**：`Select-String 'context.get("candidates", []) or []'` 计数 = **1**（`mock.py:143`），无 `candidate_subjects` 取值残留。
- **遗留转办**：`m002_ai_port` 替身保留（docstring 已标注前提失效）→ **`Task-014` 去替身复审**处置（须以真实 AI 链路复跑「未确认挂接 → 409」）。
- **结论**：`Task-013` **收口**（`Fixed`）；`BUG-003` 待 `Task-014` 复审通过后置 **Verified**。

## 6. 不在本任务范围

- `BUG-004` → `Task-012`（`AGENT-M001`）。
- ④ 复审（剧本 4/5 AI 全链真机 + **去替身**的 409 门控边界 + 浏览器级复跑）→ PM 将在本任务与 `Task-012` 完成后签发 **`Task-014`**（`AGENT-M002`）。
