<template>
  <div class="page">
    <div class="page-topbar">
      <van-button icon="arrow-left" plain size="small" @click="goBack">返回</van-button>
      <h1>上传作业</h1>
    </div>

    <!-- ① 目标学生（家长代传必选；学生本人无需选） -->
    <div class="card">
      <span class="field-label">上传给谁</span>
      <template v-if="session.isFamily">
        <select v-model="studentId" class="native-select" :disabled="!!batch">
          <option value="">请选择学生</option>
          <option v-for="s in students" :key="s.student_id" :value="s.student_id">{{ s.name }}</option>
        </select>
      </template>
      <div v-else class="muted small">学生模式：上传将归入本人待处理照片。</div>
    </div>

    <!-- ② 创建/重置批次 -->
    <div class="card">
      <div class="row" style="border: none">
        <div class="body">
          <div class="title">{{ batch ? "本批次已就绪" : "创建上传批次" }}</div>
          <div class="sub">
            {{
              batch
                ? `批次 ${short(batch.batch_id)} · 可连续上传多张，每张即时质检`
                : session.isFamily
                  ? "先为学生开启一次上传会话"
                  : "开启本次上传会话"
            }}
          </div>
        </div>
        <van-button
          v-if="!batch"
          type="primary"
          size="small"
          :loading="creating"
          :disabled="session.isFamily && !studentId"
          @click="startBatch"
        >
          开始上传
        </van-button>
        <van-button v-else plain type="warning" size="small" @click="resetBatch">换个批次</van-button>
      </div>
    </div>

    <!-- ③ 选图上传 -->
    <div class="card" v-if="batch">
      <span class="field-label">选择作业照片（支持一次多张，将逐张上传并质检）</span>
      <van-uploader
        v-model="fileList"
        multiple
        :max-count="30"
        :disabled="uploading || fileList.length >= 30"
        accept="image/*"
        :after-read="onAfterRead"
      >
        <van-button icon="photograph" type="primary" plain :disabled="uploading" size="small">
          {{ uploading ? "上传中…" : "添加照片" }}
        </van-button>
      </van-uploader>
      <div class="muted tiny note">
        支持 JPG/PNG/WebP，单张 ≤10MB；不清晰 / 过暗过亮 / 倾斜 / 遮挡 / 页角裁切等会被质检拒绝并提示原因。
        上传不填写任何内容；完成后在「作业」列表逐张复核挂接。
      </div>
    </div>

    <!-- ④ 逐图质检结果 -->
    <template v-if="results.length">
      <h2 class="section-title">质检与上传结果（逐图）</h2>
      <div v-for="r in results" :key="r.key" class="card result-card">
        <div class="row" style="border: none">
          <div class="thumb" :class="{ fail: r.status === 'error' }">{{ r.status === "ok" ? "✓" : "✗" }}</div>
          <div class="body">
            <div class="title">
              {{ r.fileName }}
              <span class="badge" :class="badgeClass(r)">{{ r.status === "ok" ? "已入库" : r.status === "error" ? "未入库" : "处理中" }}</span>
            </div>
            <div v-if="r.status === 'ok' && r.data" class="sub">
              第 {{ r.data.seq_no }} 张 · 质检 {{ r.data.quality.passed ? "通过" : "未通过" }}（{{ r.data.quality.ruleset_version }}）
            </div>
            <div v-else-if="r.status === 'error'" class="sub err-msg">{{ r.message }}</div>
            <div v-else class="sub muted">上传并质检中…</div>
          </div>
        </div>
        <div v-if="r.status === 'error' && r.code === 'image_quality_rejected'" class="qa-detail">
          <div v-for="c in r.checks" :key="c.id" class="qa-item" :class="c.passed ? 'pass' : 'fail'">
            <span class="qa-name">{{ checkText(c.id) }}</span>
            <span>{{ c.passed ? "通过" : qualitySeverityText(c.severity) }}</span>
            <span v-if="!c.passed && c.value != null" class="muted tiny">
              （{{ fmtVal(c.value) }}{{ c.threshold != null ? ` / 阈值 ${fmtVal(c.threshold)}` : "" }}）
            </span>
          </div>
        </div>
      </div>
    </template>

    <div v-if="batch && !uploading" class="card actions-card">
      <van-button
        round
        block
        type="primary"
        :disabled="!results.some((r) => r.status === 'ok')"
        @click="router.push('/photos')"
      >
        完成上传，去复核挂接
      </van-button>
    </div>

    <div class="action-gap"></div>
    <BottomNav active="photos" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { showToast, type UploaderFileListItem } from "vant";

import { createUploadBatch, listStudents, uploadPhoto } from "@/api";
import { ApiError, toastError } from "@/api/http";
import type { QualityReport, Student, UploadBatch } from "@/api/types";
import BottomNav from "@/components/BottomNav.vue";
import { qualitySeverityText } from "@/utils/format";
import { useSessionStore } from "@/stores/session";

const router = useRouter();
const session = useSessionStore();

const students = ref<Student[]>([]);
const studentId = ref("");
const batch = ref<UploadBatch | null>(null);
const creating = ref(false);
const uploading = ref(false);
const fileList = ref<UploaderFileListItem[]>([]);

interface UploadResult {
  key: string;
  fileName: string;
  status: "uploading" | "ok" | "error";
  code?: string;
  message?: string;
  checks?: QualityReport["checks"];
  data?: { seq_no: number; quality: QualityReport };
}

const results = ref<UploadResult[]>([]);

const isStudent = computed(() => !session.isFamily);

onMounted(async () => {
  if (session.isFamily) {
    try {
      students.value = await listStudents();
    } catch (err) {
      toastError(err);
    }
  }
  // 学生模式：直接进入可上传状态（自动建批次）
  if (isStudent.value) await startBatch();
});

function goBack(): void {
  router.push("/photos");
}

function short(uuid: string): string {
  return uuid.slice(0, 8);
}

async function startBatch(): Promise<void> {
  creating.value = true;
  try {
    // 「作业」入口显式传 kind=homework（B1/B2），上传不填任何内容。
    batch.value = await createUploadBatch(
      session.isFamily && studentId.value ? studentId.value : undefined,
      "homework"
    );
    showToast("批次已创建，可以上传了");
  } catch (err) {
    toastError(err);
  } finally {
    creating.value = false;
  }
}

function resetBatch(): void {
  batch.value = null;
  fileList.value = [];
  results.value = [];
}

async function onAfterRead(
  item: UploaderFileListItem | UploaderFileListItem[]
): Promise<void> {
  const list = Array.isArray(item) ? item : [item];
  for (const one of list) {
    await uploadOne(one);
  }
}

async function uploadOne(item: UploaderFileListItem): Promise<void> {
  if (!batch.value) return;
  const file = item.file;
  if (!file) return;
  const rec: UploadResult = {
    key: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    fileName: file.name || "作业照片",
    status: "uploading",
  };
  results.value.push(rec);
  uploading.value = true;
  try {
    const data = await uploadPhoto(batch.value.batch_id, file);
    rec.status = "ok";
    rec.data = { seq_no: data.seq_no, quality: data.quality };
    showToast(`第 ${data.seq_no} 张已入库`);
  } catch (err) {
    rec.status = "error";
    if (err instanceof ApiError) {
      rec.code = err.code;
      rec.message = err.message;
      // 质检拒绝：后端 message 携带逐项原因（明细行已在 message 展示）
      if (err.code === "image_quality_rejected") rec.checks = parseChecks(err.message);
    } else {
      rec.message = err instanceof Error ? err.message : "上传失败";
    }
    // 未入库的照片从本地选择列表移除，便于修正后重新选择
    const idx = fileList.value.findIndex((it) => it.file === file);
    if (idx >= 0) fileList.value.splice(idx, 1);
  } finally {
    uploading.value = false;
  }
}

function parseChecks(_msg: string): QualityReport["checks"] {
  // 质检拒绝原因已随 message 逐项返回，明细尽力从服务端报告解析；
  // 未解析到时返回空数组，仅展示 message 文案。
  return [];
}

const CHECK_TEXT: Record<string, string> = {
  too_blurry: "清晰度",
  too_dark: "亮度(过暗)",
  too_bright: "亮度(过亮)",
  skew: "方向(倾斜)",
  occluded: "遮挡",
  page_cropped: "页角裁切",
  too_small: "像素过小",
  unsupported: "格式/内容",
};

function checkText(id: string): string {
  return CHECK_TEXT[id] ?? id;
}

function fmtVal(v: number): string {
  return v >= 100 ? String(Math.round(v)) : v.toFixed(2);
}

function badgeClass(r: UploadResult): string {
  if (r.status === "ok") return "badge-ok";
  if (r.status === "error") return "badge-fail";
  return "";
}
</script>

<style scoped>
.small {
  font-size: 13px;
  line-height: 1.7;
}
.note {
  margin-top: 8px;
}
.thumb {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #e5efe9;
  color: var(--app-success);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex: none;
}
.thumb.fail {
  background: #fdeaea;
  color: var(--app-danger);
}
.err-msg {
  color: var(--app-danger);
}
.result-card {
  padding: 10px 14px;
}
.qa-detail {
  border-top: 1px dashed var(--app-line);
  margin-top: 8px;
  padding-top: 8px;
}
.qa-item {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 13px;
  padding: 2px 0;
}
.qa-item.pass {
  color: var(--app-success);
}
.qa-item.fail {
  color: var(--app-danger);
}
.qa-name {
  width: 90px;
  flex: none;
}
.actions-card {
  text-align: center;
}
.badge-ok {
  background: #e5efe9 !important;
  color: var(--app-success) !important;
}
.badge-fail {
  background: #fdeaea !important;
  color: var(--app-danger) !important;
}
</style>
