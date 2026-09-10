<template>
  <div class="page">
    <div class="page-topbar">
      <van-button icon="arrow-left" plain size="small" @click="router.push('/tasks')">返回</van-button>
      <h1>任务详情</h1>
    </div>

    <van-loading v-if="!task" class="loading" size="24px">加载中…</van-loading>

    <template v-if="task">
      <div class="card">
        <div class="title-line">
          <h2>{{ task.title }}</h2>
          <span class="badge" :class="task.status">{{ STATUS_TEXT[task.status] }}</span>
        </div>
        <div class="muted meta">
          归属 {{ task.belong_date }} · {{ weekText(task.week_index) }} ·
          {{ WINDOW_TYPE_TEXT[task.window_type] ?? task.window_type }} · 年级
          {{ task.grade_level || "-" }} · 截止 {{ formatTime(task.deadline) }}
        </div>
        <div class="muted meta">
          输入源 {{ task.sources.length }} 个 · 内容项 {{ task.contents.length }} 项 ·
          {{ SPEC_STATUS_TEXT[task.spec_status] ?? task.spec_status }} · 更新
          {{ formatTime(task.updated_at || task.created_at) }}
        </div>

        <div class="actions">
          <van-button
            v-if="task.status === 'draft'"
            type="primary"
            size="small"
            @click="confirmAction('publish', '确定发布该任务？发布后即可开始上传。')"
          >
            发布任务
          </van-button>
          <van-button v-if="canEdit" plain size="small" @click="router.push(`/tasks/${task.task_id}/edit`)">
            {{ task.spec_status === "confirmed" ? "编辑" : "草稿确认" }}
          </van-button>
          <van-button plain size="small" @click="openBelongDate">改归属日</van-button>
          <van-button
            v-if="task.status === 'published' || task.status === 'in_progress'"
            plain
            type="warning"
            size="small"
            @click="confirmAction('close', '确定关闭该任务？关闭后不可再上传或修改。')"
          >
            关闭任务
          </van-button>
          <van-button
            v-if="task.status === 'closed'"
            plain
            type="primary"
            size="small"
            @click="confirmAction('reopen', '确定重新发布该任务？')"
          >
            重新发布
          </van-button>
        </div>
      </div>

      <div class="card">
        <h3 class="section-h">内容项（{{ task.contents.length }}）</h3>
        <div v-if="!task.contents.length" class="muted">暂无内容项（待解析或仅图片输入源）</div>
        <div v-for="(c, i) in task.contents" :key="c.content_id" class="item-card">
          <span class="chip">{{ subjectText(c.subject) }}</span>
          <div class="q">{{ i + 1 }}. {{ c.text }}</div>
        </div>
      </div>

      <div class="card">
        <h3 class="section-h">输入源（{{ task.sources.length }}）</h3>
        <div v-for="s in task.sources" :key="s.source_id" class="source-row">
          <span class="chip">{{ s.kind === "text" ? "文本" : "图片" }}</span>
          <span class="muted source-text">{{
            s.kind === "text" ? s.text_content : `照片 ${s.photo_id}`
          }}</span>
        </div>
      </div>

      <BottomNav active="tasks" />
    </template>

    <!-- 改归属日（幂等；跨聚合连锁迁移；已消费将被拒） -->
    <van-popup v-model:show="belongOpen" position="bottom" round>
      <div class="popup-inner">
        <h3>改归属日</h3>
        <div class="muted small">改归属日会把任务移入目标窗口的聚合；若目标窗口缺同学科聚合将被拒绝。</div>
        <input v-model="belongDraft" class="native-date" type="date" />
        <div class="action-gap"></div>
        <van-button round block type="primary" :loading="busy" @click="submitBelongDate">
          确认修改
        </van-button>
      </div>
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { showConfirmDialog, showToast } from "vant";

import { changeTaskBelongDate, changeTaskStatus, getTask } from "@/api";
import type { TaskDetail } from "@/api/types";
import BottomNav from "@/components/BottomNav.vue";
import {
  SPEC_STATUS_TEXT,
  STATUS_TEXT,
  WINDOW_TYPE_TEXT,
  formatTime,
  subjectText,
  weekText,
} from "@/utils/format";

const props = defineProps<{ id: string }>();
const router = useRouter();

const task = ref<TaskDetail | null>(null);
const belongOpen = ref(false);
const belongDraft = ref("");
const busy = ref(false);

const canEdit = computed(() => task.value?.status === "draft" || task.value?.status === "published");

async function load(): Promise<void> {
  task.value = await getTask(props.id);
}

onMounted(load);

async function confirmAction(action: "publish" | "close" | "reopen", message: string): Promise<void> {
  try {
    await showConfirmDialog({ title: "确认", message });
  } catch (_) {
    return; // 用户取消
  }
  try {
    const data = await changeTaskStatus(props.id, action);
    showToast("状态已更新：" + (STATUS_TEXT[data.status] ?? data.status));
    await load();
  } catch (err) {
    showToast(err instanceof Error ? err.message : "操作失败");
  }
}

async function openBelongDate(): Promise<void> {
  belongDraft.value = task.value?.belong_date ?? "";
  belongOpen.value = true;
}

async function submitBelongDate(): Promise<void> {
  const value = belongDraft.value.trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    showToast("请选择归属日期");
    return;
  }
  busy.value = true;
  try {
    const saved = await changeTaskBelongDate(props.id, value);
    showToast(`归属日已改为 ${saved.belong_date}`);
    belongOpen.value = false;
    await load();
  } catch (err) {
    showToast(err instanceof Error ? err.message : "改归属日失败");
  } finally {
    busy.value = false;
  }
}
</script>

<style scoped>
.loading {
  padding: 48px 0;
  justify-content: center;
}
.title-line {
  display: flex;
  align-items: center;
  gap: 8px;
}
.title-line h2 {
  font-size: 18px;
  margin: 0;
  flex: 1;
}
.meta {
  margin-top: 8px;
  font-size: 13px;
}
.section-h {
  font-size: 15px;
  margin: 0 0 8px;
}
.item-card {
  border: 1px solid var(--app-line);
  border-radius: 12px;
  padding: 12px;
  margin: 10px 0;
  background: #fff;
}
.item-card .q {
  font-size: 15px;
  margin: 6px 0 0;
}
.source-row {
  display: flex;
  gap: 8px;
  align-items: baseline;
  margin: 8px 0;
}
.source-text {
  font-size: 13px;
  word-break: break-all;
}
.popup-inner {
  padding: 18px;
}
.popup-inner h3 {
  margin: 0 0 6px;
  font-size: 16px;
}
.native-date {
  width: 100%;
  margin-top: 12px;
  padding: 10px;
  border: 1px solid var(--app-line);
  border-radius: 8px;
  font-size: 15px;
}
</style>
