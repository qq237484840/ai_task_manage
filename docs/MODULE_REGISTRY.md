# MODULE_REGISTRY —— 模块登记表

> 这是全项目最重要的导航文件之一。
> 维护：Project Master。模块划分/新增/变更时更新。
>
> 状态：**V1 已登记**（2026-09-08）。模块由「V1 MVP 总控 Agent 指令」§二 指定。需求基线已批准（REQ-001~009 Approved，2026-09-08 增补 REQ-009 学校基础资料，承载于 M001）。M001 契约 v0.1.1 已获用户批准 → **Frozen**，模块进入 Developing（Task-001）；M002~M007 按顺序契约（M001 验收后进入）。
> **禁止任何 Agent 自行创建 Module ID**；新模块流程见 `DEVELOPMENT_GUIDE.md`。
>
> 别名说明：需求原文使用 `M01~M07`；本项目正式 Module ID 为 `M001~M007`（M01→M001，依此类推）。文档引用一律使用正式 ID。

## 模块登记表

| Module ID | 名称 | Domain | Purpose | 状态 | Owner Agent | 依赖 | 消费者 | Public APIs | 数据所有权 | 文档路径 | 版本 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M001 | 作业任务管理 | 作业评定 | 创建/维护作业任务，评分对照基准来源 | Testing（Task-001 完成：实现 + 54 项测试通过，待 PM DoD 验收） | AGENT-M001 | 无（基座） | M002, M004, M005, M007 | `MODULE_API.md`（API-M001-001~012） | DATA-001、DATA-002（随 M001 落地）+ DATA-011（学校字典，公共只读） | `docs/modules/M001/` | v0.1.1 |
| M002 | 作业图片采集 | 作业评定 | 上传/拍摄作业照片、质量检测、预处理与存储 | Planned | AGENT-M002 | M001 | M003, M007 | 待模块契约 | DATA-003 | `docs/modules/M002/` | 待定 |
| M003 | AI 作业识别 | 作业评定 | OCR/Vision 识别图片为结构化内容（含置信度） | Planned | AGENT-M003 | M002(数据) | M004, M005 | 待模块契约 | DATA-004 | `docs/modules/M003/` | 待定 |
| M004 | 作业任务匹配 | 作业评定 | 识别结果与任务题目对齐（可观察依据） | Planned | AGENT-M004 | M001, M003 | M005 | 待模块契约 | DATA-005 | `docs/modules/M004/` | 待定 |
| M005 | AI 作业质量评价 | 作业评定 | 六维度评分（配置化权重） | Planned | AGENT-M005 | M001, M003, M004 | M006, M007 | 待模块契约 | DATA-006 | `docs/modules/M005/` | 待定 |
| M006 | AI 教师评价与改进建议 | 作业评定 | 可观察行为式评语 + 分级重写建议 | Planned | AGENT-M006 | M005 | M007 | 待模块契约 | DATA-007 | `docs/modules/M006/` | 待定 |
| M007 | 今日作业综合报告 | 作业评定 | 聚合当日评价输出综合报告 | Planned | AGENT-M007 | M001, M002, M005, M006 | 用户（展示） | 待模块契约 | DATA-008 | `docs/modules/M007/` | 待定 |

共享/基础设施（不属于业务模块，代码落地时建立，治理规则见 `DEVELOPMENT_GUIDE.md` §13）：
- AI Provider 抽象层（Vision/OCR/LLM + 统一调用记录 DATA-009）
- shared（通用 DTO/工具）、infrastructure（日志/异常/配置/存储）

## 模块 ID 规则

- 格式 `M001`、`M002`… 连续编号，不重复（规则见 `ID_GOVERNANCE.md`）
- **Module ID 一经分配不随意修改**；模块名可改
- 每个模块文档集存放于 `docs/modules/Mxxx/`，九件套清单见 `AGENT_GUIDE.md`
- V1 仅开放上表 7 个模块；任何新模块（含未来功能）须经 Project Master 走变更流程，禁止擅自扩展范围（ADR-002）

## 模块状态机

`Planned → Designing → Developing → Testing → Reviewing → Stable → Deprecated → Archived`

## 模块拆分 / 合并判断

拆分触发：职责、生命周期、变化频率、数据所有权、权限、测试边界、部署需求、扩展方向明显不同。
合并触发：高度耦合、生命周期一致、职责重叠、数据边界无法分离、独立价值很低。
（V1 模块边界由需求 §二 指定；后续如需拆分/合并按上述标准评估并走变更流程，禁止仅因"文件太多"机械拆分）
