# CONFIGURATION —— 配置项登记

> 维护：Project Master。新增/变更配置项必须登记本表；未登记的配置项视为文档漂移。
> 机制：pydantic-settings（`backend/app/core/config.py`），环境变量前缀 **`AT_`**，支持 `.env`。
> V1 **无家长端配置编辑入口**，配置由部署侧（环境变量 / `.env`）设定。
> 本次登记范围 = `CR-003` 新增的归属与窗口配置 + `Task-006`（`AGENT-AI`）AI 接入层配置；既有配置项见文末"待登记"。

## 一、生效与锁定规则（适用全部窗口/归属类配置，ADR-013）

| # | 规则 |
| --- | --- |
| 1 | 配置变更**只影响未聚合的对象**：尚未生成聚合的 `(学生, 归属窗口)` 按**当前生效**配置聚合 |
| 2 | **已聚合的按生成时的配置**：`task_groups.policy_version` 记录生成时生效的配置版本，后续**追加数据不改**该字段 |
| 3 | 锁定**粒度** = 每个 `(学生, 聚合对象)` **独立锁**（同一日期：小明可走旧配置、小红走新配置） |
| 4 | 锁定**触发条件** = **数据写入**（任务解析完成 / 作业照片上传）；**纯浏览不触发锁定**（进列表页只 `ensure_group`，不锁配置） |
| 5 | 事实字段（`belong_date` / `week_index`）**上传时固化**，配置变更**不回算历史**（改 4 点边界不迁移历史照片） |

来源：`docs/adr/ADR-013.md`、`docs/requirements/CLARIFICATION-2026-09-10.md` §2.B（Q11~Q13 定稿）。

## 二、归属与窗口配置（CR-003 新增）

| 配置项 | 环境变量 | 字段名 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| 时区 | `AT_TIMEZONE` | `timezone` | `Asia/Shanghai` | 归属日 / 周次计算的时区，**固定不跟随设备**（时间戳仍按 UTC 存储，仅在归属计算处转换） |
| 学期开始日 | `AT_TERM_START` | `term_start` | 部署侧填写 | `week_index` 起算基准 = 该日**所在周的周一**（学期开始日非周一时，第 1 周为半周） |
| 学期结束日 | `AT_TERM_END` | `term_end` | 部署侧填写 | 学期区间外 = **假期**（V1 假期按自然周聚合） |
| 归属日边界 | `AT_DAY_CUTOFF` | `day_cutoff` | `04:00` | 日界，`belong_date = (ts − cutoff).date()`；例：9/9 20:00 与 9/10 03:00 同归 **9/9** |

## 三、窗口策略（聚合规则，随 CR-003）

| 规则 | V1 取值 |
| --- | --- |
| 单日聚合 | 每个 `belong_date` 至少一个聚合（**最小聚合 = 1 天**）；周一到周四各自一个聚合 |
| 周末聚合 | **周五 04:00 ~ 周一 04:00** 合并为一个"**周末作业**"聚合（成员 = 周五/周六/周日三个 `belong_date`） |
| 周次分组 | 按 `week_index` 分组展示（"第 N 周"），起点由 `AT_TERM_START` 决定 |
| 假期聚合 | 按**自然周**分段（`H:<起始日>.W1`、`.W2`…）；假期"完成计划 / 评估报告 / 汇总简报"**后置 V2** |
| 解析器 | 抽为策略接口 `WindowResolver.resolve(ts) → {belong_date, week_index, window_type, group_key}`，便于后续替换规则 |

注：窗口策略变更同样适用第一节的生效与锁定规则（**配置不回溯、数据可增补**）。

## 四、待登记（既有配置项，本次不擅自补充）

以下既有配置项**尚未登记**本表（`INDEX.md` 中"规划位置"的触发时机已过），需后续单独补齐：

- ~~评分维度 / 权重（`DATA-010`，M005 契约轮）~~ → **后置 V2**（`ADR-014` 决议 2：M005 不属 V1，配置项随 V2 回归登记）
- ~~AI Provider（模型 / 密钥 / 限额 / 超时重试降级，`ADR-011`）~~ → **已登记，见第五节**（`Task-006` 交付回填；真实三方密钥就绪后同步登记 `EXTERNAL_SYSTEMS.md`）
- 已有实现但未登记项：`AT_DATABASE_URL`、`AT_FRONTEND_DIR`、认证会话 TTL、登录失败锁定、scrypt 参数、分页默认/上限（见 `backend/app/core/config.py`）

> 上列属于**本次修订范围之外**，需 Project Master 确认后另行登记。

## 五、AI 接入层配置（`Task-006` 落地登记，ADR-011）

> 归属：设置类 `AISettings`（前缀 **`AT_AI_`**，实现位置 `backend/app/core/ai/config.py`，独立于 `core/config.py`）。
> 原则：**无硬编码模型名 / 密钥 / 厂商地址**；密钥仅经部署侧环境变量注入，**禁止入库、禁止入日志**（`DATA-009` 敏感约束）。

| 配置项 | 环境变量 | 默认值 | 说明 |
| --- | --- | --- | --- |
| Provider 模式 | `AT_AI_PROVIDER_MODE` | `auto` | `real` / `mock` / `auto`；`auto` = 已配置密钥走真实三方，否则 Mock 降级 |
| 允许 Mock 降级 | `AT_AI_ALLOW_MOCK_FALLBACK` | `true` | 三方不可用/超时/输出不合规时是否降级为「不可用」信号（上游走手工兜底） |
| 请求超时 | `AT_AI_REQUEST_TIMEOUT_SECONDS` | `20` | 单次调用超时（秒） |
| 最大重试 | `AT_AI_MAX_RETRIES` | `2` | 可重试错误的重试次数 |
| 重试退避 | `AT_AI_RETRY_BACKOFF_SECONDS` | `0.5` | 指数退避基准（秒） |
| 最大 token | `AT_AI_MAX_TOKENS` | `1024` | LLM 输出上限 |
| 温度 | `AT_AI_TEMPERATURE` | `0.0` | 解析/判定类任务默认确定性输出 |
| Mock 时延 | `AT_AI_MOCK_LATENCY_MS` | `0` | Mock Provider 模拟时延（仅测试用） |
| LLM 模型 / 密钥 / 地址 | `AT_AI_LLM_MODEL`、`AT_AI_LLM_API_KEY`、`AT_AI_LLM_BASE_URL` | 空 | 三者齐备该类型才走真实三方 |
| Vision 模型 / 密钥 / 地址 | `AT_AI_VISION_MODEL`、`AT_AI_VISION_API_KEY`、`AT_AI_VISION_BASE_URL` | 空 | 同上 |
| OCR 模型 / 密钥 / 地址 | `AT_AI_OCR_MODEL`、`AT_AI_OCR_API_KEY`、`AT_AI_OCR_BASE_URL` | 空 | 同上（V1 三链路未强制依赖，预留） |

> 真实三方实现为 **OpenAI 兼容 Chat Completions** 协议；如最终选用其他厂商/SDK，仅调整 Provider 映射，**不改调用契约**（`Task-006` §6 遗留项）。
