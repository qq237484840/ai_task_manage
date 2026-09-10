# frontend —— AI 作业智能评定（Vue3 + Vite + TypeScript + Vant 4）

移动优先 H5 前端工程（ADR-012 / CHANGE-002 / Task-003）。M001（作业任务管理）页面已完成等价迁移；M002（作业照片采集与归属）基础 UI 已按本栈实现（上传/逐图质检/列表归属）；M003 起全部前端 UI 继续按本栈实现。

> 注：`src/main.ts` 已全局注册 Vant 4（`app.use(Vant)`），视图层直接使用 `van-*` 组件。

## 技术栈

- Vue 3 + Vite 5 + TypeScript（严格）
- Vant 4（移动组件库）+ Vue Router 4（**hash 模式**）+ Pinia
- axios：统一错误语义映射（400/401/403/404/409/413/415/422）；401 自动清会话回登录

## 目录

```
src/
  api/          axios 实例（http.ts）+ 契约 API 层（index.ts）+ DTO 类型（types.ts）
  stores/       Pinia 会话（token / loginName / subject：family | student）
  router/       hash 路由 + 登录守卫
  views/        登录（家长/学生/注册三 Tab）、任务列表/编辑/详情、学生档案、我的（子账号管理）、
                照片上传（PhotoUploadView：建批次→多图上传→逐图质检）、照片列表（PhotoListView：筛选/归属/采纳建议/驳回/删除）
  components/   BottomNav 等
  styles/       Vant 主题与移动响应式基线
  utils/        展示映射与时间换算
```

## 命令

前置：Node ≥ 20（本仓库实测 22.22.2）+ npm。

```bash
npm install          # 安装依赖（锁文件 package-lock.json 已入库）
npm run dev          # 开发：http://localhost:5173，/api 代理到 http://127.0.0.1:8000
npm run typecheck    # vue-tsc --noEmit 类型检查
npm run build        # 类型检查 + 产物构建 → frontend/dist
npm run preview      # 本地预览构建产物
```

## 生产托管

后端 FastAPI 通过 `StaticFiles` 托管 `frontend/dist`（`backend/app/core/config.py` 的
`frontend_dir`，可用环境变量覆盖），`GET /` 直出构建应用；单进程部署形态不变（ASM-010）。

`frontend/dist` 与 `node_modules/` 不入库（`.gitignore`）。

## 契约约束

REST API 是唯一契约面（`docs/modules/M*/MODULE_API.md`）；前端为纯表现层。禁止未经
CR/ACR 自行发明接口；DTO 类型定义须与契约字段保持一致。
