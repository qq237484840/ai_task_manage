# M002 模块文件规划 —— 作业图片采集与归属

- **状态**：实现中（契约 **v0.3.0 Frozen**，2026-09-08）｜ 本文件由 Task-002 按设计实现更新并回填
- **命名**：后端模块 `backend/app/modules/m002/`，测试 `backend/tests/`（M001 先例）

## 文档（九件套，docs/modules/M002/）

| 文件 | 内容 |
| --- | --- |
| `MODULE.md` | 模块总览（职责/边界/依赖/数据/接口） |
| `MODULE_SUMMARY.md` | 摘要与决策记录（D1~D8、R1~R3、R4~R6/v0.3.0） |
| `MODULE_CONTRACT.md` | 黑盒契约 v0.3.0（状态机/质检/归一/配置/错误/签署区） |
| `MODULE_API.md` | REST + 内部服务接口权威源（API-M002-001~006） |
| `MODULE_DATA.md` | 数据字段权威源（upload_batches / photos） |
| `MODULE_DESIGN.md` | 白盒分层与流程（Task-002 回填细节） |
| `MODULE_TEST.md` | 测试计划与验收口径 |
| `MODULE_FILES.md` | 本文件 |
| `MODULE_CHANGELOG.md` | 版本记录 |

## 代码规划（Task-002 产出，路径示意）

```
backend/
├─ app/
│   ├─ modules/
│   │   ├─ m001/                     # Stable（Frozen v0.1.1 + CR-001/CR-002/ACR-001/ACR-002 Approved 待执行）
│   │   └─ m002/                     # 本模块
│   │       ├─ domain/{models,enums,errors}.py
│   │       ├─ repository/{batch_repository,photo_repository}.py
│   │       ├─ services/{quality,normalizer,image_store,upload_service,
│   │       │            association_service,undo_service,photo_query_service}.py
│   │       ├─ api/{upload_routes,photo_routes,association_routes,schemas}.py
│   │       ├─ clients/{task_client,recognition_client}.py
│   │       └─ config.py
│   ├─ shared/                       # AuthContext 两级主体（ACR-001）、audit、config、errors
│   └─ main.py                       # 注册 m002 路由
├─ data/images/                      # 本地受控图片目录（image_store.root，随部署备份）
└─ tests/
    ├─ m001/…                        # 既有 54 测试（回归）
    └─ m002/
        ├─ test_quality_rules.py
        ├─ test_normalize.py
        ├─ test_upload_batch.py
        ├─ test_association_state_machine.py
        ├─ test_mark_in_progress_once.py
        ├─ test_limits.py
        ├─ test_undo_and_consumed.py
        └─ test_authorization_matrix.py
```

## 说明

- 后端模块清单/Agent 分工登记见 `docs/MODULE_REGISTRY.md`、`docs/AGENT_REGISTRY.md`；API 登记见 `docs/API_REGISTRY.md`
- 本地图片目录不入 git（`.gitignore`），属运行时数据；示例/夹具图放 `backend/tests/fixtures/` 或 test 内合成
- 前端 H5 入口与上传/兜底页面随 Task-002/前端协作产出（`frontend/` 仅占位，见仓库 README）
