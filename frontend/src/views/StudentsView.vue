<template>
  <div class="page">
    <div class="page-topbar"><h1>学生档案</h1></div>

    <div v-if="!students.length" class="card empty">还没有学生档案，先添加一位学生</div>
    <div v-for="s in students" :key="s.student_id" class="card">
      <div class="row">
        <div class="body">
          <div class="title">{{ s.name }}</div>
          <div class="sub">
            {{ s.school.name }}（{{ stageText(s.school.stage) }}）{{
              s.grade_level ? ` · ${s.grade_level}` : ""
            }}{{ s.relation ? ` · ${s.relation}` : "" }}
          </div>
        </div>
        <van-button size="small" plain type="primary" @click="fillForm(s)">编辑</van-button>
      </div>
    </div>

    <div class="card">
      <h2 class="section-title" style="margin-top: 0">{{ editingId ? "编辑学生" : "添加学生" }}</h2>
      <van-form @submit="onSubmit">
        <van-cell-group inset>
          <van-field
            v-model="form.name"
            name="name"
            label="姓名"
            placeholder="学生姓名"
            maxlength="32"
            :rules="[{ required: true, message: '请输入姓名' }]"
          />
          <van-field
            v-model="form.relation"
            name="relation"
            label="与账号关系"
            placeholder="如：儿子（可选）"
            maxlength="16"
          />
        </van-cell-group>

        <label class="field-label">学段</label>
        <select v-model="form.stage" class="native-select" @change="onStageChange">
          <option v-for="o in STAGES_OPTS" :key="o.value" :value="o.value">{{ o.text }}</option>
        </select>

        <label class="field-label">学校（必选）</label>
        <select v-model="form.school_id" class="native-select">
          <option value="" disabled>请选择学校</option>
          <option v-for="sc in schoolOptions" :key="sc.school_id" :value="sc.school_id">
            {{ sc.name }}
          </option>
        </select>

        <label class="field-label">年级/班级（可选）</label>
        <van-field
          v-model="form.grade_level"
          name="grade_level"
          placeholder="如：三年级 1 班"
          maxlength="64"
        />

        <div class="action-gap"></div>
        <div class="form-btns">
          <van-button round block type="primary" native-type="submit" :loading="saving">
            保存学生档案
          </van-button>
          <van-button v-if="editingId" round block plain @click="cancelEdit">取消编辑</van-button>
        </div>
      </van-form>
    </div>

    <BottomNav active="students" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { showToast } from "vant";

import { createStudent, fetchSchools, listStudents, schoolsOfStage, updateStudent } from "@/api";
import type { Stage, Student } from "@/api/types";
import BottomNav from "@/components/BottomNav.vue";
import { stageText } from "@/utils/format";

const STAGES_OPTS: { value: Stage; text: string }[] = [
  { value: "primary", text: "小学" },
  { value: "junior", text: "初中" },
  { value: "senior", text: "高中" },
];

const students = ref<Student[]>([]);
const editingId = ref<string | null>(null);
const saving = ref(false);

const form = reactive<{
  name: string;
  relation: string;
  stage: Stage;
  school_id: string;
  grade_level: string;
}>({ name: "", relation: "", stage: "primary", school_id: "", grade_level: "" });

const schoolOptions = computed(() => schoolsOfStage(form.stage));

function onStageChange(): void {
  form.school_id = "";
}

async function load(): Promise<void> {
  await fetchSchools();
  students.value = await listStudents();
}

onMounted(load);

function fillForm(s: Student): void {
  editingId.value = s.student_id;
  form.name = s.name;
  form.relation = s.relation ?? "";
  form.stage = s.school.stage;
  form.school_id = s.school.school_id;
  form.grade_level = s.grade_level ?? "";
}

function cancelEdit(): void {
  editingId.value = null;
  form.name = "";
  form.relation = "";
  form.stage = "primary";
  form.school_id = "";
  form.grade_level = "";
}

async function onSubmit(): Promise<void> {
  if (!form.school_id) {
    showToast("请选择学校");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      name: form.name,
      relation: form.relation || null,
      grade_level: form.grade_level || null,
      school_id: form.school_id,
    };
    if (editingId.value) await updateStudent(editingId.value, payload);
    else await createStudent(payload);
    showToast("已保存");
    editingId.value = null;
    form.name = "";
    form.relation = "";
    form.grade_level = "";
    form.school_id = "";
    await load();
  } catch (err) {
    showToast(err instanceof Error ? err.message : "保存失败");
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.form-btns {
  display: grid;
  gap: 10px;
}
</style>
