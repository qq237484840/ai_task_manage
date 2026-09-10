import { defineStore } from "pinia";

import {
  clearSession,
  LOGIN_KEY,
  SUBJECT_KEY,
  TOKEN_KEY,
} from "@/api/http";
import { familyLogout, studentLogout, type SubjectKind } from "@/api/index";

// 会话 store（ADR-012：Pinia 承载会话/主体上下文；ADR-009 两级主体）。
// 令牌/登录名/主体类型持久于 localStorage，store 为响应式镜像。
export const useSessionStore = defineStore("session", {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) ?? "",
    loginName: localStorage.getItem(LOGIN_KEY) ?? "",
    subject: (localStorage.getItem(SUBJECT_KEY) ?? "family") as SubjectKind,
  }),
  getters: {
    isAuthed: (s) => Boolean(s.token),
    isFamily: (s) => s.subject !== "student",
  },
  actions: {
    setAuth(token: string, loginName: string, subject: SubjectKind = "family") {
      this.token = token;
      this.loginName = loginName;
      this.subject = subject;
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(LOGIN_KEY, loginName);
      localStorage.setItem(SUBJECT_KEY, subject);
    },
    async logout() {
      try {
        if (this.subject === "student") await studentLogout();
        else await familyLogout();
      } catch (_) {
        /* 忽略登出接口异常，本地会话照常清除 */
      }
      this.token = "";
      this.loginName = "";
      this.subject = "family";
      clearSession();
    },
  },
});
