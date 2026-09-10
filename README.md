# AI.TaskManage —— 中小学生 AI 作业与学习成长综合评定系统

> 采用 **文档驱动 + 多 Agent 协作** 的软件工程治理模式：人负责决策，Project Master 负责治理，模块 Agent 负责实现，Contract 负责协作，Documentation 负责记忆，Registry 负责导航，Tests 负责验证，Git 负责版本。
> 当前阶段 / 模块进度 / 待决事项见 `docs/PROJECT_STATUS.md`、`docs/MODULE_REGISTRY.md`；本地启动方式见下方「快速开始」。

## V1 核心闭环

```text
创建作业任务 → 上传作业照片 → AI 识别 → 任务匹配 → 质量评价 → AI 教师评价 → 今日综合报告
```

## 文档入口

| 目的 | 位置 |
| --- | --- |
| 知识地图（一切从这里开始） | `docs/INDEX.md` |
| 项目全貌（L0） | `docs/PROJECT.md` |
| 需求登记（REQ-001~008） | `docs/REQUIREMENTS.md` |
| 模块登记（M001~M007） | `docs/MODULE_REGISTRY.md` |
| 当前状态与待决决策 | `docs/PROJECT_STATUS.md` |
| 架构（L1） | `docs/ARCHITECTURE.md` |
| 数据模型（L5） | `docs/DATA_MODEL.md` |
| Agent 分工与权限 | `docs/AGENT_REGISTRY.md`、`docs/AGENT_GUIDE.md` |
| 开发流程与变更治理 | `docs/DEVELOPMENT_GUIDE.md` |
| 风险登记 | `docs/RISK_REGISTER.md` |

## 快速开始（本地启动）

技术形态：FastAPI + SQLite 单体（`backend/`）+ Vue3 + Vite + TS + Vant4（`frontend/`）。部署为单进程形态：后端托管 `frontend/dist`，`GET /` 直出 H5（ADR-012）；开发期则前后端分离运行。以下命令均在本仓库根目录执行，Windows PowerShell 写法已给出，Linux/macOS 同理（venv 激活路径改为 `source .venv/bin/activate`）。

### 1. 首次环境准备

后端（Python 3.12+，建议虚拟环境）：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # 激活后 pip 装依赖
pip install -r requirements.txt
cd ..
```

前端（Node ≥ 20，实测 22.22.2；依赖锁文件已入库）：

```powershell
cd frontend
npm install
cd ..
```

### 2. 开发模式（前后端分离）

两个终端分别启动：

```powershell
# 终端 A：后端 API（http://127.0.0.1:8000，接口文档 /docs）
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
# 终端 B：前端 Vite（http://localhost:5173，/api 代理到 8000，需后端已启动）
cd frontend
npm run dev
```

> 后端首次启动自动建 SQLite（`backend/data/app.db`）并幂等 seed 学校字典，无需手工建库/迁移。配置项以 `AT_` 前缀环境变量或 `backend/.env` 覆盖（默认值见 `backend/app/core/config.py`；M002 图片存储为 `backend/data/images/`，运行时数据不入库）。

### 3. 演示 / 生产单进程形态

先构建前端，再只启动后端即可同进程提供完整站点：

```powershell
cd frontend
npm run build                                  # vue-tsc 类型检查 + 产物 → frontend/dist
cd ..\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> 静态目录默认 `frontend/dist`，可用 `AT_FRONTEND_DIR` 覆盖；目录不存在时后端仅提供 API。

### 4. 校验与测试

```powershell
# 后端全量测试（backend/ 下，pytest.ini 已配 pythonpath/testpaths）
cd backend
.\.venv\Scripts\python.exe -m pytest

# 前端类型检查 / 构建校验
cd frontend
npm run typecheck
npm run build
```

| 用途 | 地址 / 命令 | 说明 |
| --- | --- | --- |
| 前端开发页 | `http://localhost:5173` | Vite dev，代理 `/api` → `127.0.0.1:8000` |
| 后端 API / 文档 | `http://127.0.0.1:8000/api/v1/...`、`/docs` | FastAPI |
| 单进程站点 | `http://127.0.0.1:8000/` | 后端托管 `frontend/dist` |

前端工程细节（目录/脚本/契约约束）见 [`frontend/README.md`](frontend/README.md)。

## 治理原则（摘要）

架构、模块、接口、数据、方法等知识一律进入 `docs/` 分层文档维护，本 README 仅作入口，不承载业务知识，避免知识重复。V1 范围控制与 AI 评价原则见 ADR-002/003。

## 治理模板包（复用资产）

本仓库同时维护 **可复用治理模板** `ai-governance-template/`：由本仓库 `docs/` 体系通用化而来，新项目可直接铺装（复制 `docs/` + 按 `INSTALL.md` 替换占位符）。模板是复用资产，不参与本项目知识分层，勿混入业务内容。
