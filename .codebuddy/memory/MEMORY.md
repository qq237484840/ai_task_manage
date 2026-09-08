# MEMORY —— 长期项目记忆

> 就地更新说明：v0.5.0 → v0.6.0（2026-09-08）：Task-001 完成 —— M001 实现 + 54 测试通过 + 九件套实现版回填；M001 Testing，待 PM DoD 验收。

## 项目概览
- 仓库：`c:\DevProject\AI.TaskManage`，git 分支 main。
- **业务（V1，2026-09-08 由用户提供）**：中小学生 AI 作业与学习成长综合评定系统 —— V1 MVP =「AI 每日作业智能评定系统」，闭环：创建任务→上传照片→AI识别→任务匹配→质量评价→AI教师评价→今日报告。仅 M001~M007 七模块（需求原文 M01~M07），禁止知识图谱/画像/组卷/班级管理/多租户等（ADR-002）。
- **已确认技术决策（用户 2026-09-08 答复，全部落库）**：技术栈=移动优先 H5 + FastAPI + SQLite 单体（ADR-004）；身份=纯家庭模式，家庭账号家长=布置者+学生档案=评定对象、家庭级数据隔离（ADR-005）；正确度判定=分科混合，客观题对照参考答案/主观题不判对错并注明（ADR-006）；AI Provider=抽象+Mock 先行（ADR-007）；部署=单机/局域网 + SQLite + 本地图片目录（ASM-010）；学科=小学语数英书面作业起步、无法判断→标记+家长复核/重拍（ASM-011）。
- **学校基础资料（2026-09-08，M001 开发输入）**：学校字典=全局共享只读（seed 预置、后台维护暂缓），学生档案 `school_id` 必填关联，字段=名称+学段（ADR-008/REQ-009/DATA-011）；ADR-005 家庭隔离的唯一限定例外，学校管理域仍禁止。
- 采用「文档驱动 + 总控 Agent 治理 + 模块 Agent 实现」多 Agent 工程模式。用户提供的 #0~#107 方法论已落实为 docs/ 体系。
- 状态 **v0.6.0**：Phase 2 M001 模块开发（Testing）；**Task-001 完成**：backend（FastAPI 单体）+ frontend（零构建原生 H5）+ tests（54 passed）落地，M001 九件套实现版已回填；待 PM 按 DoD 验收 → 通过转 Stable → M002 契约。REQ-001~009 Approved；PD-001~009 全部确认。

## 用户偏好与决策（稳定事实）
- 文档语言：**中文为主**，代码/API 标识符英文。
- 文档体系分层渐进：模块九件套在模块划分时按真实模块生成，**勿建空模板文件**。
- 源码目录自 Task-001 起落地：`backend/`（含 `.venv`，Python 3.12）+ `frontend/` + `backend/tests/`；后端改动需同步回填 docs 与测试。
- ID 治理规范先行（ID_GOVERNANCE.md）；ID（M/API/REQ/ADR/CR/ACR/CHANGE/BUG/TD/RISK/ASM/AGENT）**仅由 Project Master 分配**，Agent 不得自行编号。
- 单条需求详情入 `docs/requirements/REQ-xxx.md`，需变更登记先 CR/ACR；普通增量改动记 `CHANGELOG.md`。
- README 只做入口，业务知识一律入 docs 分层，禁止知识重复/Single Source of Truth。
- 确认交互形式：一次 ask_followup 多问（≤4 题），选项带推荐标注，用户逐项答复后落库。
- **用户偏好复用**：后续项目均采用本治理模式。治理模板包位于仓库内 `ai-governance-template/`（v1.0.0，含 INSTALL.md；占位符 {{PROJECT_NAME}}/{{PROJECT_DIR}}/{{INIT_DATE}}）。新项目铺装=复制 docs/ + 按 INSTALL 替换占位符 + 确认默认假设。模板为复用资产，治理规范改进须回同步模板并递增版本。

## 关键索引
- 知识地图入口：`docs/INDEX.md`
- 状态：`docs/PROJECT_STATUS.md`（v0.6.0 / Phase 2 M001 Testing / PD-001~009）；假设：`docs/ASSUMPTIONS.md`（ASM-001~011）；决策：`docs/adr/ADR-001~008.md`
- 需求：`docs/REQUIREMENTS.md` + `docs/requirements/REQ-001~009.md`（Approved）；模块：`docs/MODULE_REGISTRY.md`（M001 Testing，M002~M007 Planned）；API：`docs/API_REGISTRY.md`（API-M001-001~012 **Frozen**，改须 CR）；数据：`docs/DATA_MODEL.md`（DATA-001~011）；Agent：`docs/AGENT_REGISTRY.md`（AGENT-M001 Active / Task-001 已完成）；风险：`docs/RISK_REGISTER.md`（RISK-001~005）
- 当前阶段：Phase 2 M001 模块开发（Testing）—— 工程落地：`backend/app/`（core/shared/api/v1/modules/m001）+ `frontend/`（**零构建原生 H5**，FastAPI 静态托管；Vue3+Vite 仅为可替换壳）+ `backend/tests/`（54 passed，venv 于 `backend/.venv`）。核心实现事实：请求级统一 commit/rollback；`_UNSET` 哨兵 PATCH 清空语义；SQLite FK 开启；schools seed 幂等；`_TRANSITIONS` 表驱动状态机 + mark_in_progress 幂等；越权 REST 对外 404 / 内部接口 403。文档九件套实现版已回填（FILES/TEST/DESIGN 含实现期决策记录 10 条）。**待办：PM 按 DoD（AGENT_GUIDE §6）验收 M001 → 通过转 Stable → 进入 M002 契约设计**。实现/编码细节见 `docs/modules/M001/MODULE_*.md` 与 `.codebuddy/memory/2026-09-08.md`。
- 治理模板包：`ai-governance-template/`（README v1.0.0 / INSTALL.md）。
