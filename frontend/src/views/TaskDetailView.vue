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
          <!-- 重新解析（API-M001-022 / CR-005）：未确认任务可重跑链路 T；confirmed 隐藏 -->
          <van-button
            v-if="canReparse"
            plain
            type="primary"
            size="small"
            :loading="reparsing"
            :disabled="reparsing"
            @click="reparse"
          >
            重新解析
          </van-button>
          <span v-if="reparsing" class="muted small">AI 解析中，约 15–30 秒…</span>
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

      <!-- AI 未识别的作业照片（REQ-011 第一阶段：只读 + 单张重试；口径 = 该学生级，非本任务窗口） -->
      <div class="card">
        <h3 class="section-h">AI 未识别的照片（{{ pendingPhotos.length }}）</h3>
        <div class="muted small">
          该学生当前未能自动识别挂接目标的作业照片：可单张「重试建议」；采纳、手工挂接等完整处理请到「作业」页。
        </div>

        <van-loading v-if="photosLoading" class="photos-loading" size="18px">加载中…</van-loading>
        <div v-else-if="photosError" class="muted small">{{ photosError }}</div>
        <div v-else-if="!pendingPhotos.length" class="muted small">当前没有待 AI 识别的作业照片</div>

        <div v-for="p in pendingPhotos" :key="p.photo_id" class="photo-row">
          <img v-if="thumbs[p.photo_id]" :src="thumbs[p.photo_id]" class="thumb-img" alt="作业图" />
          <div v-else class="thumb-img thumb-placeholder">📷</div>
          <div class="photo-body">
            <div class="photo-title">
              第 {{ p.seq_no }} 张
              <span class="badge draft">{{ PHOTO_STATUS_TEXT[p.status] ?? p.status }}</span>
            </div>
            <div class="muted small">上传于 {{ formatTime(p.created_at) }}</div>
            <div class="muted small">
              质检
              <span :class="p.quality.passed ? 'ok-text' : 'warn-text'">
                {{ p.quality.passed ? "通过" : "存在问题" }}
              </span>
            </div>
            <div class="photo-actions">
              <van-button
                plain
                type="primary"
                size="small"
                :loading="retrying === p.photo_id"
                :disabled="Boolean(retrying)"
                @click="retrySuggestion(p)"
              >
                重试建议
              </van-button>
            </div>
          </div>
        </div>

        <div v-if="retrying" class="muted small">AI 分析中，约 15–30 秒，请稍候…</div>
        <div v-if="pendingPhotos.length >= 50" class="muted small">更多照片请到「作业」页处理</div>

        <div class="photos-foot">
          <van-button plain size="small" @click="router.push('/photos')">去「作业」页处理</van-button>
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
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { showConfirmDialog, showToast } from "vant";

import {
  changeTaskBelongDate,
  changeTaskStatus,
  fetchPhotoBlob,
  getLinkSuggestions,
  getTask,
  listPhotos,
  reparseTask,
} from "@/api";
import { toastError } from "@/api/http";
import type { Photo, TaskDetail } from "@/api/types";
import BottomNav from "@/components/BottomNav.vue";
import {
  PHOTO_STATUS_TEXT,
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

// ---- AI 未识别的照片（REQ-011 第一阶段：只读 + 单张重试）----
/** 该学生 `kind=homework` + `status=unassigned` 的照片（**学生级**口径 —— 未挂接照片无窗口归属，见 TD-005）。 */
const pendingPhotos = ref<Photo[]>([]);
const thumbs = ref<Record<string, string>>({});
const photosLoading = ref(false);
const photosError = ref("");
/** 正在重试的 photo_id（单张串行；非空时其余重试按钮禁用）。 */
const retrying = ref("");
/** 单请求超时覆盖：`retry=true` 同步等待真实模型（实测约 15.6s），全局 15s 必然超时（BUG-007）。 */
const RETRY_TIMEOUT_MS = 60000;

const canEdit = computed(() => task.value?.status === "draft" || task.value?.status === "published");

// ---- 重新解析（`API-M001-022` / `CR-005`）----
/** 未确认（`placeholder` / `parsed`）时可重跑链路 T；`confirmed` 须先取消确认（V1 无入口）→ 不显示。 */
const canReparse = computed(() => {
  const s = task.value?.spec_status;
  return s === "placeholder" || s === "parsed";
});
const reparsing = ref(false);
/** 单请求超时覆盖：真实 Vision 同步解析约 15s+，全局 15s 必然超时（同 `BUG-007` 模式，**不改** `http.ts`）。 */
const REPARSE_TIMEOUT_MS = 60000;

async function load(): Promise<void> {
  task.value = await getTask(props.id);
}

/** 重新解析：反馈以「解析后是否有内容项」为准 —— **无内容项不得谎报成功**。 */
async function reparse(): Promise<void> {
  const current = task.value;
  if (!current || reparsing.value) return;
  reparsing.value = true;
  try {
    const updated = await reparseTask(current.task_id, { timeoutMs: REPARSE_TIMEOUT_MS });
    task.value = updated;
    if (updated.spec_status === "parsed" && updated.contents.length > 0) {
      showToast(`已解析出 ${updated.contents.length} 项内容，请到「草稿确认」核对`);
    } else {
      showToast("AI 未返回解析结果（可能暂时不可用或图片无法识别），可稍后重试或手工补录");
    }
  } catch (err) {
    toastError(err);
    await load(); // 409（已确认）等 → 刷新最新状态
  } finally {
    reparsing.value = false;
  }
}

async function loadPendingPhotos(): Promise<void> {
  const studentId = task.value?.student_id;
  if (!studentId) return;
  photosLoading.value = true;
  photosError.value = "";
  try {
    const res = await listPhotos({
      student_id: studentId,
      kind: "homework",
      status: "unassigned",
      page: 1,
      page_size: 50,
    });
    const items = res.items ?? [];
    pendingPhotos.value = items;
    await loadThumbs(items);
  } catch (err) {
    photosError.value = err instanceof Error ? err.message : "照片加载失败";
  } finally {
    photosLoading.value = false;
  }
}

async function loadThumbs(items: Photo[]): Promise<void> {
  await Promise.all(
    items.map(async (p) => {
      if (thumbs.value[p.photo_id]) return;
      try {
        thumbs.value[p.photo_id] = await fetchPhotoBlob(p.photo_id, "normalized");
      } catch (_) {
        /* 取图失败不阻塞列表 */
      }
    })
  );
}

/** 单张重试 AI 挂接建议（`retry=true` 幂等；成败按 `suggestions` 是否为空区分，不谎报成功）。 */
async function retrySuggestion(p: Photo): Promise<void> {
  if (retrying.value) return;
  retrying.value = p.photo_id;
  try {
    const res = await getLinkSuggestions(p.photo_id, true, { timeoutMs: RETRY_TIMEOUT_MS });
    if (res.suggestions.length > 0) {
      showToast("已生成挂接建议，请到「作业」页采纳");
    } else {
      showToast("AI 未返回建议（可能暂时不可用），可稍后重试，或到「作业」页手工挂接");
    }
  } catch (err) {
    toastError(err);
  } finally {
    retrying.value = "";
    await loadPendingPhotos(); // 成功 → 该照片变 suggested，自动移出本列表
  }
}

onMounted(async () => {
  await load();
  await loadPendingPhotos();
});

onBeforeUnmount(() => {
  for (const url of Object.values(thumbs.value)) URL.revokeObjectURL(url);
  thumbs.value = {};
});

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
.photo-row {
  display: flex;
  gap: 12px;
  margin: 12px 0;
  padding-top: 10px;
  border-top: 1px solid var(--app-line);
}
.photo-body {
  flex: 1;
  min-width: 0;
}
.photo-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
}
.thumb-img {
  width: 72px;
  height: 96px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--app-line);
  flex: none;
  background: #f2f4f9;
}
.thumb-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}
.photo-actions {
  margin-top: 8px;
}
.photos-loading {
  padding: 12px 0;
  justify-content: center;
}
.photos-foot {
  margin-top: 12px;
}
.ok-text {
  color: var(--app-success);
}
.warn-text {
  color: #b07a12;
}
</style>
