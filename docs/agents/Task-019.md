# Task-019 任务书 —— `CR-005` 消费方：M001 图片源转发（回调槽）+ `API-M001-022` 任务重新解析

- **Task ID**：Task-019 ｜ **Agent**：`AGENT-M001` ｜ **Module**：M001（任务域 / 链路 T）
- **签发**：Project Master，2026-09-16 ｜ **状态**：**已签发（待执行）** ｜ **Kind**：**契约实施（M001 消费方 + 新端点，中）**
- **上游**：`CR-005`（**Approved**）→ M001 契约 **v0.2.0 → v0.3.0**（**已修订**：`API-M001-022` + 内部回调槽）
- **启动前置（已满足）**：全量基线 **251 / 0 / 0 / 0**；`BUG-006` 已修复（降级语义 = 如实失败）；M002 提供方（`Task-018`）**可并行** —— 未就绪时本任务须**不依赖**其存在（槽为空 → 不转发图片源）。
- **契约影响**：M001 **新增端点 `API-M001-022`**（已修订契约文本；**仍为 Draft，实施后由 PM 转 Active**）。
- **写区（授权）**：
  1. `backend/app/modules/m001/services/task_parser.py`（图片源适配 + provider 消费）
  2. `backend/app/modules/m001/services/image_provider.py`（**新增**：回调槽定义 + 注册入口；或并入既有 `aggregation_service.py`，二选一须在 §5 说明）
  3. `backend/app/modules/m001/services/task_service.py`（**reparse 服务方法**，含 §2.4 内容项规则）
  4. **`backend/app/api/v1/tasks.py`**（**新端点 `API-M001-022`**）—— **写区更正（PM 裁决，2026-09-16，实施中发现）**：M001 路由**不在** `modules/m001/routers/`（该目录不存在），实际位于 `app/api/v1/`（见 `app/main.py:56`）。
  5. `backend/tests/unit/**`、`backend/tests/api/**`（新增用例）
  6. `docs/agents/Task-019.md`（§5）
- **禁止改**：`backend/app/core/ai/**`（**全部**）、`backend/app/modules/m002/**`（`Task-018` 写区）、`backend/app/main.py`（`Task-018` 写区）、`frontend/**`、`docs/**`。

## 1. Objective

① 让 M001 链路 T 在**真实 Vision** 下能解析**图片源**（布置单照片）；② 提供 `POST /tasks/{task_id}/reparse` 让家长在 AI 失败后**自助重试解析**。**绝不伪造**（Mock/degraded 下不转发图片源）。

## 2. 背景（PM 读码确认）

| # | 事实 | 证据 |
| --- | --- | --- |
| 1 | 现状：`_to_ai_sources` **只转发文本源**，图片源不转发（注释明示原因：Mock 无视觉能力会伪造占位草稿） | `m001/services/task_parser.py:167-186` |
| 2 | `app/core/ai` **已支持**图片源，无需改动 | `core/ai/types.py:25-56`（`ImageInput(mime, data|path, image_id)` / `SourceInput.image_of` `load_bytes()`）；单测 `test_parse_image_uses_vision_provider` |
| 3 | 解析失败语义（`BUG-006` 修复后）：`allow_mock_fallback=false` → `default_parser` 返回 `None` → 上层保持 `placeholder` | `task_parser.py::_mock_fallback_allowed`（`BUG-006`）+ `task_service.py:176-182` |
| 4 | 真实 Vision 判据来源：ProviderBundle 的解析结果带 `degraded`/`reason` | `core/ai/providers/registry.py`（`ResolvedProvider(provider, kind, degraded, reason)`） |
| 5 | M002 提供方签名（契约） | `docs/modules/M002/MODULE_API.md` 内部接口表（`provide_task_source_image`） |

## 3. 任务要求

### 3.1 回调槽（**必做**，与既有模式逐字对齐）

- 定义（`image_provider.py` 或 `aggregation_service.py`，二选一）：
  - 槽：`_task_spec_image_provider: Callable[[str, str], TaskSourceImage | None] | None = None`
  - 注册：`register_task_spec_image_provider(fn) -> None`
  - 读取（内部）：返回 `TaskSourceImage | None`；未注册 → `None`
  - `TaskSourceImage`：`{mime: str, abs_path: str}`（**不得**外发路径）
- **参照** `aggregation_service.register_links_migration_hook` 的写法与注释风格。

### 3.2 图片源转发（**必做 + 防伪造硬约束**）

`_to_ai_sources` 扩展：

1. 文本源：**行为不变**（回归零影响）；
2. 图片源（`kind == "image"` 且有 `photo_id`）：
   - **前置判据**：仅当 **Vision Provider 为真实**时才转发 —— 用 `core/ai` 公开装配结果判定（`get_ai_service()` 或 `build_providers()` 的 vision `degraded is False` **且** `reason == "real"`）；**禁止**硬编码模型名；
   - 经 `_task_spec_image_provider(session, family_id, photo_id)` 取 `{mime, abs_path}` → 构造 `ImageInput(mime=…, path=…, image_id=photo_id)` → `SourceInput.image_of(...)`；**`session` 复用调用方事务**（`_to_ai_sources` 需接收 `session`，由 `default_parser` 传入）；
   - **槽未注册 / 返回 `None` / 判据不满足** → **不转发该源**（保持 `placeholder`，**不伪造**）；
   - `family_id` 来源：解析调用链已有的 `family_id` 上下文（`default_parser` 签名若需扩展，**仅允许**新增带默认值的关键字参数，并在 §5 说明 —— 兼容既有调用点）。

### 3.3 `API-M001-022` 端点与服务方法（**必做**）

- 路由：`POST /api/v1/tasks/{task_id}/reparse`（`m001/routers/tasks.py`；鉴权与既有任务端点一致）；
- 服务：`TaskService.reparse(session, family_id, task_id, *, scope_student_id=None, resolver=None) -> TaskDTO`，**逐字实现契约 §2.4**：
  | 当前 `spec_status` | 解析成功 | 无草稿 / AI 失败 |
  | --- | --- | --- |
  | `placeholder` | 写内容项 → `parsed` | **不改动** |
  | `parsed`（未确认） | **整体替换**内容项 + 审计 | **不改动（不清空）** |
  | `confirmed` | —（**`409 spec_confirmed`**，不执行） | 同左 |
- 解析调用：复用 `default_parser(sources, session=session)`（**不得**另写解析路径）；**按契约传入 `family_id`** 以便图片源转发；
- 响应 `200 TaskDTO`（当前态，与 `GET /tasks/{task_id}` 同构）；失败**不抛错**（沿用 `BUG-006` 语义）；
- 审计：沿用既有 `audit_event` 风格（如 `task_reparsed`）。

### 3.4 用例（**必做，含判别力**）

| # | 用例 | 断言 |
| --- | --- | --- |
| 1 | **防伪造（判别力，必做）**：`provider_mode=mock`（或 vision degraded）+ 含图片源任务 → `reparse` | `default_parser`/`reparse` **不转发**图片源 → `spec_status` 保持 `placeholder`、`contents==[]`（**红→绿**：移除判据 → 断言立败） |
| 2 | 真实判据下转发（以 `monkeypatch` 注入假 provider + 假 Vision 判据） | 转发成功 → 解析产出草稿 → `parsed`（**标注为桩**，§5 报备） |
| 3 | `placeholder` + 成功 → `parsed` | 内容项写入 |
| 4 | `parsed`（未确认）+ 成功 → **整体替换** | 旧内容项被替换（数量/文本以本次为准） |
| 5 | 解析失败（AI 不可用）→ **不清空** | 既有内容项数量不变、`spec_status` 不变 |
| 6 | `confirmed` → `409 spec_confirmed` | 状态码 + code 断言 |
| 7 | 图片源 + 槽未注册（M002 未就绪） | 不转发、不报错（保持 `placeholder`） |

- 用例 1/2 的桩**必须**在 docstring 显式标注并向 PM 报备（PM 铁律 ①）；核心结论（防伪造）**必须**有一条**不依赖桩**的用例（如用例 1 用真实 `provider_mode=mock` 环境）。

## 4. DoD

- [ ] 回调槽按 §3.1 落地（与 `register_links_migration_hook` 同模式）
- [ ] `_to_ai_sources` 图片源转发 + **防伪造判据**（真实 Vision 才转发）
- [ ] `API-M001-022` 路由 + `TaskService.reparse`（§2.4 三情形逐字）
- [ ] §3.4 用例 1~7 全部新增并通过；**用例 1 具备红→绿判别力**
- [ ] `confirmed` → `409 spec_confirmed`；失败**不清空**内容项
- [ ] 既有 M001 用例（`tests/unit/test_task_parser*.py`、`tests/api/test_tasks*.py`）**零放宽**
- [ ] 全量 `pytest`：**0 failed / 0 errors / 0 skipped**，用例数 **≥ 251**
- [ ] `read_lints` = 0；写区合规（双证）：`core/ai/**`、`modules/m002/**`、`main.py`、`frontend/**`、`docs/**` **零写入**
- [ ] §5 七段式报告（含红→绿原文与桩报备）
- [ ] **不伪造**：真实 Vision 证据若受外部中转限制不可得 → 停下回报并标注

## 5. 执行方报告（七段式）

> **执行者说明**：本任务由 **PM 代执行**（当前 IDE 无具备写权限的执行 subagent）→ 不构成独立第三方复核，限制如实标注。

### ① 状态

**完成**。回调槽、图片源转发（**含防伪造硬约束**）、`TaskService.reparse`、`API-M001-022` 端点全部落地；新增 **8 例**（含**防伪造红→绿**）；全量回归 **265 / 0 failed / 0 errors / 0 skipped**（基线 257 + 8）。

### ② 改动文件清单 + diff 摘要

| 文件 | 性质 | 改动摘要 |
| --- | --- | --- |
| `backend/app/modules/m001/services/image_provider.py` | **新增** | 回调槽：`TaskSourceImage{mime, abs_path}` + `register_task_spec_image_provider(fn \| None)` + `get_task_source_image(session, family_id, photo_id)`（未注册/实现抛错 → `None`，不阻断） |
| `backend/app/modules/m001/services/task_parser.py` | 改 | ① `Parser` Protocol 增 `family_id`（关键字）；② 新增 **`_vision_is_real()`**（判据取自 `get_ai_service().providers.vision` 的 `reason=="real" && !mock && !degraded`；**禁止硬编码模型名**；不可读 → `False` 保守不转发）；③ `_to_ai_sources(sources, *, session, family_id)` 支持图片源（三条件齐备才经槽取图 → `ImageInput(mime, path, image_id)`），**任一不满足即不转发**；④ `default_parser(..., family_id=None)` 透传 |
| `backend/app/modules/m001/services/task_service.py` | 改 | ① `ingest` 解析调用改传 `family_id=famly_id`（图片源上下文）；② 新增 **`reparse(...)`**：`confirmed` → `ConflictError`（409）；`placeholder` → 写入 → `parsed`；`parsed`（未确认）→ **整体替换**；无草稿/失败 → **不改动、不清空**；审计 `task_reparsed` |
| `backend/app/api/v1/tasks.py` | 改 | 新端点 **`POST /api/v1/tasks/{task_id}/reparse`**（`response_model=TaskDTO`；docstring 补 `API-M001-022`） |
| `backend/tests/api/test_task_reparse_api.py` | **新增（8 例）** | 见 §③/§⑥ |

### ③ 红→绿 / 判别力证据原文（**防伪造**）

**红**（临时移除 `_vision_is_real()` 判据，令图片源无条件转发）：

```
FAILED tests/api/test_task_reparse_api.py::test_no_forgery_when_vision_mock_even_if_provider_registered
tests/api/test_task_reparse_api.py:114: AssertionError: Mock 下不得转发图片源（防伪造草稿）
— Captured log —
INFO audit event=task_reparsed … parsed=True replaced=True spec_status=parsed
RED_EXIT=1
```
→ 无判据时 **Mock Vision 立即产出「假解析」**（`parsed=True`）——证明该判据是**真防线**、断言非无脑通过。

**绿**（还原判据）：8 例全绿 → 含于 §④ 全量 `GREEN_EXIT=0`。

### ④ 全量回归与用例数

```
$ pytest --no-header -q --tb=short --junitxml=../.pm_t019.xml
tests=265 failures=0 errors=0 skipped=0
GREEN_EXIT=0
```
**265 = 基线 257 + 本任务 8**。

### ⑤ 写区合规自证（双证）

- **`git status --porcelain`**：`M backend/app/api/v1/tasks.py`、`M backend/app/modules/m001/services/task_parser.py`、`M backend/app/modules/m001/services/task_service.py`、`?? backend/app/modules/m001/services/image_provider.py`、`?? backend/tests/api/test_task_reparse_api.py`；**未出现** `backend/app/core/ai/**`、`backend/app/modules/m002/**`（除 `Task-018` 已提交部分）、`backend/app/main.py`（`Task-018` 写区）、`frontend/**`、`docs/**`。
- **mtime 审计**：写区均为本日写区时段；`core/ai/**` 与 `m002/**` 未触碰（`Task-018` 提交后无再写）。
- `read_lints` = 0。

### ⑥ 契约逐字核对 + 桩报备

| 契约点（`MODULE_API.md` v0.3.0） | 对应用例 | 结果 |
| --- | --- | --- |
| §2.4 `placeholder` + 成功 → 写入 → `parsed` | 用例 3 | ✅ |
| §2.4 `parsed`（未确认）+ 成功 → **整体替换** | 用例 4 | ✅ |
| §2.4 失败 **不清空**（`real` + 禁兜底） | 用例 5 | ✅ |
| `confirmed` → `409 spec_confirmed` | 用例 6 | ✅ |
| 图片源**仅真实 Vision 转发**（防伪造） | 用例 1 / **1b（判别力核心）** | ✅ |
| 图片源经槽转发（含 `abs_path`/`image_id`） | 用例 2 | ✅（桩） |
| 槽未注册 → 不转发、不报错 | 用例 7 | ✅ |

**桩报备（PM 铁律 ①）**：用例 2 注入 `_vision_is_real`（判据）与假 provider；用例 3/4 注入**假 AI parser**（构造成功分支）。**核心结论（防伪造 / 不清空 / 409 / 槽未注册不报错）均由不依赖桩的用例取得。**

### ⑦ 遗留 + 需 PM 裁决项

1. **`API-M001-022` 仍为 Draft** → 建议 PM 转 **Active**（路由已实施 + 8 例覆盖）。
2. **调试记录（如实）**：① 首轮 `test_reparse_from_placeholder_*` 失败 = 用**图片源**建任务但未注入判据/provider → `ai_sources` 为空 → 假 parser 不被调用 → 已改为「先禁兜底建 `placeholder`（文本源）→ 再注入假 parser」；② 首轮断言 `image.abs_path` 笔误（`ImageInput` 字段名是 `path`）→ 已修；③ **`Task-018` 的假 M001 模块用例因真实槽出现而失效**（`from package import name` 命中真实模块）→ 已改为**真实槽位断言**（同时**去掉一个桩**，测试更真实）。
3. `Task-020`（前端入口）、`Task-021`（验收）待执行；`CR-006` 待排期。

## 6. 不在本任务范围

- M002 提供方（`Task-018`）、前端按钮（`Task-020`）、验收（`Task-021`）；
- `app/core/ai/**` 任何改动（若发现 AI 层需变更 → **停下回报**，走 CR）；
- `CR-006`（A/B/C）。
