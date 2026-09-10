import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

// ADR-012：Vite 5 工程。
// - dev：vite dev server，/api/v1 代理到本地 FastAPI（backend 由 uvicorn 提供）
// - prod：npm run build 产出 frontend/dist，由 FastAPI StaticFiles 托管
//
// 端口/代理目标可用环境变量覆盖（默认不变，兼容 README 标准用法）：
//   VITE_DEV_PORT            前端 dev 端口，默认 5173
//   VITE_API_PROXY_TARGET    /api 代理目标，默认 http://127.0.0.1:8000
const DEV_PORT = Number(process.env.VITE_DEV_PORT) || 5173;
const API_PROXY_TARGET = process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: DEV_PORT,
    proxy: {
      "/api": { target: API_PROXY_TARGET, changeOrigin: true },
    },
  },
  build: { outDir: "dist" },
});
