<template>
  <div class="card photo-card">
    <div class="photo-head">
      <img
        v-if="thumb"
        :src="thumb"
        class="thumb-img"
        alt="作业图"
        @click="$emit('preview')"
      />
      <div v-else class="thumb-img thumb-placeholder" @click="$emit('preview')">📷</div>
      <div class="body">
        <div class="title">
          第 {{ photo.seq_no }} 张
          <span class="badge" :class="statusClass">{{ PHOTO_STATUS_TEXT[photo.status] ?? photo.status }}</span>
        </div>
        <div class="sub">{{ studentName }} · 上传于 {{ formatTime(photo.created_at) }}</div>
        <div class="sub">
          质检
          <span :class="photo.quality.passed ? 'ok-text' : 'warn-text'">
            {{ photo.quality.passed ? "通过" : "存在问题" }}
          </span>
          （{{ photo.quality.ruleset_version }}）
        </div>
      </div>
    </div>

    <!-- 已确认挂接（N:N，可跨学科；逐条可改挂） -->
    <div v-if="confirmed.length" class="assign-line">
      <div v-for="l in confirmed" :key="l.link_id" class="link-row">
        <span class="link-text">已挂接：{{ linkText(l) }}</span>
        <van-button size="mini" plain type="primary" @click="$emit('assign', photo, l)">改挂</van-button>
      </div>
    </div>

    <!-- 待复核 AI 建议 -->
    <div v-if="suggestionText" class="suggest-line">AI 建议：{{ suggestionText }}</div>

    <div class="actions">
      <template v-if="hasSuggestion">
        <van-button type="primary" size="small" :loading="busy" @click="$emit('accept', photo)">
          采纳建议
        </van-button>
        <van-button plain type="warning" size="small" :loading="busy" @click="$emit('reject', photo)">
          驳回建议
        </van-button>
      </template>
      <van-button plain type="primary" size="small" :loading="busy" @click="$emit('assign', photo)">
        {{ assignLabel }}
      </van-button>
      <van-button plain size="small" :loading="busy" @click="$emit('retry', photo)">重试建议</van-button>
      <van-button plain size="small" @click="$emit('preview')">查看</van-button>
      <van-button plain type="danger" size="small" :loading="busy" @click="$emit('remove', photo)">
        删除
      </van-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { Photo, PhotoLink } from "@/api/types";
import { PHOTO_STATUS_TEXT, formatTime } from "@/utils/format";

const props = defineProps<{
  photo: Photo;
  thumb?: string;
  studentName: string;
  /** group_subject_id → 学科显示名（供挂接目标文案）。 */
  subjectNames: Record<string, string>;
  /** group_subject_id → 窗口显示名（「第 N 周」/「周末作业」）。 */
  groupNames: Record<string, string>;
  busy: boolean;
}>();

defineEmits<{
  (e: "preview"): void;
  (e: "remove", photo: Photo): void;
  (e: "accept", photo: Photo): void;
  (e: "reject", photo: Photo): void;
  (e: "assign", photo: Photo, link?: PhotoLink): void;
  (e: "retry", photo: Photo): void;
}>();

const active = computed(() => props.photo.links.filter((l) => !l.rejected_at));
const confirmed = computed(() => active.value.filter((l) => l.confirmed_at));
const suggestion = computed(() =>
  active.value.find((l) => !l.confirmed_at && l.source === "ai")
);
const hasSuggestion = computed(() => Boolean(suggestion.value));

const statusClass = computed(() => {
  switch (props.photo.status) {
    case "assigned":
      return "in_progress";
    case "rejected":
      return "closed";
    case "suggested":
      return "published";
    default:
      return "draft";
  }
});

const assignLabel = computed(() => (confirmed.value.length ? "追加挂接" : "挂接到…"));

const suggestionText = computed(() => {
  const s = suggestion.value;
  if (!s) return "";
  const conf = s.confidence != null ? ` · 置信 ${Math.round(s.confidence * 100)}%` : "";
  return `${linkText(s)}${conf}`;
});

function linkText(link: PhotoLink): string {
  const subject = props.subjectNames[link.group_subject_id] ?? link.subject ?? "";
  const group = props.groupNames[link.group_subject_id] ?? "";
  const base = subject || "未知目标";
  return group ? `${base} · ${group}` : base;
}
</script>

<style scoped>
.photo-head {
  display: flex;
  gap: 12px;
}
.photo-head .body {
  flex: 1;
  min-width: 0;
}
.thumb-img {
  width: 72px;
  height: 96px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--app-line);
  flex: none;
  cursor: pointer;
  background: #f2f4f9;
}
.thumb-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}
.ok-text {
  color: var(--app-success);
}
.warn-text {
  color: #b07a12;
}
.assign-line {
  margin-top: 10px;
  background: #eef2ff;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 13px;
  color: #3b5bdb;
}
.link-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 2px 0;
}
.link-text {
  flex: 1;
  min-width: 0;
}
.suggest-line {
  margin-top: 10px;
  background: #fff8ec;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 13px;
  color: #b07a12;
}
.actions {
  margin-top: 6px;
}
</style>
