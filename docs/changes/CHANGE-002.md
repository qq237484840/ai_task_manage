# CHANGE-002 —— 前端技术栈切换（零构建原生 H5 → Vue3 + Vite + TypeScript + Vant 4）

- **CHANGE ID**：CHANGE-002 ｜ **状态**：**执行中（Executing）——Task-003 DoD 已复核 APPROVED（2026-09-09），关闭条件待勾销（见复核记录）** ｜ **日期**：2026-09-08（立项）｜ **DoD 复核**：2026-09-09 PM APPROVED
- **提出者**：用户（技术方案变更）→ Project Master 可行性评估 ｜ **执行 Agent**：AGENT-M001（Task-003）
- **依据**：`docs/adr/ADR-012.md`（**Accepted**，PD-025）；用户决策点 Q1=Vant 4 移动库 / Q2=TypeScript / Q3=独立前置任务 + Task-002 后段接轨
- **关联文档**：`docs/agents/Task-003.md`（任务书）、`docs/agents/Task-002.md`（前端段接轨注）、M001 DESIGN/FILES/SUMMARY（前端实况回填）、`ARCHITECTURE.md`、`PROJECT_STATUS.md`（O-6 关闭）

## 变更范围（Single Source of Truth = ADR-012）

| 面 | 内容摘要 | 影响范围 |
| --- | --- | --- |
| 工程化 | `frontend/` 重建为 Vite + Vue3 + TS 工程（`src/`：views/components/api/stores/router/types；Vant 4 组件库；Vue Router 4 hash 模式；Pinia；axios 错误语义封装） | frontend 全目录（零构建三文件退役删除） |
| 页面迁移 | M001 现有 6 视图功能**等价迁移**：登录（family/student 双主体）、任务列表、任务编辑（题目 items 动态表单）、任务详情、学生档案（schools 选择）、我的（学生子账号开通/改密）+ 导航/会话 | frontend/src（无功能增删，体验打磨留后续 UI 任务） |
| 托管切换 | FastAPI 静态挂载由零构建目录 → **构建产物 `frontend/dist`**（挂载点沿用 settings 语义最小调整，走 Request 控制）；dev = Vite proxy | `backend/app/main.py`（或 config，最小改动） |
| 接轨 | Task-002（M002）前端基础 UI 在 Task-003 验收后按新栈实现（上传/质检报告/归属页面为 Vue 组件）；Task-003 期间 AGENT-M002 不写 frontend | `docs/agents/Task-002.md` 注记 + AGENT_REGISTRY 协调 |
| 文档回填 | M001 DESIGN/FILES/SUMMARY（前端实况 = Vue 工程 + dist 托管）；ARCHITECTURE 前端句引用 ADR-012 | M001 九件套前端段、ARCHITECTURE |

**明确不做**：不改任何 REST API 契约 / 后端业务 / 数据面 / M002 契约；不改运行部署形态（单进程 FastAPI + 静态 dist）；不实现 O-2/O-6 完整体验打磨。

## 执行清单

1. 阅读 ADR-012 + 现有 `frontend/` 三文件 + `backend/app/main.py`/`core/config.py` 挂载点，确认迁移等价面
2. 工程搭建：Vite（vue-ts 模板）+ 目录约定 + Vant 4 全量/按需引入 + Vue Router（hash）+ Pinia + axios 封装（错误码映射 400/401/403/404/409/413/415/422）+ 环境（dev proxy / build）
3. 页面迁移：登录（双主体）/任务列表/任务编辑（items 动态表单）/任务详情/学生档案/我的 + 导航/登出/会话恢复（等价实现，禁止功能增删）
4. 托管切换：main.py 静态 mount → `dist`；`npm run build` 产物验证 GET / 与 API 代理冒烟；零构建三文件删除
5. 冒烟与回归：M001 功能冒烟清单逐项（对照原 app.js 行为）+ `backend/.venv` pytest **89 全绿回归** + `vue-tsc`/lint 干净
6. 回填：M001 DESIGN（决策 1 前端形态更新 + 新实现期决策行）/FILES（L6 实况清单）/SUMMARY；`ARCHITECTURE.md` 前端句引用 ADR-012；CHANGE-002 进度/复核节

## 验收标准（DoD，随任务书 Task-003 §6 勾选）

- [x] Vite + Vue3 + TS + Vant 4 工程就绪（`package.json`/`lock`/`vite.config.ts`/`tsconfig*`/目录约定），`npm run build` 出 `dist/`
- [x] M001 6 视图 + 导航/会话**功能等价迁移**（双主体登录/登出/会话恢复、任务 CRUD + items 动态表单、学生档案、我的/子账号开通改密）
- [x] FastAPI 托管 `dist/`，`GET /` 返回构建应用；dev proxy 可联调；零构建三文件已删除
- [x] 冒烟记录 + pytest 89 全绿回归 + 类型检查/lint 无错误
- [x] M001 DESIGN/FILES/SUMMARY 与 ARCHITECTURE 前端实况回填；未触碰任何 API 契约与后端业务
- [x] Task-002 前端接轨注记生效（其前端 UI 段等待新栈，后端并行不受阻）

## 处理路径

用户技术方案变更 → 可行性评估 + 3 决策点确认（2026-09-08）→ ADR-012 Accepted → **CHANGE-002 立项（Executing）+ Task-003 签发（AGENT-M001）** → 执行 → 回填 → **PM 复核（2026-09-09，Task-003 DoD 全项 APPROVED）** → **关闭（待关闭条件：Task-002 前端基础 UI 按新栈实现并在其 DoD 冒烟通过后，由 PM 在 Task-002 复核时一并勾销）**。随后 Task-002 前端 UI 段按新栈接轨（AGENT-M002）。

## 执行进度（Task-003 / AGENT-M001，2026-09-08）

- **1 工程搭建（完成）**：`frontend/` 重建为 Vite 5 + Vue3 + TS 严格 + Vant 4 工程（`package.json`/`package-lock.json`/`vite.config.ts`/`tsconfig*.json`/`index.html`）；`src/` 目录约定（views/components/api/stores/router/types/utils/styles）；Vue Router 4 hash + 登录守卫；Pinia 会话 store（token/loginName/subject 双主体）；axios 封装统一错误语义映射（400/401/403/404/409/413/415/422，401 自动清会话回登录）；dev proxy `/api/v1` → `127.0.0.1:8000`
- **2 页面迁移（完成，功能等价）**：M001 6 视图 + 导航/登出/会话恢复逐项迁移 —— 登录（**家长 / 学生 / 注册三 Tab**，学生登录存显示名 + subject=student）、任务列表（状态筛选+FAB）、任务编辑（items 动态增删、draft/published 编辑边界、组号/科目）、任务详情（状态推进、题目展示）、学生档案（schools 按学段下拉）、我的（family=**学生子账号开通/停用开关/改密**；student=只读提示）；BottomNav 三 Tab；**零功能增删**
- **3 托管切换（完成）**：`backend/app/core/config.py` `frontend_dir` → `frontend/dist`（env 可覆盖）；`backend/app/main.py` 挂载注释更新（目录不存在则仅 API）；零构建 `frontend/app.js`/`styles.css` 删除、`index.html` 重建为 Vite 入口；构建/开发说明落 `frontend/README.md`；`.gitignore` 忽略 `node_modules/`+`dist/`
- **4 冒烟与回归（完成）**：`npm run build`（vue-tsc 无类型错误 + vite build 成功，380 modules → dist 产出）；`GET /` 返回 Vite 构建应用（FastAPI 托管 200）；后端 `pytest` **89 passed 全绿**；API 全链冒烟 **19 步全通过**（家庭注册/登录、schools、学生建档、子账号开通、学生登录/me/仅本人列表、学生越权建档 403、任务创建(容器 subject=None+客观/主观 items)/publish/详情、学生任务列表、停用→登录 401、启用+改密→登录成功、双登出）
- **5 回填（完成）**：M001 DESIGN（决策 1 退役注 + **决策 16**）/FILES（L6 Vue 工程实况）/SUMMARY（Key Decisions + API-M001-013~017 行修正）与 ARCHITECTURE（技术架构前端句引用 ADR-012 + dist 托管）已按实况更新；未触碰任何 API 契约与后端业务逻辑

## 复核记录（2026-09-09，Project Master）

- **复核方式**：执行方进度自证 + **独立证据复核**（复核时点实测，不单采信自述）——
  - `backend/.venv` `pytest` → **89 passed**（独立重跑）；
  - `frontend/dist/index.html` + 按视图分包 hashed assets 在（对应当日 `vue-tsc` 无类型错误 + `vite build` 380 modules 成功产物）；`app.js`/`styles.css` 已不存在（退役），`index.html` 为 Vite 入口；
  - `frontend/README.md`（构建/开发/dist 托管说明）与 `package-lock.json` 已落盘；`GET /` FastAPI 托管 dist 200 + API 全链冒烟 19 步通过记录在案；
  - M001 DESIGN（决策 1 退役注 + 决策 16）/FILES（L6 Vue 实况）/SUMMARY 与 ARCHITECTURE（ADR-012 前端句）回填抽查一致；git 改动面仅 `main.py`/`config.py` 托管最小调整，未触碰任何 API 契约与后端业务逻辑。
- **结论**：**DoD 全项通过 → APPROVED（2026-09-09）**；Task-003 状态 → 已完成（AGENT-M001）；本变更进入「已复核、待关闭条件」。
- **关闭条件（遗留）**：Task-002 前端基础 UI 按新栈（Vue 组件）实现并在其 DoD 冒烟通过后，由 PM 在 **Task-002 复核**时一并勾销本变更（此时 CHANGE-002 → 已完成/Applied）。
