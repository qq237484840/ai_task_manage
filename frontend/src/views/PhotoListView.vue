<template>
  <div class="page">
    <div class="page-topbar">
      <h1>作业</h1>
      <van-button
        type="primary"
        plain
        size="small"
        icon="photograph"
        @click="router.push('/photos/upload')"
      >
        上传
      </van-button>
    </div>

    <!-- 筛选 -->
    <div class="card filter-card">
      <div class="filter-row">
        <span class="field-label">学生</span>
        <select v-if="session.isFamily" v-model="filters.student_id" class="native-select" @change="reload">
          <option value="">全部学生</option>
          <option v-for="s in students" :key="s.student_id" :value="s.student_id">{{ s.name }}</option>
        </select>
        <div v-else class="muted small">学生模式：仅本人作业</div>
      </div>
      <div class="status-tabs">
        <button
          v-for="tab in TABS"
          :key="tab.value"
          class="status-chip"
          :class="{ on: filters.status === tab.value }"
          @click="switchTab(tab.value)"
        >
          {{ tab.text }}
        </button>
      </div>
    </div>

    <van-loading v-if="loading" class="loading" size="24px">加载中…</van-loading>

    <div v-else-if="!photos.length" class="card empty">
      还没有作业。点右上角「上传」开始拍摄 / 选择作业照片。
    </div>

    <template v-else>
      <!-- 待挂接（无有效挂接：AI 未识别 / 建议已驳回；手工挂接兜底 B6） -->
      <template v-if="unlinkedPhotos.length">
        <h2 class="section-title">
          待挂接 <span class="chip">{{ unlinkedPhotos.length }} 张</span>
        </h2>
        <div class="section-sub muted">无有效挂接（AI 未识别 / 建议已驳回），可手工挂接</div>
        <PhotoCard
          v-for="p in unlinkedPhotos"
          :key="p.photo_id"
          :photo="p"
          :thumb="thumbs[p.photo_id]"
          :student-name="studentName(p.student_id)"
          :subject-names="subjectNames"
          :group-names="groupNames"
          :busy="busy"
          @preview="preview(p)"
          @remove="removePhoto"
          @accept="acceptSuggestion"
          @reject="rejectSuggestion"
          @assign="openPicker"
          @retry="retrySuggestion"
        />
      </template>

      <!-- 周次 / 窗口（含周末聚合）分组 -->
      <template v-for="sec in windowSections" :key="sec.group.group_id">
        <div class="section-head">
          <h2 class="section-title">{{ sec.title }}</h2>
          <span class="badge" :class="sec.gate.satisfied ? 'closed' : 'in_progress'">
            {{
              sec.gate.satisfied
                ? `已复核（${sec.gate.total_photos} 张）`
                : `待复核 ${sec.gate.pending_photos} 张`
            }}
          </span>
        </div>
        <div class="section-sub muted">{{ sec.subtitle }}</div>

        <!-- 完成分析（草稿 → 确认可校正 → 重跑仅 draft） -->
        <div class="card analysis-card">
          <div class="row analysis-row">
            <div class="body">
              <div class="title">完成分析</div>
              <div class="sub">
                <template v-if="!sec.gate.satisfied">
                  门控未满足：待复核 {{ sec.gate.pending_photos }} 张，全部复核后可生成
                </template>
                <template v-else>门控已满足，可生成完成情况草稿</template>
              </div>
            </div>
            <van-button
              type="primary"
              size="small"
              :disabled="!sec.group.subjects.length || !sec.gate.satisfied"
              :loading="analysisBusy === sec.group.group_id"
              @click="generateAnalysis(sec.group)"
            >
              生成分析
            </van-button>
          </div>

          <div
            v-for="a in analysisByGroup[sec.group.group_id] ?? []"
            :key="a.analysis_id"
            class="analysis-item"
          >
            <div class="title">
              {{ subjectText(a.subject ?? "") }}
              <span class="badge" :class="a.status === 'confirmed' ? 'closed' : 'published'">
                {{ analysisStatusText(a.status) }}
              </span>
            </div>
            <div class="sub">
              结论 {{ conclusionText(a.conclusion) }}
              · 置信 {{ a.confidence != null ? Math.round(a.confidence * 100) + "%" : "-" }}
              · 依据 {{ a.evidence_photo_ids.length }} 张
              · 第 {{ a.run_no }} 次
            </div>
            <div class="actions">
              <van-button
                v-if="a.status === 'draft'"
                type="primary"
                size="small"
                @click="openConfirm(sec.group, a)"
              >
                确认
              </van-button>
              <van-button
                v-if="a.status === 'draft'"
                plain
                size="small"
                :loading="analysisBusy === sec.group.group_id"
                @click="rerunAnalysis(sec.group, a)"
              >
                重跑
              </van-button>
            </div>
          </div>
          <div v-if="!(analysisByGroup[sec.group.group_id] ?? []).length" class="muted small">
            尚未生成分析；门控满足后点「生成分析」。
          </div>
        </div>

        <PhotoCard
          v-for="p in sec.photos"
          :key="p.photo_id"
          :photo="p"
          :thumb="thumbs[p.photo_id]"
          :student-name="studentName(p.student_id)"
          :subject-names="subjectNames"
          :group-names="groupNames"
          :busy="busy"
          @preview="preview(p)"
          @remove="removePhoto"
          @accept="acceptSuggestion"
          @reject="rejectSuggestion"
          @assign="openPicker"
          @retry="retrySuggestion"
        />
      </template>
    </template>

    <!-- 挂接 / 改挂目标选择弹层（目标 = 聚合学科子任务 group_subject_id） -->
    <van-popup v-model:show="pickerOpen" position="bottom" round class="assign-popup">
      <div class="popup-inner">
        <h3>{{ pickerRelinkLinkId ? "改挂到…" : "挂接到…" }}</h3>
        <div class="muted small">
          选择作业窗口与学科子任务（判定与门控按学科子任务粒度，可跨学科多条）。
        </div>

        <div class="picker-block">
          <span class="field-label">作业窗口</span>
          <div v-if="!pickerGroups.length" class="muted small">
            该学生暂无聚合作业窗口（需先有已解析内容的任务）。
          </div>
          <button
            v-for="g in pickerGroups"
            :key="g.group_id"
            class="group-chip"
            :class="{ on: pickerGroupId === g.group_id }"
            @click="selectPickerGroup(g.group_id)"
          >
            {{ windowDisplayName(g.display_name, g.window_type) }}
          </button>
        </div>

        <div v-if="pickerGroupId" class="picker-block">
          <span class="field-label">学科子任务</span>
          <van-loading v-if="pickerLoading" size="18px">加载学科…</van-loading>
          <div v-else-if="!pickerSubjects.length" class="muted small">
            该窗口暂无可挂接学科子任务。
          </div>
          <button
            v-for="s in pickerSubjects"
            :key="s.group_subject_id"
            class="group-chip"
            :class="{ on: pickerTargetId === s.group_subject_id }"
            @click="pickerTargetId = s.group_subject_id"
          >
            {{ subjectText(s.subject) }}
          </button>
        </div>

        <div class="action-gap"></div>
        <van-button
          round
          block
          type="primary"
          :loading="busy"
          :disabled="!pickerTargetId"
          @click="confirmPicker"
        >
          {{ pickerRelinkLinkId ? "确认改挂" : "确认挂接" }}
        </van-button>
      </div>
    </van-popup>

    <!-- 完成分析确认弹层（可校正结论） -->
    <van-popup v-model:show="confirmOpen" position="bottom" round>
      <div class="popup-inner">
        <h3>确认完成分析</h3>
        <div class="muted small">可校正结论后确认；确认后回写判定单元并锁定相关照片。</div>
        <span class="field-label">结论</span>
        <select v-model="confirmConclusion" class="native-select">
          <option v-for="c in CONCLUSIONS" :key="c" :value="c">{{ conclusionText(c) }}</option>
        </select>
        <div class="action-gap"></div>
        <van-button round block type="primary" :loading="busy" @click="doConfirm">确认结论</van-button>
      </div>
    </van-popup>

    <div class="action-gap"></div>
    <BottomNav active="photos" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { showConfirmDialog, showImagePreview, showToast } from "vant";

import {
  confirmCompletionAnalysis,
  createCompletionAnalyses,
  deletePhoto,
  fetchPhotoBlob,
  getLinkSuggestions,
  getTaskGroup,
  listPhotoGates,
  listPhotos,
  listStudents,
  listTaskGroups,
  rerunCompletionAnalysis,
  reviewPhotoLinks,
} from "@/api";
import { toastError } from "@/api/http";
import type {
  AnalysisItem,
  Conclusion,
  GateStatus,
  Photo,
  PhotoLink,
  PhotoListParams,
  PhotoStatus,
  Student,
  TaskGroup,
  TaskGroupListParams,
  TaskGroupSubject,
} from "@/api/types";
import BottomNav from "@/components/BottomNav.vue";
import PhotoCard from "@/components/PhotoCard.vue";
import {
  WINDOW_TYPE_TEXT,
  analysisStatusText,
  conclusionText,
  subjectText,
  windowDisplayName,
} from "@/utils/format";
import { useSessionStore } from "@/stores/session";

interface Section {
  group: TaskGroup;
  title: string;
  subtitle: string;
  gate: GateStatus;
  photos: Photo[];
}

const TABS: { value: PhotoStatus | ""; text: string }[] = [
  { value: "", text: "全部" },
  { value: "unassigned", text: "待处理" },
  { value: "suggested", text: "建议待采纳" },
  { value: "assigned", text: "已挂接" },
  { value: "rejected", text: "已驳回" },
];

const CONCLUSIONS: Conclusion[] = ["完成", "部分完成", "未完成", "无法判断"];

const router = useRouter();
const session = useSessionStore();

const students = ref<Student[]>([]);
const photos = ref<Photo[]>([]);
const groups = ref<TaskGroup[]>([]);
const gates = ref<GateStatus[]>([]);
const loading = ref(false);
const busy = ref(false);
const filters = reactive<{ student_id: string; status: PhotoStatus | "" }>({
  student_id: "",
  status: "",
});
const thumbs: Record<string, string> = {};

// 挂接 / 改挂弹层
const pickerOpen = ref(false);
const pickerPhoto = ref<Photo | null>(null);
const pickerRelinkLinkId = ref<string | null>(null);
const pickerGroupId = ref("");
const pickerTargetId = ref("");
const pickerSubjects = ref<TaskGroupSubject[]>([]);
const pickerLoading = ref(false);

// 完成分析
const analysisByGroup = ref<Record<string, AnalysisItem[]>>({});
const analysisBusy = ref("");
const confirmOpen = ref(false);
const confirmItem = ref<AnalysisItem | null>(null);
const confirmGroupId = ref("");
const confirmConclusion = ref<Conclusion>("完成");

const studentNameById = new Map<string, string>();

onMounted(async () => {
  if (session.isFamily) {
    try {
      students.value = await listStudents();
      for (const s of students.value) studentNameById.set(s.student_id, s.name);
    } catch (err) {
      toastError(err);
    }
  }
  await load();
});

onBeforeUnmount(() => {
  for (const url of Object.values(thumbs)) URL.revokeObjectURL(url);
});

// ---- 派生：聚合学科子任务 → 窗口 / 学科显示名 ----
const subjectToGroup = computed(() => {
  const m = new Map<string, TaskGroup>();
  for (const g of groups.value) for (const s of g.subjects) m.set(s.group_subject_id, g);
  return m;
});

const subjectNames = computed<Record<string, string>>(() => {
  const m: Record<string, string> = {};
  for (const g of groups.value) {
    for (const s of g.subjects) m[s.group_subject_id] = subjectText(s.subject);
  }
  return m;
});

const groupNames = computed<Record<string, string>>(() => {
  const m: Record<string, string> = {};
  for (const g of groups.value) {
    for (const s of g.subjects) {
      m[s.group_subject_id] = windowDisplayName(g.display_name, g.window_type);
    }
  }
  return m;
});

const sortedGroups = computed(() =>
  [...groups.value].sort((a, b) => a.group_key.localeCompare(b.group_key))
);

const unlinkedPhotos = computed(() => photos.value.filter((p) => !photoGroupId(p)));

const windowSections = computed<Section[]>(() => {
  const list: Section[] = [];
  for (const g of sortedGroups.value) {
    const items = photos.value.filter((p) => photoGroupId(p) === g.group_id);
    if (!items.length) continue;
    list.push({
      group: g,
      title: windowDisplayName(g.display_name, g.window_type),
      subtitle: WINDOW_TYPE_TEXT[g.window_type] ?? g.window_type,
      gate: gateForGroup(g),
      photos: items,
    });
  }
  return list;
});

const pickerGroups = computed(() => {
  const p = pickerPhoto.value;
  if (!p) return [] as TaskGroup[];
  return sortedGroups.value.filter(
    (g) => g.student_id === p.student_id && g.subjects.length > 0
  );
});

// 复核目标数据源 = GET /task-groups/{group_id}（API-M001-020）的 subjects[]（惰性加载）。


function studentName(id: string): string {
  return studentNameById.get(id) ?? (session.isFamily ? "未知学生" : "本人");
}

/** 照片归属窗口：取首个有效挂接的 group_subject_id 反查聚合对象。 */
function photoGroupId(p: Photo): string | null {
  for (const l of p.links) {
    if (l.rejected_at) continue;
    const g = subjectToGroup.value.get(l.group_subject_id);
    if (g) return g.group_id;
  }
  return null;
}

/** 本地门控重算（兜底）：窗口内有确认挂接的照片数 / 其中仍有未确认挂接的照片数。 */
function localGate(g: TaskGroup): GateStatus {
  const ids = new Set(g.subjects.map((s) => s.group_subject_id));
  let total = 0;
  let pending = 0;
  for (const p of photos.value) {
    const active = p.links.filter((l) => !l.rejected_at && ids.has(l.group_subject_id));
    if (!active.length) continue;
    total += 1;
    if (active.some((l) => !l.confirmed_at)) pending += 1;
  }
  return {
    group_key: g.group_key,
    window_type: g.window_type,
    total_photos: total,
    pending_photos: pending,
    satisfied: pending === 0,
  };
}

/** 优先后端 `GET /photo-gates`（按窗口）；无匹配时本地重算，保证生成按钮禁用判定准确。 */
function gateForGroup(g: TaskGroup): GateStatus {
  const remote = gates.value.find((x) => x.group_key && x.group_key === g.group_key);
  return remote ?? localGate(g);
}

async function load(): Promise<void> {
  loading.value = true;
  try {
    const studentFilter = session.isFamily ? filters.student_id || undefined : undefined;
    const photoParams: PhotoListParams = {
      student_id: studentFilter,
      status: filters.status,
      page: 1,
      page_size: 50,
    };
    const scopeParams: TaskGroupListParams = studentFilter ? { student_id: studentFilter } : {};
    const [photoRes, groupRes, gateRes] = await Promise.all([
      listPhotos(photoParams),
      listTaskGroups(scopeParams).catch(() => ({ items: [] as TaskGroup[] })),
      listPhotoGates(scopeParams).catch(() => [] as GateStatus[]),
    ]);

    for (const url of Object.values(thumbs)) URL.revokeObjectURL(url);
    Object.keys(thumbs).forEach((k) => delete thumbs[k]);

    photos.value = photoRes.items;
    groups.value = groupRes.items;
    gates.value = gateRes;
    await loadThumbs(photoRes.items);
  } catch (err) {
    toastError(err);
  } finally {
    loading.value = false;
  }
}

async function loadThumbs(items: Photo[]): Promise<void> {
  await Promise.all(
    items.map(async (p) => {
      if (thumbs[p.photo_id]) return;
      try {
        thumbs[p.photo_id] = await fetchPhotoBlob(p.photo_id, "normalized");
      } catch (_) {
        /* 取图失败不阻塞列表，点击查看时会提示 */
      }
    })
  );
}

function reload(): void {
  void load();
}

function switchTab(value: PhotoStatus | ""): void {
  if (filters.status === value) return;
  filters.status = value;
  void load();
}

function preview(p: Photo): void {
  if (!thumbs[p.photo_id]) {
    showToast("图片加载失败");
    return;
  }
  showImagePreview([thumbs[p.photo_id]]);
}

// ---- 逐张挂接复核（accept / reject / relink） ----
function activeLinks(p: Photo): PhotoLink[] {
  return p.links.filter((l) => !l.rejected_at);
}

function pendingSuggestion(p: Photo): PhotoLink | undefined {
  return activeLinks(p).find((l) => !l.confirmed_at && l.source === "ai");
}

async function acceptSuggestion(p: Photo): Promise<void> {
  const s = pendingSuggestion(p);
  if (!s) return;
  busy.value = true;
  try {
    await reviewPhotoLinks(p.photo_id, { action: "accept", link_id: s.link_id });
    showToast("已采纳建议");
    await load();
  } catch (err) {
    toastError(err);
  } finally {
    busy.value = false;
  }
}

async function rejectSuggestion(p: Photo): Promise<void> {
  const s = pendingSuggestion(p);
  if (!s) return;
  try {
    await showConfirmDialog({
      title: "驳回建议",
      message: "确定驳回该 AI 挂接建议？（照片可另挂）",
    });
  } catch (_) {
    return;
  }
  busy.value = true;
  try {
    await reviewPhotoLinks(p.photo_id, { action: "reject", link_id: s.link_id });
    showToast("已驳回建议");
    await load();
  } catch (err) {
    toastError(err);
  } finally {
    busy.value = false;
  }
}

async function retrySuggestion(p: Photo): Promise<void> {
  busy.value = true;
  try {
    await getLinkSuggestions(p.photo_id, true);
    showToast("已重试挂接建议");
    await load();
  } catch (err) {
    toastError(err);
  } finally {
    busy.value = false;
  }
}

/** 打开挂接目标选择：带 link 为「改挂」，不带为手工挂接（兜底 B6）。 */
async function openPicker(p: Photo, link?: PhotoLink): Promise<void> {
  pickerPhoto.value = p;
  pickerRelinkLinkId.value = link?.link_id ?? null;
  pickerOpen.value = true;
  const g = link ? subjectToGroup.value.get(link.group_subject_id) : undefined;
  if (g) {
    await loadPickerSubjects(g.group_id, link ? link.group_subject_id : "");
  } else {
    pickerGroupId.value = "";
    pickerSubjects.value = [];
    pickerTargetId.value = "";
  }
}

/** 惰性取 `GET /task-groups/{group_id}`（API-M001-020）的 subjects[] 作为复核目标。 */
async function loadPickerSubjects(groupId: string, preselect = ""): Promise<void> {
  pickerGroupId.value = groupId;
  pickerSubjects.value = [];
  pickerTargetId.value = preselect;
  pickerLoading.value = true;
  try {
    const g = await getTaskGroup(groupId);
    pickerSubjects.value = g.subjects;
    const idx = groups.value.findIndex((x) => x.group_id === groupId);
    if (idx >= 0) groups.value[idx] = g;
  } catch (err) {
    toastError(err);
  } finally {
    pickerLoading.value = false;
  }
}

function selectPickerGroup(groupId: string): void {
  void loadPickerSubjects(groupId);
}

async function confirmPicker(): Promise<void> {
  const p = pickerPhoto.value;
  if (!p || !pickerTargetId.value) return;
  busy.value = true;
  try {
    if (pickerRelinkLinkId.value) {
      await reviewPhotoLinks(p.photo_id, {
        action: "relink",
        link_id: pickerRelinkLinkId.value,
        group_subject_id: pickerTargetId.value,
      });
      showToast("已改挂");
    } else {
      await reviewPhotoLinks(p.photo_id, {
        action: "accept",
        group_subject_id: pickerTargetId.value,
      });
      showToast("已挂接");
    }
    pickerOpen.value = false;
    await load();
  } catch (err) {
    toastError(err);
  } finally {
    busy.value = false;
  }
}

async function removePhoto(p: Photo): Promise<void> {
  try {
    await showConfirmDialog({
      title: "删除照片",
      message: "将删除照片原图/归一图及记录，不可恢复。已挂接照片删除后不影响任务状态。确定？",
    });
  } catch (_) {
    return;
  }
  busy.value = true;
  try {
    await deletePhoto(p.photo_id);
    showToast("已删除");
    await load();
  } catch (err) {
    toastError(err);
  } finally {
    busy.value = false;
  }
}

// ---- 完成分析（生成 → 确认可校正 → 重跑仅 draft） ----
async function generateAnalysis(g: TaskGroup): Promise<void> {
  analysisBusy.value = g.group_id;
  try {
    const res = await createCompletionAnalyses({
      student_id: g.student_id,
      group_key: g.group_key,
    });
    analysisByGroup.value = { ...analysisByGroup.value, [g.group_id]: res.items };
    showToast(res.items.length ? "已生成分析草稿" : "该窗口暂无可分析的学科");
  } catch (err) {
    toastError(err);
  } finally {
    analysisBusy.value = "";
  }
}

function openConfirm(g: TaskGroup, item: AnalysisItem): void {
  confirmGroupId.value = g.group_id;
  confirmItem.value = item;
  confirmConclusion.value = item.conclusion;
  confirmOpen.value = true;
}

async function doConfirm(): Promise<void> {
  const item = confirmItem.value;
  if (!item) return;
  busy.value = true;
  try {
    const updated = await confirmCompletionAnalysis(item.analysis_id, {
      conclusion: confirmConclusion.value,
    });
    const list = analysisByGroup.value[confirmGroupId.value] ?? [];
    analysisByGroup.value = {
      ...analysisByGroup.value,
      [confirmGroupId.value]: list.map((x) =>
        x.analysis_id === updated.analysis_id ? updated : x
      ),
    };
    confirmOpen.value = false;
    showToast("已确认结论");
    await load();
  } catch (err) {
    toastError(err);
  } finally {
    busy.value = false;
  }
}

async function rerunAnalysis(g: TaskGroup, item: AnalysisItem): Promise<void> {
  analysisBusy.value = g.group_id;
  try {
    const updated = await rerunCompletionAnalysis(item.analysis_id);
    const list = (analysisByGroup.value[g.group_id] ?? []).filter(
      (x) => x.analysis_id !== item.analysis_id
    );
    analysisByGroup.value = { ...analysisByGroup.value, [g.group_id]: [...list, updated] };
    showToast("已重跑，生成新草稿");
  } catch (err) {
    toastError(err);
  } finally {
    analysisBusy.value = "";
  }
}
</script>

<style scoped>
.filter-row {
  margin-bottom: 6px;
}
.status-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.status-chip {
  border: 1px solid var(--app-line);
  background: #fff;
  color: var(--app-muted);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 13px;
  cursor: pointer;
}
.status-chip.on {
  background: var(--van-primary-color);
  border-color: var(--van-primary-color);
  color: #fff;
}
.loading {
  padding: 48px 0;
  justify-content: center;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.section-sub {
  font-size: 12px;
  margin-top: -2px;
}
.analysis-card {
  padding: 12px 14px;
}
.analysis-row {
  border: none;
  padding: 0;
}
.analysis-item {
  border-top: 1px dashed var(--app-line);
  margin-top: 10px;
  padding-top: 10px;
}
.assign-popup {
  max-height: 80vh;
  overflow-y: auto;
}
.popup-inner {
  padding: 16px 16px calc(16px + env(safe-area-inset-bottom));
}
.popup-inner h3 {
  margin: 0 0 4px;
  font-size: 16px;
}
.group-chip {
  display: inline-block;
  border: 1px solid var(--app-line);
  background: #fff;
  color: var(--app-text);
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 13px;
  margin: 4px 6px 0 0;
  cursor: pointer;
}
.group-chip.on {
  background: var(--van-primary-color);
  border-color: var(--van-primary-color);
  color: #fff;
}
.picker-block {
  margin-top: 10px;
}
</style>
