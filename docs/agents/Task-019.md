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
  4. `backend/app/modules/m001/routers/tasks.py`（**新端点**）
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

## 5. 执行方报告（七段式，执行后填写）

> ① 状态 ｜ ② 改动文件清单 + diff 摘要 ｜ ③ 红→绿 / 判别力原文（含防伪造）｜ ④ 全量回归与用例数 ｜ ⑤ 写区双证 ｜ ⑥ 契约逐字核对（`API-M001-022` 与 `MODULE_API.md`）+ 桩报备 ｜ ⑦ 遗留 + 需 PM 裁决项

## 6. 不在本任务范围

- M002 提供方（`Task-018`）、前端按钮（`Task-020`）、验收（`Task-021`）；
- `app/core/ai/**` 任何改动（若发现 AI 层需变更 → **停下回报**，走 CR）；
- `CR-006`（A/B/C）。
