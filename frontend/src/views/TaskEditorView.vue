<template>
  <div class="page">
    <div class="page-topbar">
      <van-button icon="arrow-left" plain size="small" @click="goBack">返回</van-button>
      <h1>{{ isEdit ? "草稿确认" : "新建任务" }}</h1>
    </div>

    <van-loading v-if="loading" class="loading" size="24px">加载中…</van-loading>

    <!-- 新建：只上传输入源（图片 / 粘贴文本），不填内容（API-M001-007） -->
    <van-form v-else-if="!isEdit" @submit="onCreate">
      <div class="card">
        <label class="field-label">学生</label>
        <select v-model="form.student_id" class="native-select">
          <option v-for="s in students" :key="s.student_id" :value="s.student_id">
            {{ s.name }}
          </option>
        </select>

        <label class="field-label">年级/学段（可选）</label>
        <van-field v-model="form.grade_level" name="grade_level" placeholder="如：三年级" maxlength="64" />

        <label class="field-label">上传作业图片（可多选，可选）</label>
        <input
          ref="fileInput"
          class="native-file"
          type="file"
          accept="image/*"
          multiple
          @change="onPickFiles"
        />
        <div v-if="files.length" class="muted tiny">已选 {{ files.length }} 张：{{ fileNames }}</div>

        <label class="field-label">或粘贴作业文本（图片与文本可同时提交）</label>
        <textarea
          v-model="form.pasted_text"
          class="native-textarea"
          rows="4"
          maxlength="4000"
          placeholder="如：数学 练习册 P23 第 1-10 题"
        ></textarea>
        <div class="muted tiny">上传即归属今天（凌晨 4 点切日）；同日同类型重复上传会自动合并。</div>
      </div>

      <div class="card">
        <van-button round block type="primary" native-type="submit" :loading="saving">
          提交任务
        </van-button>
      </div>
    </van-form>

    <!-- 编辑：降级为「解析草稿确认」 -->
    <van-form v-else @submit="onSave">
      <div class="card">
        <van-field
          v-model="form.title"
          name="title"
          label="标题"
          maxlength="64"
          :rules="[{ required: true, message: '请输入标题' }]"
        />

        <div class="muted meta-line">
          学生 {{ studentName }} · 归属 {{ task?.belong_date }} · 第 {{ task?.week_index }} 周 ·
          {{ SPEC_TEXT[task?.spec_status ?? ""] ?? task?.spec_status }}
        </div>

        <label class="field-label">年级/学段（可选）</label>
        <van-field v-model="form.grade_level" name="grade_level" placeholder="如：三年级" maxlength="64" />

        <label class="field-label">截止时间（可选）</label>
        <van-field v-model="form.deadline" name="deadline" type="datetime-local" />
      </div>

      <h2 class="section-title" style="padding: 0 2px">内容项（AI 解析草稿，可增删改）</h2>

      <div v-for="(it, idx) in contents" :key="idx" class="card item-editor">
        <div class="muted item-no">第 {{ idx + 1 }} 项</div>
        <label class="field-label">学科</label>
        <select v-model="it.subject" class="native-select">
          <option v-for="o in SUBJECTS_OPTS" :key="o.value" :value="o.value">{{ o.text }}</option>
        </select>
        <label class="field-label">内容</label>
        <textarea
          v-model="it.text"
          class="native-textarea"
          rows="2"
          maxlength="2000"
          placeholder="如：练习册 P23 第 1-10 题"
        ></textarea>
        <button type="button" class="remove-item" @click="removeContent(idx)">删除本项</button>
      </div>

      <div class="card">
        <van-button round block plain type="primary" @click="addContent">＋ 添加一项</van-button>
        <div class="action-gap"></div>
        <van-button round block type="primary" native-type="submit" :loading="saving">保存修改</van-button>
        <div class="action-gap"></div>
        <van-button
          v-if="task?.spec_status !== 'confirmed'"
          round
          block
          plain
          type="success"
          :loading="confirming"
          @click="onConfirm"
        >
          确认解析结果
        </van-button>
      </div>
    </van-form>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "vant";

import {
  confirmTaskParse,
  createTask,
  createUploadBatch,
  getTask,
  listStudents,
  updateTask,
  uploadPhoto,
} from "@/api";
import { toastError } from "@/api/http";
import type { ContentItemInput, SourceInput, TaskDetail } from "@/api/types";
import { localInputValue, toIso } from "@/utils/format";

const props = defineProps<{ id?: string }>();
const router = useRouter();

const SUBJECTS_OPTS = [
  { value: "math", text: "数学" },
  { value: "chinese", text: "语文" },
  { value: "english", text: "英语" },
];

const SPEC_TEXT: Record<string, string> = {
  placeholder: "待解析",
  parsed: "已解析待确认",
  confirmed: "已确认",
};

const isEdit = computed(() => Boolean(props.id));
const loading = ref(false);
const saving = ref(false);
const confirming = ref(false);
const students = ref<{ student_id: string; name: string }[]>([]);
const task = ref<TaskDetail | null>(null);
const files = ref<File[]>([]);
const fileInput = ref<HTMLInputElement | null>(null);

const form = reactive({
  title: "",
  student_id: "",
  grade_level: "",
  deadline: "",
  pasted_text: "",
});

const contents = ref<ContentItemInput[]>([]);

const studentName = computed(
  () => students.value.find((s) => s.student_id === task.value?.student_id)?.name ?? "-"
);
const fileNames = computed(() => files.value.map((f) => f.name).join("、"));

onMounted(async () => {
  loading.value = true;
  try {
    students.value = await listStudents();
    if (!students.value.length) {
      showToast("请先创建学生档案");
      router.replace("/students");
      return;
    }
    if (isEdit.value) {
      const t = await getTask(props.id!);
      task.value = t;
      form.title = t.title;
      form.student_id = t.student_id;
      form.grade_level = t.grade_level ?? "";
      form.deadline = localInputValue(t.deadline);
      contents.value = t.contents.map((c) => ({
        content_id: c.content_id,
        subject: c.subject,
        text: c.text,
      }));
    } else {
      form.student_id = students.value[0]?.student_id ?? "";
    }
  } catch (err) {
    toastError(err);
  } finally {
    loading.value = false;
  }
});

function goBack(): void {
  router.push(isEdit.value ? `/tasks/${props.id}` : "/tasks");
}

function onPickFiles(e: Event): void {
  const input = e.target as HTMLInputElement;
  files.value = Array.from(input.files ?? []);
}

function removeContent(idx: number): void {
  contents.value.splice(idx, 1);
}

function addContent(): void {
  contents.value.push({ subject: "math", text: "" });
}

function normalizedContents(): ContentItemInput[] {
  return contents.value
    .map((c) => ({ content_id: c.content_id, subject: c.subject, text: c.text.trim() }))
    .filter((c) => c.text);
}

async function onCreate(): Promise<void> {
  const text = form.pasted_text.trim();
  if (!text && !files.value.length) {
    showToast("请上传图片或粘贴作业文本");
    return;
  }
  saving.value = true;
  try {
    const sources: SourceInput[] = [];
    if (text) sources.push({ seq: sources.length + 1, kind: "text", text_content: text });
    if (files.value.length) {
      const batch = await createUploadBatch(form.student_id, "task_spec");
      for (const f of files.value) {
        const up = await uploadPhoto(batch.batch_id, f);
        sources.push({ seq: sources.length + 1, kind: "image", photo_id: up.photo_id });
      }
    }
    const saved = await createTask({
      student_id: form.student_id,
      category: "school",
      grade_level: form.grade_level.trim() || null,
      sources,
    });
    showToast("已按今天归属创建");
    router.replace(`/tasks/${saved.task_id}`);
  } catch (err) {
    showToast(err instanceof Error ? err.message : "提交失败");
  } finally {
    saving.value = false;
  }
}

async function onSave(): Promise<void> {
  saving.value = true;
  try {
    const saved = await updateTask(props.id!, {
      title: form.title,
      grade_level: form.grade_level.trim() || null,
      deadline: toIso(form.deadline),
      contents: normalizedContents(),
    });
    showToast("已保存");
    task.value = saved;
  } catch (err) {
    showToast(err instanceof Error ? err.message : "保存失败");
  } finally {
    saving.value = false;
  }
}

async function onConfirm(): Promise<void> {
  const items = normalizedContents();
  if (!items.length) {
    showToast("请至少填写一项内容");
    return;
  }
  confirming.value = true;
  try {
    const saved = await confirmTaskParse(props.id!, { confirmed: true, contents: items });
    showToast("解析结果已确认");
    task.value = saved;
  } catch (err) {
    showToast(err instanceof Error ? err.message : "确认失败");
  } finally {
    confirming.value = false;
  }
}
</script>

<style scoped>
.loading {
  padding: 48px 0;
  justify-content: center;
}
.item-no {
  font-weight: 700;
  margin-bottom: 4px;
}
.meta-line {
  font-size: 13px;
  margin: 8px 0;
}
.native-file {
  width: 100%;
  font-size: 14px;
}
.tiny {
  font-size: 12px;
  margin-top: 6px;
}
</style>
