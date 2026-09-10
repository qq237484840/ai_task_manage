<template>
  <div class="page">
    <div class="page-topbar"><h1>我的</h1></div>

    <div class="card">
      <div class="row" style="border: none">
        <div class="avatar">👪</div>
        <div class="body">
          <div class="title">{{ session.loginName || "家庭账号" }}</div>
          <div class="sub">
            {{ session.isFamily ? "家庭模式（家长）· 全家任务与档案" : "学生模式 · 仅本人任务与档案" }}
          </div>
        </div>
      </div>
    </div>

    <!-- 家长：学生子账号管理（ACR-001：开通/停用/改密，家长专属） -->
    <template v-if="session.isFamily">
      <h2 class="section-title">学生子账号</h2>
      <div class="card muted small">
        为学生开通账号后可自主登录（仅本人数据）；密码至少 6 位。刷新后账号状态不随档案列表返回，如需改密/停用请直接操作。
      </div>

      <div v-for="s in students" :key="s.student_id" class="card account-card">
        <div class="row">
          <div class="body">
            <div class="title">{{ s.name }}</div>
            <div class="sub">{{ s.school.name }} · {{ stageText(s.school.stage) }}</div>
          </div>
          <van-button
            size="small"
            :type="formOpenFor === s.student_id ? 'primary' : 'default'"
            :plain="formOpenFor !== s.student_id"
            @click="toggleOpen(s)"
          >
            {{ formOpenFor === s.student_id ? "收起" : "开通账号" }}
          </van-button>
          <van-button size="small" plain type="warning" @click="toggleManage(s)">
            {{ formManageFor === s.student_id ? "收起" : "改密/停用" }}
          </van-button>
        </div>

        <!-- 开通 -->
        <div v-if="formOpenFor === s.student_id" class="sub-form">
          <van-field v-model="openForm.login_name" label="登录名" placeholder="≥3 位" maxlength="64" />
          <van-field
            v-model="openForm.password"
            type="password"
            label="初始密码"
            placeholder="≥6 位"
            maxlength="128"
          />
          <van-button block type="primary" size="small" :loading="busy" @click="submitOpen(s)">
            开通
          </van-button>
        </div>

        <!-- 改密/停用 -->
        <div v-if="formManageFor === s.student_id" class="sub-form">
          <van-field
            v-model="manageForm.password"
            type="password"
            label="新密码（选填）"
            placeholder="留空则不修改"
            maxlength="128"
          />
          <div class="manage-row">
            <span class="muted">账号状态</span>
            <van-switch
              :model-value="manageForm.status === 'active'"
              size="20"
              @update:model-value="(v: boolean) => (manageForm.status = v ? 'active' : 'disabled')"
            />
          </div>
          <van-button block plain type="warning" size="small" :loading="busy" @click="submitManage(s)">
            保存修改
          </van-button>
        </div>
      </div>
    </template>

    <!-- 学生：仅提示本人，无管理入口 -->
    <div v-else class="card muted small">
      学生账号仅能访问本人任务与档案。如需开通/停用/改密，请联系家长在「我的」中操作。
    </div>

    <div class="action-gap"></div>
    <van-button block round type="danger" :loading="loggingOut" @click="onLogout">
      退出登录
    </van-button>

    <BottomNav active="mine" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "vant";

import { listStudents, openStudentAccount, updateStudentAccount } from "@/api";
import type { AccountStatus } from "@/api";
import type { Student } from "@/api/types";
import BottomNav from "@/components/BottomNav.vue";
import { stageText } from "@/utils/format";
import { toastError } from "@/api/http";
import { useSessionStore } from "@/stores/session";

const router = useRouter();
const session = useSessionStore();
const loggingOut = ref(false);
const busy = ref(false);

const students = ref<Student[]>([]);
const formOpenFor = ref<string | null>(null);
const formManageFor = ref<string | null>(null);
const openForm = reactive({ login_name: "", password: "" });
const manageForm = reactive<{ password: string; status: AccountStatus }>({
  password: "",
  status: "active",
});

onMounted(async () => {
  if (session.isFamily) {
    try {
      students.value = await listStudents();
    } catch (err) {
      toastError(err);
    }
  }
});

function toggleOpen(s: Student): void {
  formOpenFor.value = formOpenFor.value === s.student_id ? null : s.student_id;
  formManageFor.value = null;
  openForm.login_name = "";
  openForm.password = "";
}

function toggleManage(s: Student): void {
  formManageFor.value = formManageFor.value === s.student_id ? null : s.student_id;
  formOpenFor.value = null;
  manageForm.password = "";
  manageForm.status = "active";
}

async function submitOpen(s: Student): Promise<void> {
  const loginName = openForm.login_name.trim();
  if (loginName.length < 3) return void showToast("登录名至少 3 位");
  if (openForm.password.length < 6) return void showToast("密码至少 6 位");
  busy.value = true;
  try {
    const r = await openStudentAccount(s.student_id, {
      login_name: loginName,
      password: openForm.password,
    });
    showToast(`已开通：${r.login_name}${r.password_warning ? "（" + r.password_warning + "）" : ""}`);
    formOpenFor.value = null;
  } catch (err) {
    toastError(err);
  } finally {
    busy.value = false;
  }
}

async function submitManage(s: Student): Promise<void> {
  const payload: { status?: AccountStatus; password?: string } = {};
  if (manageForm.password) {
    if (manageForm.password.length < 6) return void showToast("密码至少 6 位");
    payload.password = manageForm.password;
  }
  payload.status = manageForm.status;
  busy.value = true;
  try {
    const r = await updateStudentAccount(s.student_id, payload);
    showToast(
      `已更新：${r.status === "active" ? "启用" : "停用"}` +
        (payload.password ? "，密码已修改" : "") +
        (r.password_warning ? "（" + r.password_warning + "）" : "")
    );
    formManageFor.value = null;
  } catch (err) {
    toastError(err);
  } finally {
    busy.value = false;
  }
}

async function onLogout(): Promise<void> {
  loggingOut.value = true;
  try {
    await session.logout();
  } catch (err) {
    toastError(err);
  } finally {
    router.replace("/login");
  }
}
</script>

<style scoped>
.avatar {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: #eef2ff;
  color: #3b5bdb;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex: none;
}
.account-card .row .body {
  min-width: 0;
}
.small {
  font-size: 12px;
  line-height: 1.7;
}
.sub-form {
  border-top: 1px solid var(--app-line);
  padding-top: 10px;
  margin-top: 6px;
}
.manage-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  font-size: 14px;
}
.sub-form .van-button {
  margin-top: 4px;
}
</style>
