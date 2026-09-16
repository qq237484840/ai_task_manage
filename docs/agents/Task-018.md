# Task-018 任务书 —— `CR-005` 提供方：M002 受控提供布置单图片（`provide_task_source_image`）

- **Task ID**：Task-018 ｜ **Agent**：`AGENT-M002` ｜ **Module**：M002（作业图片采集与归属）
- **签发**：Project Master，2026-09-16 ｜ **状态**：**已签发（待执行）** ｜ **Kind**：**契约实施（M002 提供方，小）**
- **上游**：`docs/changes/CR-005.md`（**Approved**）→ M002 契约 **v0.4.1 → v0.4.2**（**已修订**：内部服务接口 +1）
- **启动前置（已满足）**：全量 `pytest` 基线 **251 / 0 / 0 / 0**；M002 契约 v0.4.2 已登记；M001 侧槽位由 `Task-019` 并行实现（**本任务不依赖 M001 侧就绪**——注册失败须**不阻断**）。
- **契约影响**：M002 **内部服务接口 +1**（已在本任务前完成契约文本修订）；**对外 HTTP 端点不变**。
- **写区（授权）**：
  1. `backend/app/modules/m002/clients/task_client.py`（**推荐**：与既有 `migrate_photo_links` / `ensure_*_registered` 同文件，保持跨模块回调集中）
  2. `backend/app/main.py`（**仅 1 行**：启动期幂等自愈调用，紧邻既有 `ensure_links_migration_hook_registered()`）
  3. `backend/tests/unit/` 或 `backend/tests/integration/`（**新增**用例文件，如 `test_m002_task_source_image.py`）
  4. `docs/agents/Task-018.md`（§5）
- **禁止改**：`backend/app/modules/m001/**`（`Task-019` 写区）、`backend/app/core/ai/**`、`backend/app/modules/m002/**` **除** `clients/task_client.py`、`frontend/**`、其余 `docs/**`。

## 1. Objective

让 M001 链路 T 能**受控**取得布置单照片字节路径（不越权、不外发路径），从而支持「图片源 → Vision 解析」（`API-M001-022`）。

## 2. 背景（PM 读码确认）

| # | 事实 | 证据 |
| --- | --- | --- |
| 1 | M002 已有受控路径解析 + 读取能力，可复用 | `m002/services/link_service.py:216-222::_abs_path`（`ImageStore(settings.image_root).abs_path(photo.normalized_path)`）、`m002/api/photo_routes.py:86-104`（`ImageStore.read`） |
| 2 | 跨模块回调注册模式已固化（本任务照抄） | `m002/clients/task_client.py:424-460`（`ensure_links_migration_hook_registered` + 导入期 `_register_links_migration_hook()`）、`main.py:66-85`（启动期幂等自愈） |
| 3 | M001 侧槽位由 `Task-019` 提供 | `docs/modules/M001/MODULE_API.md`「内部服务接口」段（`CR-005` 新增条目） |
| 4 | 路径**不得**外发 | `docs/modules/M002/MODULE_API.md` 说明：`PhotoDTO` 含本地路径，**仅限同机进程内消费** |

## 3. 任务要求

### 3.1 实现 provider（**必做**）

在 `m002/clients/task_client.py` 新增（**公开函数**）：

```
@dataclass(frozen=True)
class TaskSourceImage:
    mime: str
    abs_path: str

def provide_task_source_image(family_id: str, photo_id: str) -> TaskSourceImage | None
```

- 语义：按 `family_id` 查照片（**归属校验**：不属于该家庭 / 不存在 → `None`）；解析 `normalized_path` 的绝对路径（复用 `ImageStore(settings.image_root).abs_path(...)`，`get_m002_settings()`）；
- **只读**：不得改动照片状态/DB；**不得**产生 API 响应外发路径；
- 失败（路径解析异常 / 文件缺失）→ `None`（**不抛**，交由 M001 侧降级）。

### 3.2 注册与自愈（**必做**）

- `ensure_task_spec_image_provider_registered() -> bool`：语义与 `ensure_links_migration_hook_registered` **逐字对齐**（已注册 → `True` 短路；注册成功 → `True`；**M001 未就绪 / 注册失败 → `False` + `logger.warning`，不抛、不阻断**）；
- 导入期自动注册一次（照抄 `_register_links_migration_hook()` 模式）；
- `main.py` 启动期**紧邻** `ensure_links_migration_hook_registered()` 处追加 1 行幂等自愈调用。

### 3.3 用例（**必做**）

- 归属校验：跨家庭 `photo_id` → `None`（**不得**取到他人图片）；
- 正常：本家照片 → 返回 `mime` + 存在的 `abs_path`；
- 异常：未知 `photo_id` → `None`；文件缺失 → `None`；
- **注册幂等/自愈**：连续调用恒 `True`；槽位被清空后再次调用可自愈（照抄 `test_ensure_links_migration_hook_registered_idempotent` 的写法，**用后恢复现场**）；
- **M001 未就绪不阻断**：模拟 M001 槽不可用 → 返回 `False` 且不抛（`monkeypatch` 或子进程导入）。
- **禁止**以「Mock 照片/Mock 存储桩」替代真实 `ImageStore` 路径解析（如有桩须 docstring 标注并报备）。

## 4. DoD

- [ ] `provide_task_source_image` 按 §3.1 实现（归属校验 + 只读 + 失败返回 `None`）
- [ ] `ensure_task_spec_image_provider_registered` 按 §3.2 实现（幂等 + 自愈 + 不阻断）
- [ ] 导入期注册 + `main.py` 启动期自愈（**仅 1 行**）
- [ ] §3.3 用例全部新增并通过
- [ ] 全量 `pytest`：**0 failed / 0 errors / 0 skipped**，用例数 **≥ 251**（新增用例应使总数增加）
- [ ] `read_lints` = 0；写区合规（`git status --porcelain` + **mtime 审计**）：`modules/m001/**`、`core/ai/**`、`frontend/**`、`docs/**` **零写入**
- [ ] §5 七段式报告完成
- [ ] **不伪造**：不可得证据须停下回报并标注

## 5. 执行方报告（七段式，执行后填写）

> ① 状态 ｜ ② 改动文件清单 + diff 摘要 ｜ ③ 用例证据原文（归属校验 / 幂等自愈 / 不阻断）｜ ④ 全量回归与用例数 ｜ ⑤ 写区合规自证（双证）｜ ⑥ 契约核对（内部接口签名与 `MODULE_API.md` 逐字对齐）｜ ⑦ 遗留 + 需 PM 裁决项

## 6. 不在本任务范围

- M001 侧槽位/端点/前端（`Task-019` / `Task-020`）；验收（`Task-021`）；
- `CR-006`（A/B/C）任何改动；
- 对外 HTTP 端点变更（本任务纯内部接口）。
