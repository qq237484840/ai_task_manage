# M002 文件级知识（L6）—— 作业图片采集与挂接

- **状态**：**v0.4.0（Frozen，用户批准 2026-09-10）**。代码基线 = v0.3.0（Task-002 完成，pytest 112）。下表 **① 既有实现（实况）** 为当前落盘；**② v0.4.0 待实现/待改造（③ 阶段）** 为按 `CR-003`/`ADR-013` 修订后的目标文件面。**实施 = `Task-008`（已签发，契约已定稿）。**
- **命名**：后端模块 `backend/app/modules/m002/`，测试 `backend/tests/`

## 文档（九件套，`docs/modules/M002/`）

| 文件 | 内容 |
| --- | --- |
| `MODULE.md` | 模块总览（职责/边界/依赖/数据/接口） |
| `MODULE_SUMMARY.md` | 摘要与决策记录（D1~D8、R1~R3、R4~R6、**v0.4.0 修订**） |
| `MODULE_CONTRACT.md` | 黑盒契约 **v0.4.0（草案）**（入口 kind / N:N 挂接 / 门控 / 分析 / 质检 / 归一 / 配置 / 错误 / 签署区） |
| `MODULE_API.md` | REST + 内部服务接口权威源（API-M002-001~006 + **新增 5 端点 ID 待分配**） |
| `MODULE_DATA.md` | 数据字段权威源（`upload_batches`/`photos`/**`photo_subject_links`**/**`completion_analyses`**） |
| `MODULE_DESIGN.md` | 白盒分层与流程（**v0.4.0 目标态**） |
| `MODULE_TEST.md` | 测试计划与验收口径（基线 112 + 新增用例） |
| `MODULE_FILES.md` | 本文件 |
| `MODULE_CHANGELOG.md` | 版本记录（含 Task-005 交付说明） |

## ① 既有实现（实况，v0.3.0 / Task-002）

```
backend/
├─ app/
│   ├─ modules/
│   │   ├─ m001/                     # Stable → 契约 v0.2.0 Frozen（用户批准 2026-09-10；实施 = Task-007）
│   │   └─ m002/                     # 本模块（后端实现完成，v0.3.0）
│   │       ├─ domain/{models,enums,errors}.py
│   │       ├─ repository/{batch_repository,photo_repository}.py
│   │       ├─ services/{quality,normalizer,image_store,upload_service,
│   │       │            association_service,undo_service,photo_query_service,
│   │       │            suggestion_service,dto_builders,locks}.py
│   │       ├─ api/{upload_routes,photo_routes,association_routes,content,__init__}.py
│   │       ├─ clients/task_client.py   # M001 只读桥接
│   │       ├─ schemas.py
│   │       └─ config.py                # M002Settings（AT_M002_*，质检/归一/上限）
│   ├─ shared/                          # AuthContext 双主体（ACR-001）、audit、config、errors
│   └─ main.py                          # 注册 m002 路由
├─ data/images/                         # 本地受控图片目录（随部署备份，git 忽略）
└─ tests/
    ├─ unit/test_m002_image_processing.py   # 质检规则矩阵/归一器/存储 11 例
    ├─ api/test_m002_api.py                 # REST 集成（批次/上传/列表/归属/删除/越权）12 例
    └─ …（M001 既有回归 → 合计 112 passed）
```

## ② v0.4.0 待实现 / 待改造（③ 阶段）

| 文件 | 动作 | 说明 |
| --- | --- | --- |
| `domain/models.py` | **改造** | 加 `upload_batches.kind`、`photos.kind`（+ `subject`/`group_no`/`suggestion_json` 标 Deprecated）；新增 `photo_subject_links`、`completion_analyses` |
| `domain/enums.py` | **改造** | 加 `BatchKind`、`LinkSource(ai\|manual)`、`AnalysisStatus(draft\|confirmed)` |
| `repository/link_repository.py` | **新增** | `photo_subject_links` 读写（N:N，建议/确认/驳回） |
| `repository/analysis_repository.py` | **新增** | `completion_analyses` 读写（草稿/确认/重跑） |
| `services/link_service.py` | **新增** | 挂接建议 / 逐张复核 / 手工挂接 / 首确认触发 `mark_in_progress` |
| `services/gate_service.py` | **新增** | 窗口级门控（待复核 N / satisfied） |
| `services/analysis_service.py` | **新增** | 完成分析生成/确认/重跑（确认经 M001 `commit_conclusion`） |
| `services/association_service.py` | **重构/替换** | 段级归属 → link_service（旧语义作废） |
| `services/upload_service.py` | **改造** | 批次 `kind` 冗余；提交后异步触发挂接建议 |
| `services/suggestion_service.py` | **改造** | 建议写入改为 `photo_subject_links`（`source=ai`）；去 `suggestion_json` |
| `clients/ai_client.py` | **新增** | `app/core/ai/` 调用封装（挂接建议 + 完成分析） |
| `clients/recognition_client.py` | **删除** | ~~M003 建议写接口~~（ADR-014：职责并入；**B7 漂移清理**） |
| `api/link_routes.py` / `gate_routes.py` / `analysis_routes.py` | **新增** | 新增 5 端点路由（`API-M002-007~011`） |
| `api/association_routes.py` | **改造** | `/associate` → `/links`（挂接复核） |
| `api/photo_routes.py` / `schemas.py` | **改造** | `links` 替代 `assignment`/`suggestion`；加门控/分析 DTO |
| `config.py` | **改造** | 加 `batch.kind.enum`、`analysis.gate.enabled`、`association.max_photos_per_subject` |
| `frontend/src/**` | **改造** | 「照片」→「作业」；待复核队列（逐张复核/手工挂接）；门控提示；完成分析确认 |
| `tests/**` | **扩展** | 112 基线 + 门控 / N:N 唯一 / 分析事务 / 消费锁定 / `migrate_links` / AI 降级（见 `MODULE_TEST.md`） |

## 说明

- 质检"模糊"用**浮点 4-邻域拉普拉斯方差**（`quality_blur_probe_side=320` 预览降采样，规避字节裁剪）；"倾斜"为文本行投影启发式（可解释、阈值配置化，非像素级精确）
- 上传经 `locks.py` 键控互斥（family+batch）；并发安全由 `(batch_id, seq_no)` UNIQUE 兜底
- 后端模块清单/Agent 分工登记见 `docs/MODULE_REGISTRY.md`、`docs/AGENT_REGISTRY.md`；API 登记见 `docs/API_REGISTRY.md`
- 本地图片目录不入 git（`.gitignore`），属运行时数据；测试图片均为 test 内合成（PIL）
- 前端 H5 页面随前端协作产出（`frontend/src/views/`，见 `frontend/README.md`）
