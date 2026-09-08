# API_REGISTRY —— API 登记总表（导航）

> 维护：Project Master / 各模块 Owner Agent。
> 注意：本表只做 **导航与状态登记**；API 的完整定义（请求/响应/错误/契约）以所属模块的 `MODULE_API.md` 为权威源，本表不复制定义（Single Source of Truth，见 `DEVELOPMENT_GUIDE.md`）。
>
> 状态：**V1 启用，M001 Frozen / M002 Frozen 已登记**（2026-09-08）。API-M001-001~012 **Frozen**（修改须走 CR；M001 变更 `CR-001`/`ACR-001`/`CR-002`/`ACR-002` 均 **Approved**，**CHANGE-001 编码/测试/回填完成，待 PM 复核**——冻结面契约描述随变更后实况更新于 `MODULE_API.md`，ACR-001 新增端点已编码、**API ID 待 Project Master 收口分配**）；API-M002-001~006 **Frozen**（契约基线 **v0.3.0**，2026-09-08 用户批准；先采后认重构 + 内容级判定口径；v0.1.0 四接口语义废弃）；M003~M007 在各自契约阶段逐条登记；登记前不得实现无契约接口。

## API 登记表

| API ID | 名称 | Owner 模块 | 版本 | 状态 | 方法/路径(摘要) | 详细定义位置 |
| --- | --- | --- | --- | --- | --- | --- |
| API-M001-001 | 注册家庭账号 | M001 | v0.1 | Frozen | POST `/api/v1/family/register` | `docs/modules/M001/MODULE_API.md` |
| API-M001-002 | 家庭登录 | M001 | v0.1 | Frozen | POST `/api/v1/family/login` | `docs/modules/M001/MODULE_API.md` |
| API-M001-003 | 家庭登出 | M001 | v0.1 | Frozen | POST `/api/v1/family/logout` | `docs/modules/M001/MODULE_API.md` |
| API-M001-004 | 创建学生档案 | M001 | v0.1 | Frozen | POST `/api/v1/students` | `docs/modules/M001/MODULE_API.md` |
| API-M001-005 | 学生档案列表 | M001 | v0.1 | Frozen | GET `/api/v1/students` | `docs/modules/M001/MODULE_API.md` |
| API-M001-006 | 更新学生档案 | M001 | v0.1 | Frozen | PATCH `/api/v1/students/{student_id}` | `docs/modules/M001/MODULE_API.md` |
| API-M001-007 | 创建作业任务 | M001 | v0.1 | Frozen | POST `/api/v1/tasks` | `docs/modules/M001/MODULE_API.md` |
| API-M001-008 | 任务列表 | M001 | v0.1 | Frozen | GET `/api/v1/tasks` | `docs/modules/M001/MODULE_API.md` |
| API-M001-009 | 任务详情 | M001 | v0.1 | Frozen | GET `/api/v1/tasks/{task_id}` | `docs/modules/M001/MODULE_API.md` |
| API-M001-010 | 更新任务 | M001 | v0.1 | Frozen | PATCH `/api/v1/tasks/{task_id}` | `docs/modules/M001/MODULE_API.md` |
| API-M001-011 | 推进任务状态 | M001 | v0.1 | Frozen | POST `/api/v1/tasks/{task_id}/status` | `docs/modules/M001/MODULE_API.md` |
| API-M001-012 | 学校字典列表 | M001 | v0.1 | Frozen | GET `/api/v1/schools` | `docs/modules/M001/MODULE_API.md` |
| API-M002-001 | 创建上传批次 | M002 | v0.3.0 | Frozen | POST `/api/v1/upload-batches` | `docs/modules/M002/MODULE_API.md` |
| API-M002-002 | 上传作业照片 | M002 | v0.3.0 | Frozen | POST `/api/v1/photos` | `docs/modules/M002/MODULE_API.md` |
| API-M002-003 | 照片列表/待处理队列 | M002 | v0.3.0 | Frozen | GET `/api/v1/photos` | `docs/modules/M002/MODULE_API.md` |
| API-M002-004 | 受控取图 | M002 | v0.3.0 | Frozen | GET `/api/v1/photos/{photo_id}/content` | `docs/modules/M002/MODULE_API.md` |
| API-M002-005 | 照片归属操作 | M002 | v0.3.0 | Frozen | POST `/api/v1/photos/{photo_id}/associate` | `docs/modules/M002/MODULE_API.md` |
| API-M002-006 | 撤销/清理照片 | M002 | v0.3.0 | Frozen | DELETE `/api/v1/photos/{photo_id}` | `docs/modules/M002/MODULE_API.md` |

## 规划中的 API 所有权（待契约设计）

| 模块 | 预期对外能力（占位，非契约） |
| --- | --- |
| M001 | 作业任务 CRUD、任务状态推进、任务查询（供采集/匹配/评分） |
| M002 | 已登记 API-M002-001~006（Frozen，v0.3.0；上传批次/照片上传/照片列表/受控取图/归属操作/撤销清理） |
| M003 | 识别提交与结果查询（含置信度、状态） |
| M004 | 匹配执行与结果查询 |
| M005 | 评分执行与结果查询（六维+综合+依据） |
| M006 | 教师评价生成与查询 |
| M007 | 今日报告生成与查询 |
| AI 抽象 | Provider 统一调用契约（Vision/OCR/LLM）、调用记录写入 |

## API ID 规则

- 格式 `API-M001-001`（`API-<ModuleID>-<模块内序号>`），连续编号不重复
- 分配权归属 Project Master（详见 `ID_GOVERNANCE.md`）

## API 状态机

`Draft → Active → Frozen → Deprecated → Removed`

- 进入 `Frozen` 后，修改必须走变更流程（CR），禁止无记录修改其他模块已使用的 API
- Breaking Change 处理：版本化 / 兼容 / 迁移 / 弃用 / 通知消费者（规则见 `DEVELOPMENT_GUIDE.md`）

## API 契约要素（权威模板，属模块 `MODULE_API.md`）

每个 API 至少描述：API ID / Name / Description / Owner Module / Version / Method / Path / Authentication / Authorization / Request / Response / Error / Timeout / Rate Limit / Idempotency / Transaction / Side Effect / Compatibility / Example。
