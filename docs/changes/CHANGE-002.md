# CHANGE-002 —— 前端技术栈切换（零构建原生 H5 → Vue3 + Vite + TypeScript + Vant 4）

- **CHANGE ID**：CHANGE-002 ｜ **状态**：**执行中（Executing）**（2026-09-08 用户三项决策点确认后立项；Task-003 已签发） ｜ **日期**：2026-09-08
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

- [ ] Vite + Vue3 + TS + Vant 4 工程就绪（`package.json`/`lock`/`vite.config.ts`/`tsconfig*`/目录约定），`npm run build` 出 `dist/`
- [ ] M001 6 视图 + 导航/会话**功能等价迁移**（双主体登录/登出/会话恢复、任务 CRUD + items 动态表单、学生档案、我的/子账号开通改密）
- [ ] FastAPI 托管 `dist/`，`GET /` 返回构建应用；dev proxy 可联调；零构建三文件已删除
- [ ] 冒烟记录 + pytest 89 全绿回归 + 类型检查/lint 无错误
- [ ] M001 DESIGN/FILES/SUMMARY 与 ARCHITECTURE 前端实况回填；未触碰任何 API 契约与后端业务
- [ ] Task-002 前端接轨注记生效（其前端 UI 段等待新栈，后端并行不受阻）

## 处理路径

用户技术方案变更 → 可行性评估 + 3 决策点确认（2026-09-08）→ ADR-012 Accepted → **CHANGE-002 立项（Executing）+ Task-003 签发（AGENT-M001）** → 执行 → 回填 → PM 复核（DoD）→ 关闭。随后 Task-002 前端 UI 段按新栈接轨（AGENT-M002）。
