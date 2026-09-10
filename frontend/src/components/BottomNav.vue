<template>
  <van-tabbar
    :model-value="active"
    active-color="#3b5bdb"
    inactive-color="#6b7486"
    safe-area-inset-bottom
    @change="onChange"
  >
    <van-tabbar-item name="tasks">
      <span class="nav-icon">📋</span>
      任务
    </van-tabbar-item>
    <van-tabbar-item name="photos">
      <span class="nav-icon">📄</span>
      作业
    </van-tabbar-item>
    <van-tabbar-item name="students">
      <span class="nav-icon">👧</span>
      学生
    </van-tabbar-item>
    <van-tabbar-item name="mine">
      <span class="nav-icon">👪</span>
      我的
    </van-tabbar-item>
  </van-tabbar>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const props = defineProps<{ active: "tasks" | "photos" | "students" | "mine" }>();
const router = useRouter();

function onChange(name: string | number): void {
  const key = String(name);
  if (key === props.active) return;
  router.push(key === "tasks" ? "/tasks" : `/${key}`);
}
</script>

<style scoped>
.nav-icon {
  font-size: 20px;
  line-height: 1;
}
</style>
