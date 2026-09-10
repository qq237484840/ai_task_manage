import { createRouter, createWebHashHistory } from "vue-router";

import { TOKEN_KEY } from "@/api/http";

// hash 模式路由（ADR-012：静态托管无需 history fallback，后端零改动）。
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/login", name: "login", component: () => import("@/views/LoginView.vue") },
    { path: "/tasks", name: "tasks", component: () => import("@/views/TaskListView.vue") },
    { path: "/tasks/new", name: "task-new", component: () => import("@/views/TaskEditorView.vue") },
    {
      path: "/tasks/:id",
      name: "task-detail",
      component: () => import("@/views/TaskDetailView.vue"),
      props: true,
    },
    {
      path: "/tasks/:id/edit",
      name: "task-edit",
      component: () => import("@/views/TaskEditorView.vue"),
      props: true,
    },
    // 作业域（M002）：路径保留 /photos（深链兼容），仅语义改名为「作业」。
    { path: "/photos", name: "homework", component: () => import("@/views/PhotoListView.vue") },
    {
      path: "/photos/upload",
      name: "homework-upload",
      component: () => import("@/views/PhotoUploadView.vue"),
    },
    { path: "/students", name: "students", component: () => import("@/views/StudentsView.vue") },
    { path: "/mine", name: "mine", component: () => import("@/views/MineView.vue") },
    { path: "/:pathMatch(.*)*", redirect: "/tasks" },
  ],
});

router.beforeEach((to) => {
  const authed = Boolean(localStorage.getItem(TOKEN_KEY));
  if (!authed && to.name !== "login") return { name: "login" };
  if (authed && to.name === "login") return { name: "tasks" };
  return true;
});

export default router;
