# M001 模块变更历史

| 版本 | 日期 | 作者 | 变更 |
| --- | --- | --- | --- |
| v0.7.0 (验收) | 2026-09-08 | Project Master | **PM DoD 验收 APPROVED（用户：验收通过）**：Task-001 交付物按 `AGENT_GUIDE.md` §6 全项通过 → M001 Testing→**Stable**（契约 v0.1.1 Frozen 不变，API-M001-001~012 未越契约）。M001 进入维护态，M002 契约设计启动。 |
| v0.6.0 (实现) | 2026-09-08 | Project Master | **Task-001 实现回填**：M001 编码+测试完成（54 passed）——模块状态 Developing→Testing；工程落地 backend/（FastAPI）+ frontend/（零构建 H5）+ tests/；九件套实现版同步（FILES/TEST/DESIGN）；API 契约未变更（保持 Frozen）。详见项目 `CHANGELOG.md` v0.6.0。 |
| v0.1.1 (Frozen) | 2026-09-08 | 用户 + Project Master | **批准**：用户批准 M001 契约草案 v0.1.1（签署区见 `MODULE_CONTRACT.md`）→ Contract/API/Data 基线冻结；M001 转 Developing，签发 Task-001（AGENT-M001）。 |
| v0.1.1 | 2026-09-08 | Project Master | 契约草案迭代：用户 M001 开发输入增补"学校基础资料"（REQ-009/ADR-008/DATA-011）——新增 `schools` 全局只读字典表（seed 预置、无运行期写路径）；`students.school` 自由文本 → `school_id` 必填（FK→schools）；新增 API-M001-012（GET /schools）；档案 DTO 携带学校信息。九件套同步至 v0.1.1。 |
| v0.1.0 | 2026-09-08 | Project Master | 契约草案发布：M001 定位为家庭空间 + 作业任务生命周期基座（ADR-004/005/006）；九件套 v0.1 产出；API-M001-001~011 登记（Draft）。状态：待用户批准（签署区见 `MODULE_CONTRACT.md`）。 |
