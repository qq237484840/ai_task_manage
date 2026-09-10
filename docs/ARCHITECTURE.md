# ARCHITECTURE —— 系统级知识（L1）

> 权威源：本文是「系统架构」的唯一权威来源。模块内部设计进入各模块 `MODULE_DESIGN.md`，本文只描述系统级结构。
>
> 状态：**V1 高层草案，关键决策已确认**（2026-09-08）。技术栈/身份/AI 策略见 ADR-004~007；PD-007/008 默认假设见 `ASSUMPTIONS.md`（ASM-010/011）；任何架构变更走 ACR（见 `DEVELOPMENT_GUIDE.md`）。
>
> **2026-09-10 架构变更（v0.13.0，CR-003 / ADR-013，Accepted）**：作业评定改为 **「事实层按天 + 聚合层跨天」双层模型**——**事实层** `tasks` 唯一键 `(student_id, category, belong_date)`（**`task_items` 逐题建模废弃**）；**聚合层** `task_groups` → `task_group_subjects`（**★判定单元**）→ `photo_subject_links`（**N:N**）→ `completion_analyses`；**挂接与判定落聚合层**（判定粒度 = 聚合子任务级）；**ADR-010 判定粒度 Superseded**（其余原则继承）；新增横切 **`app/core/ai/`**（Provider 抽象 + prompt + 结果 schema 校验 + 降级）。**本文下方分层图 / 模块关系 / 数据流已就地修正。**
>
> **2026-09-10 V1 范围与执行方（v0.14.0，`ADR-014`）**：**V1 有效模块 = M001 + M002 + 横切 `app/core/ai/`**；**M003/M004 职责并入 M001（链路 T）/ M002（链路 H）**（Module ID 保留、状态 Deferred）；**M005~M007（评价/评语/报告）→ Deferred（V2）**；横切 `app/core/ai/` **执行方 = `AGENT-AI`**（Task-006）。**架构分层与数据流在 V1 内以「完成结论」为终点，评分/评语/报告不计入 V1 链路。**

## 系统总体架构（草案）

逻辑分层（为可替换、可测试、不绑定单模型）：

```text
表现层(移动优先 H5, ADR-004)    「任务」上传布置单 / 「作业」上传照片 / 逐张复核确认 / 报告查看
        ↓ HTTP(S) JSON API + H5 静态资源
API / 应用编排层                各模块对外 API（契约在模块 MODULE_API.md）
        ↓
领域模块层                      M001 作业任务管理（含归属引擎 WindowResolver）
   ├─ 事实层（按天）            tasks（唯一键 (student_id, category, belong_date)）
   │                            task_contents / task_spec_sources / photos（按天归属）
   └─ 聚合层（跨天）            task_groups（policy_version）→ task_group_subjects(★判定单元)
                                → photo_subject_links(N:N) → completion_analyses
   （其余模块）                 M002 采集与挂接（**V1**）；~~M003 识别 / M004 匹配 / M005 评价 / M006 教师评价 / M007 报告~~ → **Deferred**（`ADR-014`：M003/M004 并入 M001/M002，M005~M007 后置 V2）
        ↓
横切 AI 接入层（基础设施）      `app/core/ai/`（**执行方 = `AGENT-AI` / Task-006**）：Provider 抽象 + prompt 管理 + 结果 schema 校验 + 降级
                                Vision Provider / OCR Provider / LLM Provider（+ 统一调用记录 DATA-009）
        ↓
数据存储(SQLite + 本地图片目录) 任务/聚合/图片/挂接/完成分析/评价/报告数据
```

约束：禁止巨型 Service/Controller；AI Prompt 与评分规则不得散落代码（须集中为模块内独立资产；V1 的 prompt 资产集中在横切 `app/core/ai/`）；评分权重必须配置化（随 M005 后置 V2 生效）。

## 技术架构

- 后端：Python **FastAPI** 单体应用；同一进程提供 HTTP JSON API + 前端静态资源（Vite 构建产物 `frontend/dist`）+ 图片文件服务
- 使用端：**移动优先响应式 H5**（前端工程 = Vue3 + Vite + TypeScript + Vant 4，见 **ADR-012**；开发期前端由 Vite dev server 提供并代理 `/api/v1` 到后端）；作业拍照经浏览器相机（`input capture`），手机/平板/桌面浏览器统一访问
- 数据：**SQLite** 单文件；图片存本地受控目录；存储访问经统一抽象，为迁移 PostgreSQL / 对象存储预留
- 选型理由与影响见 **ADR-004**（PD-003 已确认）；部署默认见 ASM-010
- 并发/性能边界：V1 家庭低并发场景；图片上传链路需体积控制与限流（M002 实现时落实可验证指标）

## AI Provider 抽象（V1 强制）

- 业务逻辑不得绑定某单一模型；至少抽象：Vision / OCR / LLM 三类 Provider
- 每次 AI 调用记录：model / prompt_version / request_id / latency / token_usage / result / confidence / error
- Prompt 版本化管理（用于可追溯，见 ADR-003）
- 接入策略：**真实三方默认**（v0.9.0 定稿 ADR-011，取代原 Mock 先行 ADR-007）——OCR/Vision/LLM 默认对接真实第三方 Provider，Mock 降级为测试桩与离线降级（`mock-*` 标注）；统一接口 + Provider 实现类可替换，业务代码不感知；**ACR-002 已批准（2026-09-08），ADR-011 正式生效**

## 部署架构

- V1 默认：**联网访问第三方 AI + 单进程部署**（开发、演示、家庭自用；ASM-010 已修订 v0.9.0：真实三方默认需联网，离线显式切 Mock），单进程（uvicorn）承载 API + H5 + 图片静态目录
- 存储：SQLite 单文件 + 本地图片目录；备份 = 数据库 dump + 图片目录整体备份（ASM-010，PD-007 默认待用户复核）
- AI 外部依赖经 Provider 抽象隔离（真实三方默认，离线/无密钥时降级 Mock 并标注，本地可无外网演示但不作为默认）
- 演进（上云/反代/对象存储/PostgreSQL）在存储与服务抽象内替换，不改变业务代码

## 数据架构

- 数据详情权威源：`DATA_MODEL.md`
- V1 核心实体沿**双层模型**产生：**事实层**（任务（按天）/ 内容项 / 输入源 / 提交照片（按天归属））→ **聚合层**（聚合 `task_groups` / 聚合子任务（**★判定单元**）/ 照片挂接 N:N / 完成分析）→ 六维质量评价 → 教师评价 → 今日报告；外加 AI 调用日志（可追溯）与用户档案（纯家庭模式，ADR-005）
- **事实层与聚合层的边界（ADR-013）**：事实层**按天唯一且不可回算**（`belong_date`/`week_index` 上传即固化）；聚合层**跨天**且受 `policy_version` 锁定（配置变更只影响未聚合对象）；**挂接与判定只在聚合层**
- 未成年人作业照片属敏感数据，存储与访问须受控（见 `DATA_MODEL.md` 敏感级别）

## 服务架构

V1 按单体部署优先（单进程或多模块同库），**不做微服务拆分**（避免过度设计，见 DEVELOPMENT_GUIDE）；是否拆独立服务由技术栈与部署确认后决定。**V1 有效模块 = M001 + M002 + 横切 `app/core/ai/`**（`ADR-014`；M003~M007 登记保留、状态 Deferred，不参与 V1 开发），各模块在代码与文档层独立，经接口协作。

## 模块关系（依赖图）

```text
M002 ─► M001（读取任务 + 聚合上下文，随 CR-003 修订）
M001 / M002 ─► app/core/ai/（横切基础设施，非模块依赖；执行方 = AGENT-AI / Task-006）
—— 以下不属 V1（ADR-014：M003/M004 职责已并入 M001/M002，M005~M007 后置 V2）——
M005 ─► M001/M002（聚合子任务级结论，承 M002）    【V2】
M006 ─► M005                                     【V2】
M007 ─► M001, M002, M005, M006                    【V2】
```

- 禁止循环依赖；发现即停止相关开发并重新设计
- 模块间只允许依赖 API/Interface/DTO/Event/Message/Contract；禁止跨模块依赖内部 Class/Repository/数据库
- 共享代码仅放真正跨模块通用内容（AI Provider 抽象、日志、异常、通用 DTO），禁止业务逻辑入 Common

## 外部系统

- AI Provider（OCR/Vision/LLM）为 V1 最主要外部依赖；接入策略 = 真实三方默认（ADR-011，取代 ADR-007 Mock 先行），首个真实三方接入后登记 `EXTERNAL_SYSTEMS.md`；照片/作答出域至三方须满足 RISK-009 合规口径（隐私声明/最小化传输）
- 其余待识别

## 核心数据流

```text
「任务」上传输入源(M001：图片 / 粘贴文本) ─► AI 解析草稿(链路 T) ─► 家长确认 ─► 按天任务记录
「作业」上传照片(M002：质量检测/预处理，不填内容) ─► 归属日/周次固化（AT_DAY_CUTOFF）
    ─► 聚合生成(members 按 window_type 合并；policy_version 锁定) ─► AI 挂接建议(链路 H)
    ─► 逐张复核(accept/reject/改挂) ─► 窗口级门控(全部确认) ─► 聚合子任务级完成结论(草稿) ─► 家长确认
    ─►【V1 链路终点】；以下为 **V2**（ADR-014）：六维评分(M005) ─► 教师评价(M006) ─► 报告(M007：按聚合/周次)
```

> 链路 T 与链路 H **不分先后**（并行）；主任务级按归属窗口**确定性匹配**，**子任务（学科）级仍需 AI 判定**。

全链路可追溯：任何 AI 评价均可回溯 原始图片→预处理→OCR→AI 输入→Prompt 版本→AI 输出→规则处理→最终评价（调用链数据落 AI 调用记录，见 DATA_MODEL）。

## 核心业务流

- 主流程：家庭账号（家长，对应需求语境"教师"）布置任务 → 本家庭学生档案上传 → AI 处理链 → 报告
- 分支流：图片质量不合格 → 提示重新拍摄；AI 无法判断 → 标记"无法判断"并进入人工确认/重拍
- 重写判断分级：无需重写 / 建议订正 / 建议重写部分题目 / 建议重新完成本项作业；禁止仅凭单次 AI 判断强制重写

## 安全边界

- 认证/授权：家庭账号注册/登录 + **家庭级数据过滤**（纯家庭模式，ADR-005）；业务 API 强制家庭归属校验
- 未成年人图片与个人信息：敏感信息不入普通日志；本地图片目录受控访问与访问审计；加密与访问细节按 DATA-002/003 高敏感要求落地（见 DATA_MODEL 敏感级别）
- Secret 管理：AI Provider Key、数据库口令等禁止硬编码，走配置/环境/密钥管理

## 性能边界

- 待量化后登记（用户交互链路涉及图片上传与 AI 调用，需在技术栈确认后给出可验证指标，禁止"性能要好"式描述）
