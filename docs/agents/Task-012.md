# Task-012 任务书 —— `BUG-004` 修复（链路 T 核心 AI 通路不可达）

- **Task ID**：Task-012 ｜ **Agent**：`AGENT-M001`（`m001-dev`）｜ **Module**：M001（链路 T）
- **签发**：Project Master，2026-09-10 ｜ **状态**：**已交付 → PM 复核 = 修复成立（`Fixed`）**；`BUG-004` 待 `Task-014` 后 Verified ｜ **Kind**：**缺陷修复（`BUG-004`，高）**
- **启动前置（已满足）**：M001 契约 **v0.2.0 Frozen**；`Task-007` 已完成（PM 复核 APPROVED）；`BUG-004` 已由 PM 复核 **Confirmed**（根因经读码确认，见 `docs/changes/BUG-004.md` §7）。
- **契约影响**：**无**（实现侧调用方式错位，契约文本、API 面、数据模型均不变 → 不需 CR）。
- **写区（授权）**：`backend/app/modules/m001/services/task_parser.py`（主改）＋ `backend/tests/**`（M001 侧用例：新增 / 修订）＋ **`backend/app/modules/m001/services/task_service.py`（PM 裁决 A 扩权，**仅限** `ingest` 内解析调用下传 `session`，见 §3.5）**。
- **禁止改**：`backend/app/core/ai/**`（归 `AGENT-AI` / `Task-013`）、`backend/app/modules/m002/**`、`frontend/**`、任何契约文本（M001/M002 `MODULE_API.md`）、治理文档（除 `docs/agents/Task-012.md` 过程记录）。

## 1. Objective（目标）

使 M001 链路 T 的任务解析**真正经 `app/core/ai.parse_task_spec`** 执行（AI 通路可达），消除 `TypeError` 被静默吞掉导致的「本地启发式兜底伪装成 AI 解析」；并让降级路径**可观测**。

## 2. Root Cause（PM 读码确认，勿再自行推断）

| # | 环节 | 证据（PM 复核原文） |
| --- | --- | --- |
| 1 | 便捷入口签名 | `backend/app/core/ai/service.py:556`：`def parse_task_spec(session: Session \| None, **kwargs: Any)` → `get_ai_service().parse_task_spec(session, **kwargs)`；`AIService.parse_task_spec`（`service.py:127-135`）要求 `sources` 为 **keyword-only** |
| 2 | M001 以位置参数调用 | `backend/app/modules/m001/services/task_parser.py:132`：`coerced = _coerce_draft(parser(sources))` → `sources` 被当作 `session`，缺 `sources` 关键字 → `TypeError: missing 1 required keyword-only argument: 'sources'` |
| 3 | 异常被静默吞掉 | `task_parser.py:135-136`：`except Exception: pass` → 直接落到 `mock_parse_sources` 本地兜底（无日志、无痕迹） |
| 4 | 类型不匹配（次因） | M001 传 `list[dict]`，`AIService` 要求 `list[SourceInput]`（dataclass）→ 即使修正为关键字调用仍需转换 |

## 3. 修复要求

1. **关键字调用 + 类型转换**：以 `parser(session, sources=[...])` 形式调用，并把 M001 的 `list[dict]` 转为 `app/core/ai/types.py` 的 `SourceInput`（**先读码确认字段名**，不得臆造）。**`session` 由 §3.5 裁决下传**（生产路径非 `None`；离线/无会话场景仍允许 `None`）。
   - 允许实现为 `_ai_parser()` 返回**已适配的包装函数**（`Callable[[list[dict]], Any]`），使 `default_parser` 调用处保持简洁；两种实现任选，但须在过程记录中说明。
2. **降级可观测**：`except Exception:` 不得再 `pass` —— 改为 `logger.warning("task_parser: 核心 AI 解析降级（%s）", exc)` 后**保持降级语义**（仍回退 `mock_parse_sources`，**不污染事实层**，契约 §F1 降级不变）。
3. **降级边界不变**：AI 不可用 / 返回不合规 / 超时 → 仍返回本地兜底或 `None`（图片源在 Mock 无视觉密钥时**保持 `placeholder`、`contents == []`**，**不得伪造草稿**）。
4. **不得越界**：本任务**不修** `BUG-003`（Mock 挂接建议 key 错位，属 `app/core/ai/`，见 `Task-013`）。

### 3.5 PM 裁决（2026-09-10，DoD×写区 张力 → 采纳 A）

**张力**：§3.1 原指示 `parser(None, sources=[...])`（session 传 `None`），但 DoD bullet1 要求 `ai_call_records` 落条 —— 而 `app/core/ai/records.py:72-75` 在 `session is None` 时**直接跳过写入**，物理上不可同时满足；`task_service.py:178` 原样只传 `sources`，session 未下传。

**PM 读码核实**：`records.py:72-75` 跳过语义属实；`task_service.ingest` 作用域内 `session` 可得（`TaskRepo.add_sources(session, ...)` 即用）；`default_parser` **生产唯一调用点 = `task_service.py:177-178`**（无其他隐式调用）。

**裁决：采纳 A（扩权）** —— 以真机生产路径取证，优于降级为用例级证据：

1. 扩权范围 = `task_service.py:178` 改为 `parser_fn(norm_sources, session=session)`（+ 必要 import）；该文件其余语义**一行不动**。
2. `default_parser(sources, *, session: Session | None = None)`：`session` **keyword-only、默认 `None`**（类型宜用 `TYPE_CHECKING` 引入）。
3. **调用约定统一、严禁静默兜底**：`Parser` 别名同步放宽（`Callable[..., ...]` 或 `Protocol`）并在 docstring 写明「位置 `sources` + 关键字 `session`」；**禁止** `try/except TypeError` 兼容旧签名（`BUG-004` 教训）；仓库内自定义 parser（含测试注入）**须显式改签名**。
4. `app/core/ai/**` **一行不改**（含 `records.py` 跳过语义）。
5. 降级语义与边界不变（`logger.warning` + 回落 `mock_parse_sources`，不抛错、不污染事实层）；下传 `session` 不改变 `spec_status`/`contents` 写入语义。
6. 取证：**服务级真机用例**（经 `TaskService.ingest` 生产路径 → `spec_status == "parsed"` 且 `ai_call_records` 落条）+ parser 级单测（转换 + 降级 warning）。
7. 若需大于「1 行下传 + 签名扩展 + 别名放宽」的改动 → 停下回报，不得擅自扩面。

> 注：`record_call` 复用同一 `session.flush()`，随 `ingest` 事务一并提交/回滚，属预期行为。

## 4. DoD（交付判定）

- [ ] 链路 T 文本源经 `app/core/ai` 解析生效：任务 `spec_status == "parsed"`，且 **`ai_call_records` 写入对应记录**（`capability` / `prompt_version` / `model` 可取原文）—— 证明 AI 真跑，而非本地兜底；**取证路径必须为生产路径**（经 `TaskService.ingest`，非手工注入 session 绕过）
- [ ] `backend/tests/e2e/test_acceptance_ai_wiring.py` 的 `BUG-004` 两例处置：
  - `test_bug004_m001_default_parser_reaches_core_ai`：**xfail → XPASS**（修复后自然转绿；不得删除或放宽 `strict`）
  - `test_bug004_evidence_signature_mismatch_and_silent_fallback`：该用例断言「必然 `TypeError` + 兜底等价于 `mock_parse_sources`」，修复后**前提失效** → 按新实现改写为**修复后取证**（如：经 `app/core/ai` 通路成功、降级时写 warning 日志、`ai_call_records` 落条），并在过程记录说明改动理由
- [ ] M001 侧新增/修订断言：解析元数据（`spec_status` / `contents` / `ai_call_records`）至少 1 例
- [ ] 全量 `pytest`：**0 failed**，用例数**不低于 227**（不得删减既有用例；`xfail→XPASS` 会使 xfailed 数减少，属预期）
- [ ] `read_lints` = 0；`git diff --name-only` **仅限授权写区**（超出即视为越界）
- [ ] 过程记录：`docs/agents/Task-012.md` 追加「§5 修复过程与证据」（命令 + 原文输出 + 红→绿对照）

## 5A. 交付物（签发时清单）

代码改动（授权写区内）、用例（新增 / 修订）、本文档 §5 过程记录、修订后 `docs/changes/BUG-004.md`（**§7 追加「修复记录」**，状态由 PM 复核后置 **Verified**）。

## 6. 不在本任务范围

- `BUG-003`（Mock 挂接建议 key）→ `Task-013`（`AGENT-AI`）。
- `TD-001`（`get_group_subject` 全量扫描 N+1）/ `TD-002`（契约未暴露 `window_task_id`/`task_status`）→ 不在本任务修复。
- ④ 复审（去桩 + 剧本 4/5 真机 + 浏览器级）→ PM 将在本任务与 `Task-013` 完成后签发 `Task-014`（`AGENT-M002`）。

## 5. 修复过程与证据（`AGENT-M001` / `m001-dev` 回填，2026-09-10）

### 5.1 红取证（修复前）

命令 1（强制运行 xfail 用例，取真实失败原文）：

```
cd backend
.\.venv\Scripts\python.exe -m pytest "tests/e2e/test_acceptance_ai_wiring.py::test_bug004_m001_default_parser_reaches_core_ai" --runxfail -v
```

原文（节选）：

```
>       assert errors == [], f"核心 AI 通路抛错并被 `except Exception: pass` 静默兜底：{errors}"
E       AssertionError: 核心 AI 通路抛错并被 `except Exception: pass` 静默兜底：['TypeError']
E       assert ['TypeError'] == []
FAILED tests/e2e/test_acceptance_ai_wiring.py::test_bug004_m001_default_parser_reaches_core_ai
======================== 1 failed, 1 warning in 0.35s =========================
EXIT=1
```

命令 2（直击根因：位置调用 + 兜底等价性）：

```
.\.venv\Scripts\python.exe -c "from app.modules.m001.services.task_parser import _ai_parser, default_parser, mock_parse_sources; p=_ai_parser(); src=[{'kind':'text','text_content':'数学：练习册 P23'}]; print('mock  =', mock_parse_sources(src)); print('default=', default_parser(src));
try:
    p(src)
except Exception as e:
    print('POSITIONAL CALL ->', type(e).__name__, ':', e)"
```

原文：

```
parser = <function parse_task_spec at 0x0000022D41517380>
mock  = [ContentDraft(subject='math', text='练习册 P23')]
default= [ContentDraft(subject='math', text='练习册 P23')]
same_as_mock= True
POSITIONAL CALL -> TypeError : AIService.parse_task_spec() missing 1 required keyword-only argument: 'sources'
```

→ 证实：位置调用必 `TypeError`；异常被静默吞掉后 `default_parser` 结果与本地 `mock_parse_sources`
**逐字相同**（本地启发式兜底伪装成 AI 解析）。

### 5.2 改动清单（授权写区内）

| 文件 | 改动摘要 |
| --- | --- |
| `backend/app/modules/m001/services/task_parser.py` | ① 新增 `_to_ai_sources()`（`list[dict]` → `SourceInput`）；② 新增 `_iter_texts()` 并增强 `_coerce_draft()`（支持 `ParsedContentItem.text` 对象）；③ `default_parser(sources, *, session=None)` 改**关键字** `sources=` 调用 + `logger.warning` 降级；④ `Parser` 由 `Callable[[list[dict]], ...]` 放宽为 `Protocol`（调用约定 = 位置 `sources` + 关键字 `session`）；⑤ `Session` 经 `TYPE_CHECKING` 引入 |
| `backend/app/modules/m001/services/task_service.py:178` | `parser_fn(norm_sources)` → `parser_fn(norm_sources, session=session)`（**仅 1 行**）。**扩权与采纳依据：PM 2026-09-10 裁决「采纳 A」** —— 读码三点：`core/ai/records.py:72-75`（`session is None → return None`）、`task_service.py:178` 未下传而 `session` 正在作用域内、`default_parser` 生产唯一调用点 = `task_service.py:177-178`（无其他隐式调用）→ 1 行扩权换取 DoD 字面满足 + **真机路径取证**，收益 > 成本。该文件其余语义（事实层 / 聚合 / 审计 / 幂等）**一行未动** |
| `backend/tests/unit/test_task_parser_ai_path.py` | **新增 4 例**：AI 真跑 + `ai_call_records` 落条 / AI 产物被消费（≠本地兜底）/ 降级 warning / 图片源保持 `placeholder` |
| `backend/tests/api/test_tasks_ai_parse_records.py` | **新增 1 例**：**生产路径**（`POST /tasks` → `TaskService.ingest`，**非手工注入 session**）→ `spec_status=="parsed"` + `ai_call_records` 落条，并逐字断言 `capability`(`task_spec_parse`) / `provider_kind`(`llm`) / `prompt_key` / `prompt_version` / `model`(`mock-llm`) / `mock is True` / `request_id`（常量引自 `app/core/ai/`，非臆造） |
| `backend/tests/e2e/test_acceptance_ai_wiring.py` | `BUG-004` 两例处置（见 §5.6） |

### 5.3 关键实现决策

1. **关键字调用 + 类型转换**：`parser(session, sources=ai_sources)` —— `session` 走位置、`sources` 走关键字
   （`AIService.parse_task_spec` 中 `sources` 为 keyword-only）；`ai_sources` 由 `_to_ai_sources()` 产出
   `app/core/ai/types.py::SourceInput`（字段：`kind` / `text` / `image`，**读码确认，未臆造**）。
2. **`_coerce_draft` 增强（原次生缺陷）**：原实现对 `subjects[].contents[]` 只识别 `str` / `dict`，
   而 AI 真实产物为 `ParsedContentItem`（`.text`）→ 会静默判为「不合规」再回落兜底。新增 `_iter_texts()`
   兼容 `str` / `dict{"text"}` / 对象（`.text`），确保 **AI 产物被真正消费**。
3. **降级可观测**：`except Exception:` 不再 `pass`，改为
   `logger.warning("task_parser: 核心 AI 解析降级（%s）", exc)`，随后**保持降级语义**（回落 `mock_parse_sources`，
   不抛错、不污染事实层）。
4. **图片源不转发（§3.3 边界）**：M001 `photo_id` 仅存引用（照片实体 Owner = M002，本层无字节/路径），
   硬转发会在 Mock 无视觉密钥时产出占位草稿（伪造）；故 `_to_ai_sources()` **只转发文本源**，
   图片源保持 `placeholder` / `contents == []`。真实 Provider 的图片 OCR 分支仍需图片字节，属后续范围。
5. **session 下传（裁决 A）**：`default_parser(..., *, session)` keyword-only、默认 `None`；
   生产唯一调用点 `task_service.ingest` 下传请求会话 → `ai_call_records` 随同事务 `flush`/提交。
   未采用 `try/except TypeError` 兼容旧签名（`BUG-004` 教训）。

### 5.4 绿取证（修复后）

命令：

```
.\.venv\Scripts\python.exe -m pytest tests/e2e/test_acceptance_ai_wiring.py -v -rx
```

原文（节选）：

```
tests\e2e\test_acceptance_ai_wiring.py X..X.                             [100%]
=================== 3 passed, 2 xpassed, 1 warning in 0.11s ===================
EXIT=0
```

→ `BUG-004` 目标例由 `xfail` 自然转 **XPASS**（`strict=False` 标记保留未放宽；另一 `X` = `BUG-003`，由 `Task-013` 修复）。

命令：

```
.\.venv\Scripts\python.exe -m pytest tests/api/test_tasks_ai_parse_records.py tests/unit/test_task_parser_ai_path.py tests/unit/test_task_parser.py -v
```

原文（节选）：

```
tests\api\test_tasks_ai_parse_records.py .                               [ 10%]
tests\unit\test_task_parser_ai_path.py ....                              [ 50%]
tests\unit\test_task_parser.py .....                                     [100%]
======================== 10 passed, 1 warning in 1.26s ========================
EXIT=0
```

### 5.5 全量回归

```
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

原文：

```
============ 235 passed, 2 xpassed, 1 warning in 88.53s (0:01:28) =============
EXIT=0
```

（合计 237 例 = 235 passed + 2 xpassed；`failures=0` / `errors=0`；用例数 ≥ 227，未删减既有用例；
`xfail→XPASS` 使 xfailed 归零，属预期。）

### 5.6 `BUG-004` 两例处置

- `test_bug004_m001_default_parser_reaches_core_ai`：**保留 `xfail(strict=False)` 标记未动**，修复后自然转 **XPASS**；
  仅更新 `reason` 文案为「已由 Task-012 修复 → 应 XPASS，作回归哨兵」。
- `test_bug004_evidence_signature_mismatch_and_silent_fallback`：原断言「必然 `TypeError` + 兜底结果**逐字等于**
  `mock_parse_sources`」在修复后前提失效 → 按新实现改写为**修复后取证**：① 位置调用**仍**必然 `TypeError`
  （说明修复点 = 改走关键字）；② 默认路径经核心 AI 真跑（断言入参已适配为 `SourceInput` 且以 keyword 传递）；
  ③ 降级可观测（`caplog` 断言 warning + 兜底结果不变）。**函数名保留**以维持追溯性（沿用 `BUG-003` 取证例的处理约定）。

### 5.7 写区合规自证

- `git --no-pager diff --name-only -- backend/app frontend/src` 原文：

```
backend/app/api/v1/deps.py
backend/app/api/v1/tasks.py
backend/app/core/config.py
backend/app/main.py
backend/app/modules/m001/models/orm.py
backend/app/modules/m001/repositories/task_repo.py
backend/app/modules/m001/schemas/task.py
backend/app/modules/m001/services/task_service.py
```

  > 说明：上列多数为 `CHANGE-003` **既有**未提交改动（`task_service.py` 等），非本任务引入；
  > `task_parser.py` 为**未跟踪新文件**故不出现在该命令中，以 mtime 审计为准。
- mtime 审计（本次会话写窗口 `2026-09-10 20:00` 之后，`backend/app/**/*.py`）：

```
2026/9/10 20:11:26  backend/app/modules/m001/services/task_parser.py
2026/9/10 20:11:26  backend/app/modules/m001/services/task_service.py
2026/9/10 20:13:06  backend/app/core/ai/providers/mock.py   ← Task-013（AGENT-AI）并发写入，非本任务
```

  > 本任务对 `backend/app` 的写入 = `task_parser.py` + `task_service.py`（后者仅 §5.2 所述 1 行）；
  > `frontend/src` **零写入**；`app/core/ai/**`、`modules/m002/**`、契约文本、治理文档**零写入**。

### 5.8 遗留说明

1. **首次全量运行的 1 次失败为并发抖动**：首次运行 `tests/e2e/test_acceptance_scenarios.py::test_scenario6_llm_unavailable_keeps_unassigned_then_manual_link_api_level`
   失败 1 次；该例**单跑通过**、随后两次全量运行均通过；且 `app/core/ai/providers/mock.py` 于运行窗口内被 `Task-013`
   并发写入 → 判定为并发写入抖动，非本任务回归。
2. **图片源 OCR 分支仍不可达**：M001 侧无图片字节（`photo_id` 仅引用），需后续任务打通取图链路；
   本任务按要求保持 `placeholder` / `contents == []`，不伪造草稿。
3. **`docs/changes/BUG-004.md`**：按任务书 §5 交付物 + PM 2026-09-10 指令「`BUG-004.md §7 修复记录` 照旧追加」，
   已追加「**§7.1 修复记录（Task-012 执行方回填）**」；状态**保持 `Confirmed`**，由 PM 复核后置 `Verified`。
   （备注：该文件不在任务书授权写区，与 `BUG-003.md` 同类情形；执行方按 PM 显式指令追加并在此报备，
   若 PM 更倾向「变更文档由 PM 独揽回填」，可直接撤回该 §7.1。）

### 5.9 对 PM 7 条硬约束的逐条对照

| # | 硬约束 | 落实情况 |
| --- | --- | --- |
| 1 | 扩权仅限 `task_service.py:178`（+必要 import），其余一行不动 | ✅ 该文件仅 `:178` 一行改动（`git status` ` M`，mtime 同刻；未新增 import）；事实层/聚合/审计/幂等未动 |
| 2 | 签名 `default_parser(sources, *, session: Session \| None = None)`，`TYPE_CHECKING` 引入 | ✅ `session` keyword-only、默认 `None`；`from typing import TYPE_CHECKING` + `if TYPE_CHECKING: from sqlalchemy.orm import Session`，运行时零耦合 |
| 3 | `Parser` 别名同步放宽 + docstring 写明约定；**严禁** `try/except TypeError` 兼容旧签名；仓库内自定义 parser 须显式改签名 | ✅ `Parser` 由 `Callable[[list[dict]], ...]` 改 **`Protocol`**（`__call__(sources, *, session=None)`，类 docstring 写明「位置 `sources` + 关键字 `session`」）；**无任何 `try/except TypeError`**；全仓复查 `parser=` 注入点 = **0**（无 `lambda sources: ...`），`_ai_parser` 桩均为 `spy(session, **kwargs)` 新签名 |
| 4 | `app/core/ai/**` 一行不改（含 `records.py` 跳过语义） | ✅ 零写入；未改 `record_call`；`session=None` 跳过语义原样（仅由生产路径传真实 session） |
| 5 | 降级语义与边界不变；下传 session 不改 `spec_status`/`contents` 语义 | ✅ `logger.warning` + 回落 `mock_parse_sources`，不抛错、不污染事实层；图片源仍 `placeholder` + `contents == []` |
| 6 | 取证体现 A 的收益：① 服务级真机（经 `TaskService.ingest`）→ `spec_status=="parsed"` 且 `ai_call_records` 落条（`capability`/`model`/`prompt_version`/`mock` 可取原文）；② parser 级单测（`SourceInput` 转换 + 降级 warning）；③ 两例 `xfail → XPASS` 不变 | ✅ ① `tests/api/test_tasks_ai_parse_records.py`（`POST /tasks` → `ingest`，逐字断言 7 字段）；② `tests/unit/test_task_parser_ai_path.py` 4 例；③ e2e `X..X.` = 3 passed / 2 xpassed（`xfail` 标记未删/未放宽） |
| 7 | 不得擅自扩面；若还有其他生产调用点或需更大改动 → 停下回报 | ✅ 复查：`default_parser` 生产唯一调用点 = `task_service.py:177-178`（`grep` 全仓无其他）；本次改动 = 「1 行下传 + 签名扩展 + 别名放宽」，未扩面 |

> PM 附注（`record_call` 用同一 `session.flush()`，随 `ingest` 事务提交/回滚）= 属预期，未做额外处理。

## 5D. PM 复核（2026-09-10，独立复现）

**结论：修复成立（`Fixed`）** —— 本任务符合 §3.5 全部 7 条硬约束；`BUG-004` 待 `Task-014` 复审后置 `Verified`。

- **全量（PM 实测）**：`pytest --tb=no -q --junitxml=.pm_check.xml` → **`tests=237 failures=0 errors=0 skipped=0`、`EXIT=0`**（含本任务新增 5 例）；`BUG-004` 哨兵 **XPASS**；临时统计文件已清理。
- **根因机制 PM 只读复现**（未做多行还原，避免扰动共享树；以「机制复现 + 用例判别力审读」替代整体回退）：
  `python -c "from app.core.ai.service import parse_task_spec as cp; cp([{'kind':'text','text_content':'math:x'}])"` → **`TypeError: AIService.parse_task_spec() missing 1 required keyword-only argument: 'sources'`、`PY_EXIT=1`** → 证实「旧调用形状必失败」，与 §5.1 红证一致。
- **取证用例审读（未放宽、有判别力）**：
  - `tests/api/test_tasks_ai_parse_records.py`：**经 `POST /tasks` → `TaskService.ingest` 生产路径**（未手工注入 session）；`capability` / `prompt_key` / `prompt_version` / `model` / `mock` / `request_id` 常量**引自 `app/core/ai/`，非臆造**。**判别力成立**：修复前 `TypeError` 发生在进入 `AIService` **之前** → `ai_call_records` 为 **0 行**，本用例必失败（非「形状恒真」型断言）。
  - `tests/unit/test_task_parser_ai_path.py`：AI 产物被**真正消费**（stub 结果与本地兜底**不同** → 排除静默回落）、降级 `logger.warning` 可观测、图片源返回 `None`（**不伪造**草稿，§3.3 边界守住）。
  - `test_bug004_m001_default_parser_reaches_core_ai`：`xfail(strict=False)` 装饰器与 `strict` **未删未放宽**（仅 `reason` 文案更新）→ 自然 **XPASS**。
  - `test_bug004_evidence_signature_mismatch_and_silent_fallback`：改写后**仍保留**「位置调用必 `TypeError`（`sources` keyword-only）」「降级 warning」「兜底结果与 `mock_parse_sources` 逐字相等」三组断言 → **未被弱化**，函数名保留维持追溯性。
- **代码审读**：`Parser` 已为 `Protocol`（docstring 写明「位置 `sources` + 关键字 `session`」）；全仓 `default_parser(` 调用点 5 处**均为关键字兼容**形态；M001 内**无** `try/except TypeError`；`task_service.py` 仅 `:178` 一行下传（`:144` 的 `parser: Parser | None` 参数属 `Task-007` 既有基线）。
- **更正（重要，防错误知识留档）**：§5.8.1 将首轮 1 failed 归因为「`Task-013` 并发写入抖动」**不成立**。真实根因 = `core/ai/config.py:62-64`（`get_ai_settings`）与 `core/ai/service.py:550-552`（`get_ai_service`）**双 `lru_cache` 跨用例泄漏**（前序 scenario 经 `real_stack` 缓存 **auto/Mock** 配置 → scenario6 实际走 Mock），由 `Task-013` 定位并在 `real_stack` teardown / scenario6 内补 `clear_settings()` 修复。**以本结论为准**（代码无需再改，PM 已更正文档）。
- **§5A / §8 张力裁决**：§5A 交付物列「修订 `docs/changes/BUG-004.md` §7」而 §8 禁改治理文档 → 冲突归 **PM 签发自检缺失**（与 `Task-013` 同一根因）；执行方「按交付物条款追加 + 显式报备 + 主动提出可撤回」= **正确（加分）**。裁决：**保留**该 §7.1，状态由 PM 置位（已完成）。
- **PM 连带发现（已登记）**：`modules/m002/clients/task_client.py:213-216` 的 `except TypeError: # 兼容位置/少参签名` = **签名兼容垫片**（与 `BUG-004` 教训同型、与 `BUG-002` 的 `FakeGateway` 同类陷阱）→ 登记 **`TD-003`**，处置并入 `Task-014`（M002 写区）或后续触碰时清理。
- **写区核验**：改动面 = `task_parser.py`（重写）+ `task_service.py:178`（**1 行**，PM 裁决 A 扩权）+ `backend/tests/**` 3 个新/改用例 → **全部在授权写区**；`app/core/ai/**`、`modules/m002/**`、`frontend/**`、契约文本**零写入**（`git status --porcelain` + mtime 审计佐证；`task_parser.py` 为未跟踪新文件，不入 `git diff`）。
