# REQUIREMENTS —— 需求登记总表（权威源）

> 维护：Project Master。需求是工程链的源头（需求 → 模块 → 代码 → 测试）。
> 状态：**V1 已批准（Approved，需求基线冻结）**。2026-09-08 依据用户提供的「V1 MVP 总控 Agent 指令」录入；PD-001~008 全部确认（ADR-002~007、ASM-001~011），REQ-001~008 于 2026-09-08 冻结为 V1 需求基线；同日按 M001 开发输入增补 **REQ-009（学校基础资料）→ Approved**（决策见 ADR-008）。单内"待确认点"为历史决策记录，已确认者以 ADR/ASM 为准，残留条目在后续变更审批时精校。
> **禁止任何 Agent 自行创建 REQ ID**（规则见 `ID_GOVERNANCE.md`）。
>
> 模块 ID 别名说明：需求原文使用 `M01~M07`，本项目正式 Module ID 为 `M001~M007`（对应关系见 `MODULE_REGISTRY.md`，本表使用正式 ID）。

## 需求登记表

| REQ ID | 标题 | 来源 | 优先级 | 状态 | 关联模块 | 关联 API | 测试 | 需求详情 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | 作业任务管理 | V1 指令 §二/§五/§十五 | P0 | Approved | M001 | 待模块契约 | 待设计 | `requirements/REQ-001.md` |
| REQ-002 | 作业图片采集与质量检测 | V1 指令 §二/§五/§十五 | P0 | Approved | M002 | 待模块契约 | 待设计 | `requirements/REQ-002.md` |
| REQ-003 | AI 作业识别 | V1 指令 §二/§九/§十 | P0 | Approved | M003 | 待模块契约 | 待设计 | `requirements/REQ-003.md` |
| REQ-004 | 作业任务匹配 | V1 指令 §二/§十 | P0 | Approved | M004 | 待模块契约 | 待设计 | `requirements/REQ-004.md` |
| REQ-005 | AI 作业质量评价（六维度） | V1 指令 §二/§八/§十 | P0 | Approved | M005 | 待模块契约 | 待设计 | `requirements/REQ-005.md` |
| REQ-006 | AI 教师评价与改进建议 | V1 指令 §二/§六/§七 | P0 | Approved | M006 | 待模块契约 | 待设计 | `requirements/REQ-006.md` |
| REQ-007 | 今日作业综合报告 | V1 指令 §二/§八/§十五 | P0 | Approved | M007 | 待模块契约 | 待设计 | `requirements/REQ-007.md` |
| REQ-008 | V1 横切工程与 AI 治理约束 | V1 指令 §九~§十二/§十六 | P0 | Approved | 全局（M003/M005/M006 等） | 待模块契约 | 待设计 | `requirements/REQ-008.md` |
| REQ-009 | 学校基础资料（全局共享字典 + 档案必填关联） | 用户 M001 开发输入增补（2026-09-08） | P0 | Approved | M001（承载，不设独立模块） | API-M001-012（草案） | 待设计 | `requirements/REQ-009.md` |

状态机：`Draft → Approved → In Progress → Done → Deprecated`
优先级：`P0 必须 / P1 重要 / P2 一般 / P3 可选`

## 需求来源与版本

| 版本 | 说明 | 日期 |
| --- | --- | --- |
| V1 MVP | AI 每日作业智能评定系统（用户提供开发指令） | 2026-09-08 |

## 可追踪性要求

每条需求必须形成闭环：`需求 → 模块 → 代码 → 测试`。V1 需求 → 模块对应关系固定为：REQ-00x ↔ M00x（REQ-008 为横切约束，落实到各模块设计与 DoD）。追踪断链视为质量问题，须优先修复。

## 需求录入流程

1. 用户提出需求 → Project Master 判断类型并分配 `REQ-xxx`
2. 单条需求详情进入 `docs/requirements/REQ-xxx.md`
3. 需求经影响分析后决定模块归属并跟踪到代码与测试
