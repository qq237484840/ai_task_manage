# Task-003 任务书 —— 前端技术栈切换（Vue3 + Vite + TypeScript + Vant 4 工程化，承载 M001 页面迁移与托管切换）

- **Task ID**：Task-003 ｜ **Agent**：AGENT-M001 ｜ **Kind**：跨模块前端基建（CHANGE-002，M001 前端迁移）
- **签发**：Project Master，2026-09-08 ｜ **状态**：**Active（已签发，待执行）**
- **前置**：**ADR-012 Accepted**（2026-09-08 用户 Q1~Q3 决策）；本机 **Node ≥20** 已由 PM 预装（npm 联网可用）；M001 契约 **v0.1.2 Stable**（前端为表现层，REST 契约唯一事实源，本次零契约变更）
- **任务书登记**：`docs/AGENT_REGISTRY.md`（AGENT-M001 行）｜ **验收**：本任务书 §6 DoD（PM 复核 APPROVED）

## 1. Objective（目标）

将前端自「零构建原生 H5」切换为 **Vue 3 + Vite + TypeScript + Vant 4** 统一工程（ADR-012），**功能等价迁移** M001 全部现有页面，并把 FastAPI 静态托管切换到构建产物 `dist/`。本任务**不改任何 API 契约 / 后端业务 / 数据面 / M002 契约**，为 Task-002 前端基础 UI（M002 页面）与 M003~M007 全部后续 UI 提供统一承载工程。

## 2. Requirements（依据权威源，只读，禁止复制改写）

- **决策权威源**：`docs/adr/ADR-012.md`（Accepted；组件库=Vant 4、语言=TypeScript、路由 hash、axios 错误映射、Pinia、目录与托管约定）
- **变更执行登记**：`docs/changes/CHANGE-002.md`（范围/执行清单/DoD）
- **现有前端待迁移对象（等价面）**：`frontend/index.html`、`frontend/styles.css`、`frontend/app.js`（431 行：登录双主体/任务列表/任务编辑（题目 items 动态表单）/任务详情/学生档案（schools）/我的/导航与会话）
- **托管挂载点现状**：`backend/app/main.py`（StaticFiles `html=True`）、`backend/app/core/config.py`（frontend 目录配置）
- M001 API 契约（`docs/modules/M001/MODULE_API.md`，Frozen + Active）——axios 封装与类型层对齐对象

## 3. Scope（范围）

### 3.1 本任务交付

| 交付 | 说明 |
| --- | --- |
| Vue 工程 | `frontend/`：`package.json`/`package-lock.json`/`vite.config.ts`/`tsconfig*.json`/`index.html`（Vite 入口）；`src/`：main.ts/App.vue + router（hash 模式）+ stores（Pinia：会话/主体缓存）+ api（axios 实例与错误语义映射 400/401/403/404/409/413/415/422，对齐 API 契约）+ views/（各页面）+ components/ + styles（Vant 4 主题与移动响应式基线） |
| 页面迁移（等价） | M001 6 视图 + 导航/登出/会话恢复逐项等价迁移：登录（family/student 双主体入口切换）、任务列表、任务编辑（题目 items 动态增删表单、draft/published 编辑边界）、任务详情、学生档案（schools 下拉）、我的（学生子账号开通/停用/改密）；**禁止功能增删**（体验打磨不属本任务） |
| 托管与开发 | 生产：FastAPI `StaticFiles` mount → `frontend/dist`（settings 语义最小调整走 Request）；dev：Vite proxy `/api/v1` → `127.0.0.1:8000`；构建/开发脚本说明落 `README` 或任务记录 |
| 退役清理 | 删除零构建 `index.html`/`styles.css`/`app.js`（迁移完成并经冒烟后） |
| 文档回填 | M001 DESIGN（决策 1 前端形态 + 实现期决策新行）/FILES（L6 实况清单）/SUMMARY；`docs/ARCHITECTURE.md` 前端句引用 ADR-012；CHANGE-002 进度/复核节 |

### 3.2 Allowed-Files（可写）

- `frontend/**`（重建；Task-003 期间本目录为 **AGENT-M001 独占写权**——与 Task-002 前端 UI 段协调点见批注）
- `backend/app/main.py`、`backend/app/core/config.py`（仅静态托管指向 `dist` 的最小调整）
- `docs/modules/M001/**`（DESIGN/FILES/SUMMARY 前端实况回填）
- `docs/ARCHITECTURE.md`（前端技术架构句 + ADR-012 引用）
- `docs/changes/CHANGE-002.md`（执行进度/复核节）

### 3.3 Forbidden-Files / 边界

- **禁止改动任何 REST API 契约**（M001/M002 API、`API_REGISTRY.md`）与后端业务/数据面；禁止实现无契约接口
- 禁止修改 M002 契约九件套与 Task-002 后端范围；禁止自行分配 API/DATA/CHANGE/Task ID（`ID_GOVERNANCE.md`）
- 禁止新增业务功能或体验打磨（O-2/O-6 完整体验不属本任务）
- 禁止改动其他模块文档与治理层文档（INDEX/ROADMAP/PROJECT_STATUS/AGENT_REGISTRY 由 PM 同步，如有必要走 Request）

## 4. Dependencies / 环境

- Node ≥20 + npm（**PM 已预装 Node 20.19.0**）；构建期 npm install 需联网（ASM-010 已接受；锁文件入库）
- FastAPI 运行环境不变（`backend/.venv`，pytest 89 基线）；迁移期间保持 GET / 可访问（构建产物替换）
- Task-002（AGENT-M002）**后端编码并行不受阻**；其前端 UI 段在本任务验收前不触碰 `frontend/`

## 5. Expected Deliverables（完成即提交 PM 复核）

- Vue3+TS+Vant 4 工程落地；`npm run build` 产物 `dist/` 由 FastAPI 正常托管（GET / 200 + 页面功能冒烟）
- M001 页面等价迁移冒烟记录：双主体登录/登出/会话恢复、任务 CRUD + 题目 items 动态编辑、任务详情、学生档案、我的/子账号（对照原 app.js 行为逐项）
- 后端回归：`backend/.venv` `pytest` **89 全绿**；`vue-tsc`/lint 无错误
- M001 DESIGN/FILES/SUMMARY + ARCHITECTURE 回填；CHANGE-002 进度节更新
- 完成后：提交 PM 按 §6 DoD 复核 APPROVED → CHANGE-002 关闭

## 6. Acceptance Criteria（DoD，AGENT_GUIDE §6）

- [ ] Vite + Vue3 + TS + Vant 4 工程就绪（package/lock/vite.config/tsconfig/目录约定），`npm run build` 产出 `dist/` 且无类型错误
- [ ] M001 6 视图 + 导航/会话功能等价迁移（双主体、任务 CRUD + items 动态表单、学生档案、我的/子账号）；**零功能增删**
- [ ] FastAPI 托管 `dist/`；零构建三文件已退役删除；dev proxy 联调说明可用
- [ ] 冒烟记录 + pytest 89 全绿回归 + 类型/lint 干净
- [ ] M001 DESIGN/FILES/SUMMARY 与 ARCHITECTURE 前端实况回填（无契约/后端业务改动）
- [ ] 与 Task-002 前端接轨协调生效（AGENT-M002 未并行写 frontend）
- [ ] PM 复核 APPROVED → CHANGE-002 关闭（**关闭条件**：Task-002 前端基础 UI 按新栈实现并在其 DoD 冒烟通过后，由 PM 在 Task-002 复核时一并勾销）

> **PM 批注（2026-09-08，签发）**：写权协调——`frontend/**` 在本任务 Active 期间由 AGENT-M001 独占；Task-002（AGENT-M002）后端模块编码正常并行，其 §3.1「前端基础 UI」段**后移接轨**：在 Task-003 验收后按新栈（Vue 组件）实现（已在 Task-002 任务书加接轨批注）。若执行中发现契约面问题（如 dist 路径配置需后端结构调整超出 Allowed-Files）→ 以 Request 提交 PM，禁止自行扩大改动面。
