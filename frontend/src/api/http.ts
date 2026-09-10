import axios, { AxiosError } from "axios";
import { showToast } from "vant";

// axios 统一实例（ADR-012）：错误语义与 API 契约对齐
// （400/401/403/404/409/413/415/422 → 后端 ErrorResponse {code,message}）。
export const TOKEN_KEY = "at_token";
export const LOGIN_KEY = "at_login";
export const SUBJECT_KEY = "at_subject"; // family | student（ADR-009 两级主体）

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(LOGIN_KEY);
  localStorage.removeItem(SUBJECT_KEY);
}

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(message: string, status: number, code = "") {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export const http = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
});

/**
 * 剔除 query 中的空值（""/null/undefined）。
 * 后端枚举型 query 参数（如任务列表 status）不接受空串，`?status=` 会触发 422；
 * 统一在拦截器清洗，列表页"全部状态/全部学生"等空筛选无需各自处理。
 */
function stripEmptyParams(params: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== "" && v !== null && v !== undefined)
  );
}

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (config.params && typeof config.params === "object" && !(config.params instanceof URLSearchParams)) {
    config.params = stripEmptyParams(config.params as Record<string, unknown>);
  }
  return config;
});

function extractDetail(payload: unknown): { message: string; code: string } {
  if (payload && typeof payload === "object") {
    const p = payload as { message?: unknown; code?: unknown };
    return {
      message: typeof p.message === "string" ? p.message : "",
      code: typeof p.code === "string" ? p.code : "",
    };
  }
  return { message: "", code: "" };
}

http.interceptors.response.use(
  (res) => res.data,
  (error: AxiosError) => {
    const status = error.response?.status ?? 0;
    const { message, code } = extractDetail(error.response?.data);
    // 401 且携带 auth header（非登录/注册请求）：清除会话回登录页
    const authRequest = !!error.config?.headers?.Authorization;
    if (status === 401 && authRequest) {
      clearSession();
      if (!location.hash.startsWith("#/login")) location.hash = "#/login";
    }
    const text =
      message ||
      (status >= 400 && status < 500
        ? `请求失败(${status})`
        : "网络异常，请检查后端服务是否已启动");
    return Promise.reject(new ApiError(text, status, code));
  }
);

export function toastError(err: unknown): void {
  if (err instanceof ApiError) showToast(err.message);
  else if (err instanceof Error) showToast(err.message);
  else showToast("操作失败");
}
