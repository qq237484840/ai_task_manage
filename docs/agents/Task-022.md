# Task-022 任务书 —— `CR-006` 子项 A：`photos` 窗口归属冗余（`TD-005` 根治）

- **Task ID**：Task-022 ｜ **Agent**：`AGENT-M002` ｜ **Module**：M002 ｜ **Kind**：**实施（中）**
- **签发**：Project Master，2026-09-16 ｜ **状态**：**已签发（待执行）**
- **上游**：`CR-006`（**Approved**，用户批准 2026-09-16，A/B/C 全批）｜**子项 A 契约修订已完成**（M002 **v0.4.2 → v0.4.3**）｜`CR-005` 已 `Applied`（串行约束解除）
- **关联**：`TD-005`（未挂接照片无窗口归属）、`REQ-011`（R1 口径可升级为**本任务窗口**）
- **契约影响**：**无**（契约已于本次 PM 修订完成；实施方**只按契约码**）

## 1. Objective

让**每一张上传的作业照片**在上传时即具备**窗口归属**（`belong_date` / `group_key` 冗余），从而支持「按窗口过滤/统计/展示」—— 终结 `TD-005`：「`unassigned`/`suggested` 照片在数据上不属于任何窗口」。

## 2. 背景（PM 已读码核验，实施方不必重复探索）

| 事实 | 位置 |
| --- | --- |
| `photos.task_id` **仅在「首条挂接确认」时写入** → `unassigned`/`suggested` 照片**无归属** | `m002/repository/photo_repository.py:150-155`（`set_window_task`） |
| **归属规则的唯一知识源 = M001**，且契约**已有** `TaskQueryService.resolve_window(ts) -> WindowInfo`（消费者已列 M002；「纯计算，不锁配置」） | `docs/modules/M001/MODULE_API.md` 内部服务接口表；`m001/services/window_resolver.py:76-105`（`WindowInfo = {belong_date, week_index, window_type, group_key}`） |
| M002 侧**尚无** `resolve_window` wrapper | `m002/clients/task_client.py`（`grep resolve_window` = 0 命中） |
| 上传写库点 | `m002/services/upload_service.py:176`（`PhotoRepository.create`）；`PhotoRepository.create` 签名 `:21-40` |
| 查询面 | `PhotoRepository.list_photos` `:88-130` |
| 建表 | `app/main.py:38` `Base.metadata.create_all`（**不为既有表加列** → 见 §3.5 迁移） |

## 3. 任务要求

### 3.1 数据层（`domain/models.py` + `repository/photo_repository.py`）

1. `Photo` 新增 **2 列**（均可空）：`belong_date: str | None`、`group_key: str | None`；表级索引新增 `(family_id, belong_date)`、`(family_id, group_key)`（**逐字对齐** `MODULE_DATA.md` v0.4.3）。
2. `PhotoRepository.create(...)` 新增 2 个**关键字参数**（`belong_date: str | None = None`、`group_key: str | None = None`）并落行。
3. `PhotoRepository.list_photos(...)` 新增 2 个**可选**过滤参数（`belong_date` / `group_key`，缺省 **不过滤** → 向后兼容）。
4. `set_window_task` **语义不变**（`task_id` 仍只在首条确认时写）—— **不得**借本次改动回填 `task_id`。

### 3.2 归属解析（`clients/task_client.py`）

5. 新增 `TaskClient.resolve_window(ts: datetime) -> WindowInfoRef | None`（薄 wrapper，经 **M001 契约内接口**）：
   - 归一为 M002 侧可用的轻量结构（至少含 `belong_date` / `group_key`）；
   - **M001 未就绪（ImportError）/ 调用异常 → 返回 `None` 并记 `warning`，不抛**（与 `ensure_links_migration_hook_registered` 的容错风格一致）；
   - **禁止**在 M002 内复制 4 点日界 / 周末合并 / 学期周等归属规则（**单一知识源**；违反即打回）。

### 3.3 上传链路（`services/upload_service.py`）

6. `upload()` 在 `PhotoRepository.create` **之前**解析归属（**同一事务**内，一次纯计算，无额外 IO）：成功 → 落 `belong_date`/`group_key`；`None`/异常 → **置 `NULL`**、记 `warning`，**上传必须成功**（`201`，**不得**因归属解析失败而 422/500）。
7. 上传**不触发配置锁定**（`resolve_window` 为纯计算；**不得**调用 `ensure_group`/写聚合）。

### 3.4 响应（`schemas.py` + API 层）

8. `API-M002-002` 响应体新增 `belong_date` / `group_key`（**可选**，缺省 `null`）；`API-M002-003` 列表项同样补 2 字段 —— 逐字对齐 `MODULE_API.md` v0.4.3；**不得**改动其它既有字段与错误语义。

### 3.5 迁移（**必须**在交付说明中给出可复现命令）

9. 生产/演示库：`backend/data/*.db` 已 gitignore → 采用**重建库 + 重新种子**（`main.py` 的 `create_all` 不会为既有表加列；**禁止**在生产代码里写 ALTER/自动迁移逻辑）。
10. 测试库：由 conftest fixture 新建 → 天然含新列（**无需**额外处理）。

### 3.6 用例（**必须**含真机证据）

11. **单元/集成（真机）**：新增 `backend/tests/integration/test_photos_window_belong.py`：
    - ① 真实 M001 `resolve_window` 生效：上传照片 → `belong_date` **等于**当日冻结窗口的归属日、`group_key` 正确（**并覆盖至少 1 例「周末合并」**：`group_key` = `W:<周五>`）；
    - ② **过滤**：`GET /photos?belong_date=`（与 `group_key=`）只返回命中照片，且**缺省参数时结果与改动前一致**（向后兼容哨兵）；
    - ③ **不阻断**：注入 M001 不可用（provider/网关替身或 monkeypatch，**须 docstring 标注**）→ 上传仍 `201`、两列为 `NULL`、列表缺省查询正常；
    - ④ **单一知识源**：断言 M002 生产代码**不含**归属规则的本地实现（例如断言 `m002` 包内无 `day_cutoff`/`weekend` 相关自算逻辑 —— 用可复现的静态断言，PM 复核按此检查）。
12. 既有用例**不得删除、不得放宽**；`backend/tests/unit/test_m002_task_source_image.py` / `tests/api/test_task_reparse_api.py` 等 **零回归**。

### 3.7 禁改区

- `backend/app/modules/m001/**`（**M001 零改动** —— `resolve_window` 为既有契约接口）
- `backend/app/core/ai/**`、`frontend/**`、`docs/**`（含 `MODULE_*.md`、`CR-006.md`、`PROJECT_STATUS.md`）
- **不得**修改契约文本；发现契约缺口 → **停手回报 PM**，不得自行扩权

## 4. DoD

- [ ] §3.1~§3.4 全部落地，且与 `MODULE_API.md` / `MODULE_DATA.md` v0.4.3 **逐字一致**
- [ ] §3.11 四类用例齐备（**含周末合并 + 不阻断 + 向后兼容哨兵**）
- [ ] 全量回归 `pytest`：**0 failed / 0 errors / 0 skipped**，**用例数 ≥ 267 + 新增**
- [ ] **红→绿判别力**：至少 1 条（例如临时移除上传时的归属解析 → 过滤用例立败）
- [ ] 写区双证（`git status --porcelain` + mtime）；`read_lints` = 0
- [ ] §5 报告含**迁移可复现命令**与**分域证据**

## 5. 执行方报告（七段式）

> **执行者说明**：本任务由 **PM 代执行**（本机 IDE 无具备写权限的执行 subagent）→ 不构成独立第三方复核，限制如实标注。

### ① 状态

**完成**。`photos` 新增窗口归属冗余列 `belong_date` / `group_key`（**上传时**经 M001 契约内 `resolve_window` 解析）+ 索引；`API-M002-002` 响应与 `API-M002-003` 过滤参数按 v0.4.3 落地；新增用例 **6 例**全绿；**红→绿**判别力成立；全量回归 **273 / 0 / 0 / 0**；**库重建迁移已执行并真机验证**。

### ② 改动文件清单 + diff 摘要

| 文件 | 性质 | 改动摘要 |
| --- | --- | --- |
| `m002/domain/models.py` | 改 | `Photo` +2 列（`belong_date` `String(10)` / `group_key` `String(32)`，均可空）+2 索引（`ix_photos_family_belong_date` / `ix_photos_family_group_key`）；注释写明「`task_id` 仅首条确认时写 = TD-005 成因；本两列上传即落；**派生冗余**」 |
| `m002/repository/photo_repository.py` | 改 | `create(...)` +2 关键字参数并落行；`list_photos(...)` +2 可选过滤条件（**缺省不过滤**） |
| `m002/clients/task_client.py` | 改 | 新增 `WindowInfoRef`（M002 侧消费视图）+ 协议 `resolve_window` + `DefaultM001Gateway.resolve_window`（**按契约直调** `TaskQueryService.resolve_window`，含存在性探针）+ `TaskClient.resolve_window`（**容错**：异常 → `None` + warning，**不抛**） |
| `m002/services/upload_service.py` | 改 | 阶段二开头解析归属（`TaskClient.resolve_window(datetime.now(UTC))`）+ `PhotoRepository.create` 传入两列；**解析失败 → `None`，上传仍 `201`** |
| `m002/schemas.py` | 改 | `PhotoDTO` / `UploadPhotoOut` 各 +2 **可选**字段 |
| `m002/services/dto_builders.py` | 改 | `build_photo_dto` / `build_upload_out` 各 +2 字段 |
| `m002/services/photo_query_service.py` | 改 | `list_photos` +2 参数并透传 |
| `m002/api/photo_routes.py` | 改 | `GET /photos` +2 Query（`belong_date` / `group_key`，含 description）并透传 |
| `tests/integration/test_photos_window_belong.py` | **新增**（6 例） | ①上传即落归属（**真实 M001 引擎**，参数化 周三/周五/周日 → 覆盖**周末合并** + 数据面实读 + `task_id is None`）；②过滤 + **向后兼容哨兵**；③M001 不可用**不阻断**（替身，已标注）；④**单一知识源**静态断言 |

**关键约束落实（PM 自查）**：**M002 未复制任何归属规则**（静态断言用例 ④ 通过）；`set_window_task` **未改**（`task_id` 语义不变，用例 ① 断言 `task_id is None`）。

### ③ 红→绿 / 判别力证据原文

**红**（临时把上传时的 `window = TaskClient.resolve_window(...)` 改为 `window = None`，等价修复前行为）：

```
FAILED tests/integration/test_photos_window_belong.py::test_upload_persists_window_belong_from_m001_engine[frozen0-2026-09-16-2026-09-16]
FAILED tests/integration/test_photos_window_belong.py::test_upload_persists_window_belong_from_m001_engine[frozen1-2026-09-18-W:2026-09-18]
FAILED tests/integration/test_photos_window_belong.py::test_upload_persists_window_belong_from_m001_engine[frozen2-2026-09-20-W:2026-09-18]
FAILED tests/integration/test_photos_window_belong.py::test_list_photos_filters_by_belong_date_and_group_key
tests/integration/test_photos_window_belong.py:130: AssertionError: assert [] == ['accaa96c-41...1bb6bf255e16']
RED_EXIT=1
```

→ **过滤返回空 = 归属未落库**（正是本任务要修的行为）；「不阻断」「单一知识源」2 例仍 PASS ⇒ 判别点独立。

**绿**（还原）：新增用例 **6 passed** → 全量 `GREEN_EXIT=0`。

### ④ 全量回归原文

```
$ pytest --no-header -q --tb=short --junitxml=../.pm_t022.xml
........................................................................ [ 26%]
......................................X..X.............................. [ 52%]
........................................................................ [ 79%]
.........................................................                [100%]
tests=273 failures=0 errors=0 skipped=0
GREEN_EXIT=0
```

`X..X` = 既有 `BUG-003` / `BUG-004` 双哨兵自然 **XPASS**（未删除、未放宽）。

### ⑤ 写区合规自证（双证）

- **`git status --porcelain`**：`M` 8 个 M002 生产文件（均在任务书写区内）+ `?? tests/integration/test_photos_window_belong.py`（新增）；**未出现** `m001/**`、`core/ai/**`、`frontend/**`、`docs/**` 条目（红取证期间的 `upload_service.py` 临时改动**已还原**）。
- **mtime**：`m001/**`、`core/ai/**`、`m002` 写区外文件（如 `link_service.py`、`gate_service.py`）均**早于**本次写区起点。
- `read_lints` = 0。

### ⑥ 契约一致性核对（`MODULE_API` / `MODULE_DATA` v0.4.3 逐条）

| 契约条目 | 实现 | 结论 |
| --- | --- | --- |
| `photos` +`belong_date`/`group_key`（可空）+ 索引 `(family_id, belong_date)`/`(family_id, group_key)` | `models.py` 列 + `__table_args__` 两索引 | ✔ 一致（真机 `PRAGMA` 佐证，见 ⑦） |
| 上传时经 M001 `resolve_window` 解析；失败 → `NULL` 不阻断；**M002 禁自算** | `upload_service.upload` + `TaskClient.resolve_window`（容错）；静态断言用例 ④ | ✔ 一致 |
| `API-M002-002` 响应 +2 **可选**字段 | `UploadPhotoOut` + `build_upload_out` | ✔ 一致 |
| `API-M002-003` +2 **可选**过滤参数（缺省不过滤） | `photo_routes` Query + `PhotoQueryService` + `PhotoRepository` | ✔ 一致（向后兼容哨兵用例） |
| `PhotoDTO` +2 字段 | `PhotoDTO` + `build_photo_dto` | ✔ 一致 |
| 派生冗余：写入点唯一 = 上传；不随挂接/改归属日回填 | 仅 `PhotoRepository.create` 写两列；`set_window_task` 未改 | ✔ 一致 |

### ⑦ 遗留 + 需 PM 裁决项（含**迁移执行结果**）

1. **迁移已执行（用户批准「重建可以」）**：`start_server.ps1 -Stop` → `start_server.ps1 -Seed`（**官方重建入口**：`.e2e/seed.py` 重建 `acceptance.db` + 重新种子）→ `Seed OK.` + `Health OK`。
   **真机复核原文**：
   ```
   [① 迁移] photos 含 belong_date=True group_key=True
            索引 = [..., 'ix_photos_family_belong_date', 'ix_photos_family_group_key']
   [② 上传] status=201 belong_date=2026-09-16 group_key=2026-09-16
   [③ 库内实读] belong_date=2026-09-16 group_key=2026-09-16 task_id=None
   [④ 过滤] 命中日=1 未命中日=0 缺省=1（缺省应≥1 = 向后兼容）
   ```
   → 生产/演示库与契约一致；`task_id` 仍为 `None`（既有语义不变）。
2. **新登记 `BUG-008`（中，`Confirmed`）** —— 迁移期间读日志发现：**DATA-009 在 SQLite 锁竞争下静默丢失**
   （真实 AI 调用 `HTTP 200`，但 `record_call` 遇 `database is locked` → 仅 warning + 丢弃，**主链路不受影响**）。
   根因 `core/ai/records.py:100-104`（容错正确但**无重试/无计数/无补偿**）。**本次只登记不修**（写区外），
   详见 `docs/changes/BUG-008.md`；**建议与 `CR-006` 子项 B 同批评估**。
3. 子项 A **未含前端消费**（`REQ-011` R1 口径升级为「本任务窗口」需另立前端任务）；子项 B / C 待排期。
4. 时刻控制方式（冻结 `upload_service` 模块内 `datetime`）为**测试专用**；生产代码未引入时钟注入点（若后续要求可测试性更强的时钟抽象，另立技术债）。

## 6. 不在本任务范围

- 契约修订（PM 已完成）；`REQ-011` 前端口径升级（子项 A 落地后另立任务）；`CR-006` 子项 B / C；`TD-006`。
