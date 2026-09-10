<template>
  <div class="auth-page">
    <div class="card">
      <div class="brand">
        <div class="logo">📚</div>
        <h1>AI 作业智能评定</h1>
        <p>作业任务管理 · 两级主体登录</p>
      </div>

      <van-tabs v-model:active="mode" shrink @change="onModeChange">
        <van-tab title="家长登录" name="login" />
        <van-tab title="学生登录" name="student" />
        <van-tab title="注册" name="register" />
      </van-tabs>

      <van-form @submit="onSubmit">
        <van-cell-group inset>
          <van-field
            v-model="loginName"
            name="login_name"
            label="登录名"
            placeholder="邮箱 / 手机号 / 自定义"
            :rules="[
              { required: true, message: '请输入登录名' },
              { pattern: /^.{3,}$/, message: '登录名至少 3 位' },
            ]"
          />
          <van-field
            v-model="password"
            type="password"
            name="password"
            :label="mode === 'register' ? '密码' : '密码'"
            :placeholder="mode === 'register' ? '至少 8 位' : '请输入密码'"
            :rules="[
              { required: true, message: '请输入密码' },
              { pattern: mode === 'register' ? /^.{8,}$/ : /^.{1,}$/, message: mode === 'register' ? '密码至少 8 位' : '请输入密码' },
            ]"
          />
          <van-field
            v-if="mode === 'register'"
            v-model="displayName"
            name="display_name"
            label="家庭显示名"
            placeholder="如：小明一家"
            maxlength="32"
          />
        </van-cell-group>
        <div class="auth-submit">
          <van-button round block type="primary" native-type="submit" :loading="submitting">
            {{ submitText }}
          </van-button>
        </div>
      </van-form>

      <p v-if="mode === 'student'" class="hint">
        学生账号由家长在「我的 → 学生子账号」中开通；登录后仅能访问本人任务。
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "vant";

import { familyLogin, familyRegister, studentLogin } from "@/api";
import { toastError } from "@/api/http";
import { useSessionStore } from "@/stores/session";

const router = useRouter();
const session = useSessionStore();

const mode = ref<"login" | "student" | "register">("login");
const loginName = ref("");
const password = ref("");
const displayName = ref("");
const submitting = ref(false);

const submitText = computed(() =>
  mode.value === "register" ? "注 册" : mode.value === "student" ? "学生登录" : "登 录"
);

function onModeChange(): void {
  password.value = "";
}

async function onSubmit(): Promise<void> {
  submitting.value = true;
  try {
    if (mode.value === "student") {
      const data = await studentLogin(loginName.value, password.value);
      session.setAuth(data.token, data.student_name, "student");
      showToast(`欢迎，${data.student_name}`);
      router.replace("/tasks");
    } else if (mode.value === "login") {
      const data = await familyLogin(loginName.value, password.value);
      session.setAuth(data.token, loginName.value, "family");
      showToast("登录成功");
      router.replace("/tasks");
    } else {
      await familyRegister({
        login_name: loginName.value,
        password: password.value,
        display_name: displayName.value || loginName.value,
      });
      showToast("注册成功，请登录");
      mode.value = "login";
      password.value = "";
    }
  } catch (err) {
    toastError(err);
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.hint {
  margin: 12px 16px 0;
  font-size: 12px;
  color: var(--app-muted);
  line-height: 1.7;
}
</style>
