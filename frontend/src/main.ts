import { createPinia } from "pinia";
import { createApp } from "vue";
import Vant from "vant";

import App from "./App.vue";
import router from "./router";

import "vant/lib/index.css";
import "./styles/index.css";

// ADR-012：Vant 4 全量注册（各视图大量使用 van-* 组件，需全局组件表）。
const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(Vant);
app.mount("#app");
