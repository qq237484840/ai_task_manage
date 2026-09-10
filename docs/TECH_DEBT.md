# TECH_DEBT —— 技术债务登记

> 维护：Project Master。技术债（已知取舍 / 待优化项 / 契约缺口）在此登记：**不阻断当前阶段**，但须在规模化或对应契约修订时处理。
> ID 规则：`TD-nnn`，仅 Project Master 分配（`docs/ID_GOVERNANCE.md`）。

更新日期：2026-09-10

## TD-001 —— `get_group_subject` 由直取退化为「按 family 全量扫描」（N+1 放大）

| 项 | 内容 |
| --- | --- |
| 来源 | `BUG-002` 修复（`Task-010`，2026-09-10） |
| 位置 | `backend/app/modules/m002/clients/task_client.py::DefaultM001Gateway.get_group_subject` |
| 现状 | 修复后经**契约内** `list_groups(session, family_id)` 全量扫描 `TaskGroupDTO.subjects` 定位（M002 侧无 `group_id`，无法经 `get_group` 直取）。调用方：`gate_service`（**已有 `ref_cache` 去重**）、`link_service`、`photo_query_service`、`api/link_routes`、`api/association_routes`、`api/analysis_routes` |
| 影响 | 展示/复核链路按 `group_subject_id` 逐条解析 → 同一请求内可能重复全量扫描（N+1）。**V1 单家庭规模（窗口/学科数量小）实测可接受**，不阻断 ④ 验收 |
| 触发条件 | 家庭内窗口 / 学科数量显著增长，或照片列表页数据量上升时 |
| 建议方案 | ① **推荐**：在请求作用域内一次性 `list_groups` 建 `group_subject_id → GroupSubjectRef` 映射，供所有解析点复用（只改 M002 侧）；② 或由 M001 将 `get_group_subject` 登记进契约并补齐 group 上下文，恢复「加速 + 失败回落」（**须走 CR**） |
| 责任 / 时机 | `AGENT-M002`；④ 验收通过后按需排期 |

## TD-002 —— 契约未暴露 `window_task_id` / `task_status`（窗口任务 `mark_in_progress` 不触发）

| 项 | 内容 |
| --- | --- |
| 来源 | `BUG-002` 修复复核中发现（`Task-010` 执行方遗留风险 2，PM 采纳，2026-09-10） |
| 位置 | M001 契约 `MODULE_API.md` 内部服务接口表（`list_groups` / `get_group` 返回的 `TaskGroupDTO` 未含 `window_task_id` / `task_status`）；M002 `clients/task_client.py::_to_group_ref` |
| 现状 | `GroupSubjectRef.window_task_id` 恒 `None` → `API-M002-005` 响应 `task_id: null`；M001 窗口任务 `mark_in_progress` 不被触发（`link_service.py` 中 `if not ref.window_task_id: continue`） |
| 影响 | 窗口级任务状态不随作业上传推进（链路 T 状态可见性缺失）；**不影响**门控 / 完成分析 / ④ 验收剧本 7 条 |
| 触发条件 | 需与 M001 联动窗口任务状态，或 ④ 验收提出状态可见性要求时 |
| 建议方案 | 走 CR 由 M001 在 `TaskGroupDTO` 暴露 `window_task_id` / `task_status`（Frozen 契约修订）；M002 侧 `_to_group_ref` 已预留读取，无需改动 |
| 责任 / 时机 | Project Master（CR）+ `AGENT-M001`/`AGENT-M002`；V1 后置 |

## TD-003 —— M002 网关以 `except TypeError` 容忍 M001 内部服务签名漂移（签名兼容垫片）

> **状态：已关闭（Closed，`Task-014` 清理，2026-09-10）**。处置见本节末「处置结果」。

| 项 | 内容 |
| --- | --- |
| 来源 | `Task-012` PM 复核中读码发现（2026-09-10） |
| 位置 | `backend/app/modules/m002/clients/task_client.py:213-216`（`list_groups`：先按 `student_id=`/`group_key=` 调用，`except TypeError` 再退回 `method(session, family_id, student_id)`；同文件 `get_group` 等亦有同类 getattr/兜底风格） |
| 现状 | M001 `TaskGroupService.list_groups` 契约 **v0.2.0 Frozen**，签名稳定 → 该回落分支实际为**死代码**；其存在使「契约签名漂移」被**静默掩盖**（消费面不报错、直接走窄参路径，结果集可能被悄悄放大/缩小） |
| 影响 | 不阻断功能（M001 侧签名未漂移）；但**违反 `BUG-004` 教训**（禁止以 `try/except TypeError` 兼容旧签名）—— 同一缺陷类型换模块复现，且 `BUG-002` 的 `FakeGateway` 教训亦指向「契约外兼容垫片掩盖真机缺口」 |
| 触发条件 | M001 内部服务接口变更 / 契约修订，或 M002 侧再次出现「结果与预期不符但无异常」类问题 |
| 建议方案 | 删除 `except TypeError` 回落分支，改为**按冻结契约直调**（位置/关键字与 `MODULE_API.md` 内部服务接口表逐字对齐）；如需兼容多版本，须走 CR 显式登记而非静默容错。附带：`getattr(service, ...)` + 自定义异常的探测式写法宜收敛 |
| 责任 / 时机 | `AGENT-M002`；**并入 `Task-014`（同主题：去替身/去垫片）** 或后续触碰该文件时清理，须附真机集成用例（`tests/integration/test_m002_gate_real_m001.py` 已覆盖 `list_groups` 通路） |

**处置结果（`Task-014` / `AGENT-M002`，PM 复核认可，2026-09-10）**：

- `list_groups` 的 `try/except TypeError` 回落分支**已删除**，改为按 `M001 v0.2.0 Frozen` 契约直调 `method(session, family_id, student_id=..., group_key=...)`（`clients/task_client.py`）。
- 死代码证明：真机门控集成 10 例 + 边界 2 例 + 剧本 4/5 + 上层用例**全部直调该路径通过**（0 触发）→ 回落分支从不生效。PM 独立全量回归 **237 tests / 0 failed**。
- **PM 裁决（关于同文件 `getattr(..., None) + raise M001UnavailableError` 探针）：不立项 `TD-004`** —— 该模式为**存在性探针**（缺方法 → 大声失败），与 `except TypeError` **签名兼容垫片**（存在但签名不符 → 静默改写调用）**语义不同**，不构成「掩盖契约缺口」风险（PM 铁律 ⑥ 针对的是后者）。故 Keep as-is，不清理、不立台账。
