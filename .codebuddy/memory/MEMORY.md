# MEMORY —— 长期项目记忆

> 原则：`docs/` 为 Single Source of Truth。本文件只留**跨会话要点与指针**；执行流水/证据原文见 `.codebuddy/memory/YYYY-MM-DD.md`。

## 项目一句话

中小学生 AI 作业与学习成长综合评定系统 V1。**有效模块 = M001 + M002 + 横切 `app/core/ai/`**（M003~M007 Deferred，`ADR-014`）。形态：**FastAPI + SQLite 单体**（ADR-004）+ 移动优先 H5 **Vue3+Vite+TS+Vant4**（ADR-012，FastAPI 托管 `frontend/dist`）+ **两级主体** family/student（家庭级隔离）+ **判定 = 聚合子任务(学科)级**（ADR-013）+ **真实三方 AI 默认 / Mock 降级**（ADR-011）。方法学：**文档驱动 + 多 Agent 治理**（**ID 仅 PM 分配**）。

## 当前状态（截至 2026-09-14）

- **V1（域 A/B/C）验收通过**（2026-09-10）：构建 `EXIT=0` + 种子 `SEED_OK` + `GET /` 200 + 浏览器级 **18/18** + 全量 `pytest` **237/0/0/0**（`235 passed + 2 xpassed`）。`CHANGE-003` **Closed**（④ 判达成）；M001 v0.2.0 / M002 v0.4.1 契约 **Frozen Stable**；基线入库推送链 = `aed4db1→ce5057c→b3bc0b3→ad7455c`。
- **缺陷台账**：`BUG-001`~`BUG-004` 均 **Verified** ｜ **`BUG-005` / `BUG-006` = `Fixed`（2026-09-14，`Task-015`/`Task-016` 修复；由 **PM 代执行** —— 本机无具备写权限的执行 subagent，不构成独立第三方复核，限制已标注任务书 §5）**：全量回归 **251/0/0/0** + 双**红→绿**（`BUG-006` 含 **API 面**：禁兜底→`placeholder`，回退→`parsed` 复现）+ 写区双证 + `read_lints=0` ｜ **`BUG-007` = `Fixed`（2026-09-14，`Task-017`；含 §3.3b 最小扩权使作业页同一超时路径闭环）**。
- **技术债**：`TD-001`（`get_group_subject` N+1）、`TD-002`（契约未暴露 `window_task_id`/`task_status`）待排期；`TD-003` Closed；PM 裁决不立 `TD-004`。**无阻塞项**。
- **任务队列**：`Task-006`~`Task-017` 均已完成（`Task-015`/`Task-016`/`Task-017` 于 2026-09-14 当日签发 + 收口），**无 Active**。**`REQ-011` 第一阶段（A2）已交付**（任务详情「AI 未识别的照片」只读卡 + 单张重试；`BUG-007` → `Fixed`）。下一步候选 = **`REQ-011` 第二阶段 A1（布置单图片解析，需 CR/ACR）**、`TD-005`、CR 候选（失败原因可见 / `API-M002-007` 异步化）、`TD-001`/`TD-002`，或 **V2 域 D（M005~M007，`RISK-012`）**。

## 真实三方 AI 联调（2026-09-14，PM 执行）

- **密钥源**：IDE `~/.codebuddy/models.json`（OpenAI 兼容中转）。**规范做法 = 临时脚本读取后写入 `backend/.env`（已 gitignore，勿提交），密钥不落对话/仓库**。当前（用户第二次更新 models.json 后）：`https://www.hhhana.lol/v1`，LLM `glm-5.3` / Vision·OCR `qwen3.8-flash`（`deepseek-v4-pro` 不支持 `json_object`，已排除），`AT_AI_PROVIDER_MODE=real` + `AT_AI_ALLOW_MOCK_FALLBACK=false`。
- **成果**：real 通路**真实出网并成功** —— DATA-009 记录 `provider=openai_compatible / mock=0`；完整业务 prompt（569 字符 + `response_format=json_object`）→ **HTTP 200 + 合规 JSON**。
- **端到端真实验收已通过（2026-09-14 复验，用户确认此前为「接口限流」）**：① M001 `POST /tasks → 201/spec_status=parsed`，DATA-009 `task_spec_parse / glm-5.3 / mock=0 / status=ok`；② M002 上传含真实文字作业图 → `201`、照片 `status=suggested`、`links=[{subject:'math', source:'ai', confidence:1.0}]`，DATA-009 `photo_link_suggest / qwen3.8-flash / mock=0 / status=ok / 15.6s` → **真实 LLM + Vision 全链路打通并产出正确业务结果**。**中转可用性仍间或波动**（捕获 1 条 ~20s 超时 `status=error`，重试成功）→ 须保留重试容错；该波动正是 `BUG-006` 的现实触发条件。**复验要点：查 DATA-009 `mock=0 & status=ok`，勿只看 UI 的 `spec_status`**。
- **派生缺陷（已立项）**：
  - **`BUG-005`（中）**：三方 **403「余额/配额不足」被 `core/ai/errors.py:67-68` `from_http_status` 误映射为 `auth_error`「三方鉴权失败」**，且 401/403/429/5xx 分支**丢弃响应体** → DATA-009 留痕失真、排障方向被误导（本次排障多轮才定位到「配额」而非「鉴权」）。建议：新增 `AIErrorCode.QUOTA_EXHAUSTED`（**不可重试**）+ 三方响应摘要**脱敏截断**（剔 `sk-`、≤200 字）入 `message`。
  - **`BUG-006`（高）**：`m001/services/task_parser.py:198-207` `default_parser` 在 AI 抛错/产物不合规后**无条件**回落 `mock_parse_sources`，**全程不读 `allow_mock_fallback`** → 在 real+禁兜底配置下 `POST /tasks` 仍返回 `201 / spec_status="parsed"`，而同期 DATA-009 为 `mock=0 / status=error` —— **「假成功」且 UI 无降级信号**。对照：M002 侧同配置行为正确（照片保持 `unassigned`、`links=[]`）→ 缺陷边界仅在 M001。**修复不得新增表字段/改契约**（推荐仅按配置语义返回 `None` → 保持 `placeholder`）。
- **测试隔离铁律（重要）**：`Settings`/`AISettings`/`M002Settings` 均 `env_file=".env"` → **部署侧 `.env` 会污染回归**（实测 8 例失败：7 例 AI + `test_quality_rejects_page_crop`）。已由 `backend/tests/conftest.py` autouse fixture **`isolate_deploy_config`** 关闭 `env_file` + 清空 `AT_AI_*` 凭据 + 清 `get_ai_settings`/`get_ai_service`/`get_m002_settings` 三缓存 → 全量 **EXIT=0、基线 237 不减**。**改 `.env` 后必须重跑全量回归**。

## 架构定稿要点（ADR-013）

- **双层模型**：事实层按天（`tasks` 唯一键 `(student_id, category, belong_date)`）+ 聚合层跨天（`task_groups` → `task_group_subjects` ★判定单元 → `photo_subject_links` N:N → `completion_analyses`）；**挂接与判定落聚合层**。
- **窗口语义**：日界**凌晨 4 点**（`AT_DAY_CUTOFF`，Asia/Shanghai）；`week_index` 自 `AT_TERM_START` 周一起算；**周五~周日合并周末作业**；每个 `belong_date` 至少一个聚合。
- **配置锁定**：写入触发锁定、纯浏览不锁；已聚合按生成时 `policy_version`；`belong_date` 上传即固化。
- **输入源**：图片 / 文本 / 聊天记录（**仅支持粘贴文本**）；`kind` 由菜单入口决定（「任务」→ `task_spec`，「作业」→ `homework`）。
- **分层约束**：M001 **禁止 import M002**；跨模块唯一通道 = 回调注册（`register_links_migration_hook` + `main.py` 启动期幂等自愈）。

## 用户偏好与 PM 铁律

- 中文文档、英文标识符；README 只做入口；模块九件套按真实需要生成、**禁空模板**；后端改动须**同步回填 docs 与测试**。
- 需求详情入 `docs/requirements/`；变更先 **CR/ACR** 登记；普通增量记 `CHANGELOG.md`；**禁止知识重复**；治理模板包改进须回同步并递增版本；一次 `ask_followup` ≤4 题且选项带推荐标注。
- **复核铁律**：不采信自述 —— 须**可复现命令 + 原文输出**；「零改动」须 `git diff` + **mtime** 双证；证据**逐域标注**（构建/API/服务/浏览器级不得混同）；**症状在哪一层，证据就必须到哪一层**。
- **测试铁律**：替身/桩须在 docstring 标注并向 PM 报备；`xfail` **不得删除或放宽**，修复后须自然 **XPASS**（PM 亲手红→绿）；改 AI 配置或重跑必须 **`cache_clear()` 双 `lru_cache`**（历史踩坑：`BUG-004` 归因「并发抖动」实为缓存泄漏）；跨模块消费链至少一条真机集成用例；契约外接口不得作为唯一来源。
- **修复类禁止** `try/except TypeError` 兼容旧签名（`BUG-004` 教训）；DoD × 写区冲突时先读码核实物理可行性 → 证据可经真实生产路径取得则**最小扩权**（写入任务书并附硬约束）。

## 关键索引

- 入口 `docs/INDEX.md`；状态 `docs/PROJECT_STATUS.md`；主线 `docs/ROADMAP.md`；需求 `docs/requirements/CLARIFICATION-2026-09-10.md`；配置 `docs/CONFIGURATION.md`（`docs` 侧尚未登记 `AT_M002_QUALITY_*`）；数据 `docs/DATA_MODEL.md`（DATA-009 = 物理表 `ai_call_records`）。
- ADR `docs/adr/ADR-001~014`（关键 = 011/012/013/014）｜模块 `MODULE_REGISTRY.md`｜API `API_REGISTRY.md`｜变更 `docs/changes/`（`CHANGE-001` Applied、`002` Executing、`003` **Closed**、`CR-004` Applied、`BUG-001`~`004` Verified、**`BUG-005`/`BUG-006` Confirmed**）｜任务书 `docs/agents/Task-00x.md`｜技术债 `docs/TECH_DEBT.md`。

## 环境与实况备忘

- **venv** = `backend/.venv`（Python 3.12）；**pytest 基线 = 251**（2026-09-14 起；此前 237 —— `Task-015` +9 例、`Task-016` +5 例）；端口统一 **8010**（8000 被 `wslrelay.exe` 常占）。
- **一键启动脚本**（2026-09-11；双击用根目录 `start_server.bat`）：`start_server.ps1` 自动清理同端口旧 uvicorn（**只杀命令行含 `uvicorn`+`app.main` 的 python，绝不误杀其它进程**）+ 强制 venv + 设 `AT_DATABASE_URL`/`AT_FRONTEND_DIR` + 单实例 + 健康自检；日志 `at_server*.log`（已忽略）。参数 `[-Port][-Db acceptance|app][-Seed][-Reload][-Stop]`。**背景**：曾因「系统 Python + venv 双 `--reload` 抢 8010」表現为「内部服务器报错」。※ 本机 shell 对复杂 PS 命令偶发路由到 cmd 报错，执行脚本宜用 `powershell -NoProfile -ExecutionPolicy Bypass -File <abs>`（`start_server.ps1` 输出全英文以回避 PS5.1 中文乱码）。
- **演示质检放宽**（2026-09-14）：`backend/.env` 设 `AT_M002_QUALITY_TILT_SEVERITY=warn` + `AT_M002_QUALITY_PAGE_CROP_ENABLED=false`（**仅**降级 `tilt`/`page_crop` 两条近似启发式；`blur`/亮度/遮挡照常 reject，实测模糊图仍 422）。**改动须重启**（`lru_cache`）；恢复严格 = 删/注释该两行后重启。质检实现 `m002/services/quality.py`、阈值 `m002/config.py`（`AT_M002_` 前缀）、抛错 `upload_service.py:155-160`（422 `image_quality_rejected`，message 含 `{id}(value=…)` 逐项原因，不合格不入库）。
- **浏览器级验收**（`.e2e/`，18/18）：① `& backend/.venv/Scripts/python.exe .e2e/seed.py`（**先删库重建** `backend/data/acceptance.db`）→ ② venv uvicorn 8010（带 `AT_DATABASE_URL`/`AT_FRONTEND_DIR`）→ ③ **node 不在 PATH**，须加 `C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2-2`（带 `-2` 后缀），再 `node .e2e/acceptance.mjs` → `total=18 pass=18`。跑一次会重写 `shots/` + `browser_evidence.json`（已入库 → 产生 `M`）。
- **前端类型检查必须显式指定工程**：`npx vue-tsc --noEmit -p tsconfig.app.json; "EXIT=$LASTEXITCODE"`（根 `tsconfig.json` 会漏检 `src/**`；PowerShell 管道吞退出码）。
- **git push 须绕开失效代理**：仓库 config 写死 `127.0.0.1:1080` 且该端口无监听 → **不得改 git config**，改用 `git -c http.proxy= -c https.proxy= push origin main`（PowerShell 会把 git stderr 包成 error record，**看退出码 0 即成功**）。
- `.gitignore` 已忽略：`.e2e/node_modules/`、`.e2e/*.xml`、`.e2e/seed_state.json`、`at_server*.log`、`backend/.env`；**故意保留** `.e2e/shots/*.png` + `.e2e/browser_evidence.json` 作为浏览器级证据。
- `tzdata>=2024.1` 已入 `backend/requirements.txt`；Vant 4 全局注册（`src/main.ts`）。
- 历史批次明细（v0.9.0~v0.20.0 各轮 PM 裁决与证据原文）见 `.codebuddy/memory/2026-09-08.md`、`2026-09-10.md`。
