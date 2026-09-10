# Task-010 任务书 —— M002 门控链路修复（契约内接口回填 group 上下文 + 真机集成用例）

- **Task ID**：Task-010 ｜ **Agent**：`AGENT-M002` ｜ **Module**：M002（作业图片采集与归属）
- **签发**：Project Master，2026-09-10 ｜ **状态**：**已交付 → PM 复核 APPROVED（2026-09-10）；`BUG-002` → Verified** ｜ **Kind**：**缺陷修复（后端；`BUG-002`）+ 测试补强**
- **启动前置（硬约束）**：M001 契约 **v0.2.0 Frozen（✅ 已实施，Task-007 关闭）** + M002 契约 **v0.4.0 Frozen（✅ 已实施，Task-008 关闭）** + `app/core/ai/`（✅ Task-006 交付）。
- **只读边界（本任务核心约束）**：**`backend/app/modules/m001/**` 与 M001 契约（`docs/modules/M001/**`）一律只读、零改动**。**禁止改前端 `frontend/**`**（`Task-009` 已关闭）。契约 `v0.4.0` Frozen，**本任务不得修改契约文本**（如需契约修订走 CR）。
- **前置依据**：缺陷登记 `docs/changes/BUG-002.md`（权威根因链）、`docs/modules/M001/MODULE_API.md` §内部服务接口（**Frozen 消费面清单**）、`docs/modules/M002/MODULE_API.md`（`API-M002-005/008/009`）、`docs/adr/ADR-013.md`、`docs/changes/CHANGE-003.md` §2.2 B4/B5、`docs/agents/Task-009.md` §7.3 Request-2
- **任务书登记**：`docs/AGENT_REGISTRY.md`（`AGENT-M002` 行）｜ **验收**：本任务 §6 DoD + `BUG-002` §5 验证证据回填
- **为什么必须在 ④ 之前完成**：窗口级门控是「全部复核后才允许分析」的**后端强制点**；缺陷使其仅剩前端禁用提示（可绕过、非安全边界），④ 验收剧本（浏览器级 + 域 B/C）必然触及门控与完成分析。

## 1. Objective（目标）

修复 `BUG-002`：使 M002 的窗口级门控与完成分析前置**按真实归属窗口**正确工作 —— `GET /photo-gates` 按窗口分组返回、`POST /completion-analyses` 门控未满足时**确实**返回 `409 gate_not_satisfied`、`API-M002-005` 响应中的 `gate` 字段正确；并以**真机 M001↔M002 集成用例**守护该链路（消除 `FakeGateway` 桩造成的盲区）。

## 2. 背景：缺陷实证（见 `BUG-002` §2，摘要）

- M002 网关消费了**契约外**接口 `get_group_subject`（M001 契约内部服务接口表未登记），其返回 `TaskGroupSubjectDTO` **不含** `group_key`/`window_type`/`student_id`/`group_id`（这些在 `TaskGroupDTO` 上）；
- `task_client.py:290` `group = getattr(raw, "group", None) or raw` → `_to_subject_ref(raw, raw)` → `group_key=""`；
- `gate_service.list_gates` 按 `ref.group_key` 分桶 → 全部落 `""` 单桶（跨窗口聚合）；`get_gate(<真实 key>)` 过滤 `key != group_key` 恒不匹配 → 兜底 `satisfied=True(total=0)` → `AnalysisService._require_gate` 永不触发。

## 3. Requirements（权威源，只读）

- `docs/changes/BUG-002.md`（根因链 + 修复方向，**权威**）
- `docs/modules/M001/MODULE_API.md` §内部服务接口（**契约内唯一可用消费面**：`list_groups` / `get_group -> TaskGroupDTO`）
- `docs/modules/M002/MODULE_API.md` §API-M002-008 / 009 / 005（门控语义：`satisfied` = 该窗口全部照片挂接已确认；`pending` = 待复核 N）
- 现有实现（只读参考）：`backend/app/modules/m002/clients/task_client.py`、`services/gate_service.py`、`services/analysis_service.py`、`api/link_routes.py`

## 4. Scope（范围）

### 4.1 本任务交付

| # | 交付 | 说明 |
| --- | --- | --- |
| 1 | **默认路径改走契约内接口** | `DefaultM001Gateway` 的 group 上下文获取必须经 **`list_groups(session, family_id)`**（必要条件：按 `group_subject_id` 定位所属 `TaskGroupRef`，回填 `group_key` / `window_type` / `student_id` / `group_id`）；如可经 `get_group` 直取则优先（按 `group_id`）。**契约外接口不得作为唯一来源**。 |
| 2 | **保留并修正 `get_group_subject` 语义** | 若保留作为加速路径：拿到 `TaskGroupSubjectDTO` 后**必须补齐** group 上下文；注释标注「非契约实现细节，仅作加速；缺失/失败回落契约路径」。异常语义保持不变（`LinkTargetMissingError` / `M001UnavailableError` / 越权 → 404 防探测）。 |
| 3 | **门控正确性** | `GET /photo-gates`：多窗口时返回**多条**、各 `group_key` **非空且等于真实窗口 key**、桶内 `total_photos`/`pending_photos` 正确；`GET /photo-gates?group_key=` 命中正确桶；窗口无照片 → `satisfied=true(total=0)`（保持契约语义）。 |
| 4 | **门控前置生效** | `POST /completion-analyses`：该窗口存在未确认挂接照片 → **`409 gate_not_satisfied`（可达，实测）**；全部确认 → 200 生成 draft。`settings.analysis_gate_enabled=false` 时仍跳过（保持现状）。 |
| 5 | **`API-M002-005` 响应 gate 正确** | `LinkReviewOut.gate` 回填真实窗口 key 与计数（不再空串）。 |
| 6 | **真机集成用例（关键）** | **不得使用 `FakeGateway` 桩**：以真实 M001 服务（`TaskQueryService` / `TaskAggregationService`）注入内存 SQLite，覆盖 ≥3 例：① 多窗口分组正确；② 未复核完 → `409 gate_not_satisfied`；③ 全部确认 → 200。可复用 `backend/tests/_m001_helpers.py` / `m002_support.py` 既有夹具。 |
| 7 | **回归** | 全量 `pytest` **不得低于 207**（新增用例后应为 **≥ 210 passed / 0 failed**）；`read_lints` = 0。 |

### 4.2 Allowed-Files（可写）

- `backend/app/modules/m002/clients/task_client.py`（**主改点**）
- `backend/app/modules/m002/services/gate_service.py`（仅当确需；改动须在交付报告中说明理由）
- `backend/tests/**`（仅 M002 相关：新增真机集成用例；可扩展 `m002_support.py`）
- `docs/modules/M002/MODULE_CHANGELOG.md`（**追加**本次修复小节，不改历史行）
- `docs/changes/BUG-002.md`（**仅回填** §5 验证证据与状态）

### 4.3 Forbidden-Files / 边界（越界即返工）

- **`backend/app/modules/m001/**` 一律只读**；**禁止修改 M001 契约文档**（`docs/modules/M001/**`）
- **禁止改契约文本**：`docs/modules/M002/MODULE_API.md` 等 Frozen 契约面（如需 → 提 CR，由 PM 处理）
- **禁止改前端** `frontend/**`（`Task-009` 已关闭；前端 `localGate` 兜底为**展示层**，不得作为「无需修复」理由，也不得删除）
- 禁止改动其他治理文档（AGENT_REGISTRY / API_REGISTRY / DATA_MODEL / CONFIGURATION / CHANGE-003 / ROADMAP / PROJECT_STATUS / CHANGELOG / INDEX / ADR）
- 禁止实现 V2 能力；禁止内容项级判定；禁止自行分配 API / DATA / Task / BUG ID
- **禁止以「放宽门控」或「前端禁用」方式绕过**：修复目标是后端强制可生效

## 5. Dependencies（前置就绪条件）

- **硬前置（✅ 均已满足）**：M001 v0.2.0 / M002 v0.4.0 已实施并 PM 复核 APPROVED；全量 `pytest` 基线 **207 passed**；`main.py` 启动期自愈已接线
- **本地验证**：`backend/.venv`（Python 3.12）；`python -m pytest -q`；AI 可走 Mock（`AT_AI_PROVIDER_MODE=auto`）

## 6. Acceptance Criteria（DoD，`AGENT_GUIDE.md` §6）

- [x] `GET /api/v1/photo-gates` 在某学生 ≥2 个归属窗口时返回 **≥2 条**，各 `group_key` **非空**且与 `task_groups.group_key` 一致（**实测响应体**佐证）—— 用例 ① 断言 `{'2026-09-09','W:2026-09-11'}` + `window_type=day/weekend`
- [x] `GET /api/v1/photo-gates?group_key=<真实 key>` 命中正确桶（计数与实际照片数一致）—— 用例 ① `len==1` 且计数一致
- [x] `POST /api/v1/completion-analyses`：窗口存在未确认挂接照片 → **409 `gate_not_satisfied`（实测可达，附响应体）**；全部确认 → 200 draft —— 用例 ②/③（② message = 「待复核 1 张」，③ 201 draft）
- [x] `POST /api/v1/photos/{id}/links` 响应 `gate.group_key` **非空**、计数正确 —— 用例 ① 断言 `gate` 非 `None` + 真实 key
- [x] 新增**真机 M001↔M002 集成用例 ≥3**（不使用 `FakeGateway` 桩），且**新增用例在修复前会失败**（红→绿佐证，报告中说明）—— 实交 **4 例**，`set_gateway(None)` 走真实网关；红→绿已取证
- [x] 全量 `pytest` = **≥210 passed / 0 failed**（原 207 基线不退化）；`read_lints` = 0 —— **PM 实测 4 passed（专属）+ 全量 exit 0（207 + 4 = 211）**；`read_lints` = 0
- [x] **`backend/app/modules/m001/**` 与契约文档 git diff 为空**；`frontend/**` git diff 为空 —— PM 以 `git diff --name-only -- backend`（同名 15 文件，同 Task-009 开工前）+ **mtime 审计**双重确认（`m001/**` 无 18:02 后写入；`frontend/src/**` 最新写入 17:55 < Task-010 起始 18:02）
- [x] 交付报告含：① 状态；② 改动文件清单；③ 验证命令与原文结论；④ 契约一致性自检（`API-M002-005/008/009`）；⑤ Request 清单；⑥ 遗留风险
- [x] PM 复核 APPROVED（2026-09-10）→ `BUG-002` 置 **Verified** → Task-010 关闭 → ④ 验收可启动

> 注：本任务**不含**浏览器级端到端验收（PM ④ 统一执行）、真实三方密钥联调（Mock 为最低验收线，`ADR-011`）、契约文本修订（`CR-004` 独立流程）。

## 7. 交付与 PM 复核结论（2026-09-10）

### 7.1 PM 独立复验（未采信自述）

| 复验项 | 命令 / 方式 | 结果 |
| --- | --- | --- |
| 新增真机用例 | `python -m pytest tests/integration/test_m002_gate_real_m001.py -q` | **4 passed，exit 0** |
| 全量回归 | `python -m pytest -q` | **exit 0**（基线 207 + 新增 4 = **211**，不退化） |
| 修复正确性（代码审读） | `task_client.py:275-298`：`get_group_subject` 改走 `list_groups` → `_to_group_ref` 回填 `group_key`/`window_type`/`student_id`/`group_id`；契约外 `TaskGroupService.get_group_subject` 消费**已移除** | 与 `BUG-002` §3.2 修复方向一致 |
| M001 零改动 | `git diff --name-only -- backend` + **mtime 审计** | **零改动**（无任何 `m001/**` 文件在 Task-010 期间被写入） |
| 前端零改动 | mtime 审计 | **零改动**（最新写入 17:55，早于 Task-010 起始 18:02；`localGate` 展示层兜底保留未删） |
| 契约文本零改动 | 交付清单不含 `MODULE_API.md`；`MODULE_CHANGELOG.md` 仅追加 | 合规（Frozen 保持） |
| 临时取证残留 | 检索 `backend/**` 的 `TEMP-` / `CAP_` | **0 命中** |
| 用例真实性与守护性 | 审读测试文件（`set_gateway(None)` → 真实 `DefaultM001Gateway`，经 `POST /tasks` + `ensure_group` 造真实聚合层，无桩） | 符合 §4.1-6；断言直指 BUG-002 三条症状（`group_key` 非空且等于真实 key / 409 可达 / `M002-005` 的 `gate` 非空） |
| `read_lints`（改动文件） | 工具检查 | **0** |

**结论：APPROVED**（`BUG-002` → **Verified**；Task-010 关闭；`CHANGE-003` ③ 后端修复项关闭 → **④ 验收解除前置阻塞**）。

### 7.2 执行方两条「决策说明」的 PM 裁决（均予认可）

1. **不保留 `get_group_subject` 作为加速路径**：**认可**。`TaskGroupSubjectDTO` 物理上不含 `group_id`/`group_key`，M002 侧只有 `group_subject_id`、**无从补齐** group 上下文 → 按 `BUG-002` §3.2「不能补齐即不得作为定位来源」处理。若后续 M001 将该接口登记进契约并补齐 group 字段，可恢复「加速 + 回落」，**须走 CR**。
2. **不适用 `get_group` 直取**：**认可**。M002 侧无 `group_id`，无法直取，统一经 `list_groups` 定位；与 §4.1-1「能经 `get_group` 直取则优先」不冲突（前提条件不成立）。

### 7.3 复核产生的后续治理动作（PM）

- **`TD-001`**：`get_group_subject` 由直取退化为「按 family 全量 `list_groups` 扫描」，展示链路（`photo_query_service` / `link_routes` / `association_routes` / `analysis_routes`）存在 N+1 放大；`gate_service` 已有 `ref_cache` 去重，**V1 规模可接受**；规模化前建议一次性建映射批量解析。
- **`TD-002`**：契约内 `TaskGroupDTO` 未暴露 `window_task_id`/`task_status` → `API-M002-005` 响应 `task_id` 恒 `null`、M001 窗口任务 `mark_in_progress` 不触发；属契约既定语义缺口，不阻断 ④，择机走 CR。
- **`CR-004`**（`API-M002-007` 响应体）在本次复核时为 **Proposed**，与本次修复无耦合 —— **后续：已由用户批准 → `Applied`（2026-09-10，M002 契约 v0.4.0 → v0.4.1），见 `docs/changes/CR-004.md` §落地记录与 `CHANGELOG.md` v0.20.0**。

### 7.4 交付物

`backend/app/modules/m002/clients/task_client.py`（1 改）、`backend/tests/integration/test_m002_gate_real_m001.py`（**新增**，4 例）、`docs/changes/BUG-002.md`（§5 证据回填）、`docs/modules/M002/MODULE_CHANGELOG.md`（追加 Task-010 条目）。
