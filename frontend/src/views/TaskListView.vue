<template>
  <div class="page">
    <div class="page-topbar"><h1>作业任务</h1></div>

    <div class="card">
      <div class="filter-grid">
        <div>
          <span class="filter-label">状态</span>
          <select v-model="filters.status" class="native-select" @change="reload">
            <option value="">全部状态</option>
            <option v-for="o in STATUS_OPTS" :key="o.value" :value="o.value">{{ o.text }}</option>
          </select>
        </div>
        <div>
          <span class="filter-label">学生</span>
          <select v-model="filters.student_id" class="native-select" @change="reload">
            <option value="">全部学生</option>
            <option v-for="s in students" :key="s.student_id" :value="s.student_id">{{ s.name }}</option>
          </select>
        </div>
      </div>
    </div>

    <div v-if="!tasks.length && !loading" class="card empty">
      还没有任务，点右下角 + 上传今天的作业
    </div>

    <div v-for="t in tasks" :key="t.task_id" class="card">
      <div class="row clickable" @click="openDetail(t.task_id)">
        <div class="body">
          <div class="title">{{ t.title }}</div>
          <div class="sub">
            {{ t.student_name || studentsById[t.student_id] || "" }} · 归属 {{ t.belong_date }} ·
            {{ weekText(t.week_index) }} · {{ WINDOW_TYPE_TEXT[t.window_type] ?? t.window_type }}
          </div>
          <div class="sub">
            内容 {{ t.content_count ?? 0 }} 项 · 来源 {{ t.source_count ?? 0 }} 个 · 截止
            {{ formatTime(t.deadline) }}
          </div>
        </div>
        <div class="tags">
          <span class="badge" :class="t.status">{{ STATUS_TEXT[t.status] ?? t.status }}</span>
          <span class="chip" :class="t.spec_status">
            {{ SPEC_STATUS_TEXT[t.spec_status] ?? t.spec_status }}
          </span>
        </div>
      </div>
    </div>

    <button class="fab-new" aria-label="新建任务" @click="router.push('/tasks/new')">＋</button>
    <BottomNav active="tasks" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { listStudents, listTasks } from "@/api";
import { toastError } from "@/api/http";
import type { TaskStatus, TaskSummary } from "@/api/types";
import BottomNav from "@/components/BottomNav.vue";
import {
  SPEC_STATUS_TEXT,
  STATUS_TEXT,
  WINDOW_TYPE_TEXT,
  formatTime,
  weekText,
} from "@/utils/format";

const STATUS_OPTS = [
  { value: "draft", text: "草稿" },
  { value: "published", text: "已发布" },
  { value: "in_progress", text: "进行中" },
  { value: "closed", text: "已关闭" },
];

const router = useRouter();
const students = ref<{ student_id: string; name: string }[]>([]);
const tasks = ref<TaskSummary[]>([]);
const loading = ref(false);
const filters = ref<{ status: string; student_id: string }>({ status: "", student_id: "" });

const studentsById = computed(() =>
  Object.fromEntries(students.value.map((s) => [s.student_id, s.name]))
);

async function loadStudents(): Promise<void> {
  if (students.value.length) return;
  students.value = await listStudents();
}

async function loadTasks(): Promise<void> {
  loading.value = true;
  try {
    const data = await listTasks({
      page: 1,
      page_size: 100,
      status: filters.value.status ? (filters.value.status as TaskStatus) : undefined,
      student_id: filters.value.student_id || undefined,
    });
    tasks.value = data.items;
  } catch (err) {
    toastError(err);
  } finally {
    loading.value = false;
  }
}

async function reload(): Promise<void> {
  await loadTasks();
}

onMounted(async () => {
  await loadStudents();
  await loadTasks();
});

function openDetail(taskId: string): void {
  router.push(`/tasks/${taskId}`);
}
</script>

<style scoped>
.filter-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.filter-label {
  display: block;
  font-size: 13px;
  color: var(--app-muted);
  margin-bottom: 6px;
}
.row.clickable {
  cursor: pointer;
}
.tags {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-end;
}
.fab-new {
  position: fixed;
  right: 22px;
  bottom: 78px;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: none;
  background: #3b5bdb;
  color: #fff;
  font-size: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 18px rgba(59, 91, 219, 0.4);
  cursor: pointer;
  z-index: 10;
}
</style>
