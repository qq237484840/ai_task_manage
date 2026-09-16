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

> ① 状态 ｜ ② 改动文件清单 + diff 摘要 ｜ ③ 红→绿 / 判别力证据原文 ｜ ④ 全量回归原文 ｜ ⑤ 写区合规自证（双证）｜ ⑥ 契约一致性核对（`MODULE_API`/`MODULE_DATA` v0.4.3 逐条比对）｜ ⑦ 遗留 + 需 PM 裁决项（含迁移执行结果）

## 6. 不在本任务范围

- 契约修订（PM 已完成）；`REQ-011` 前端口径升级（子项 A 落地后另立任务）；`CR-006` 子项 B / C；`TD-006`。
