/* AI 作业评定 · M001 作业任务管理 前端（零构建 H5）
   与后端 /api/v1 契约对应（API-M001-001~012）。 */
"use strict";

const API = "/api/v1";
const STATUS_TEXT = { draft: "草稿", published: "已发布", in_progress: "进行中", closed: "已关闭" };
const STAGES = [
  { v: "primary", t: "小学" },
  { v: "junior", t: "初中" },
  { v: "senior", t: "高中" },
];
const SUBJECTS = [
  { v: "math", t: "数学" },
  { v: "chinese", t: "语文" },
  { v: "english", t: "英语" },
];
const STATE = { me: null, students: [], tasks: [], schools: [], schoolsByStage: {}, taskCache: {}, filter: { status: "", student_id: "" } };

class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function subjText(v) { return (SUBJECTS.find((s) => s.v === v) || { t: v }).t; }
function fmtTime(iso) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("zh-CN", { hour12: false });
}
function toast(msg, ms = 2200) {
  let el = document.querySelector(".toast");
  if (!el) { el = document.createElement("div"); el.className = "toast"; document.body.appendChild(el); }
  el.textContent = msg; el.classList.add("show");
  clearTimeout(el._t); el._t = setTimeout(() => el.classList.remove("show"), ms);
}

async function req(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = localStorage.getItem("at_token");
  if (auth && token) headers["Authorization"] = "Bearer " + token;
  const res = await fetch(API + path, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch (_) { /* 无 JSON */ }
  if (!res.ok) {
    if (res.status === 401 && auth) { localStorage.removeItem("at_token"); if (!location.hash.startsWith("#/login")) location.hash = "#/login"; }
    throw new ApiError((data && data.message) || `请求失败(${res.status})`, res.status);
  }
  return data;
}

async function loadSchools() {
  if (STATE.schools.length) return STATE.schools;
  const data = await req("/schools?page=1&page_size=100");
  STATE.schools = data.items;
  STATE.schoolsByStage = {};
  for (const s of STATE.schools) (STATE.schoolsByStage[s.stage] = STATE.schoolsByStage[s.stage] || []).push(s);
  return STATE.schools;
}
async function loadStudents() {
  STATE.students = await req("/students");
  return STATE.students;
}
async function loadTasks() {
  const q = new URLSearchParams({ page: "1", page_size: "100" });
  if (STATE.filter.status) q.set("status", STATE.filter.status);
  if (STATE.filter.student_id) q.set("student_id", STATE.filter.student_id);
  const data = await req("/tasks?" + q.toString());
  return data.items;
}

/* ================= 路由渲染 ================= */
const appEl = () => document.getElementById("app");

function navBar(active) {
  const items = [
    ["tasks", "任务", "📋"],
    ["students", "学生", "👧"],
    ["mine", "我的", "👪"],
  ];
  return `<nav class="bottom-nav">${items
    .map(([key, t, icon]) => `<button class="${active === key ? "active" : ""}" data-nav="${key}">${icon}<span>${t}</span></button>`)
    .join("")}</nav>`;
}

window.addEventListener("hashchange", route);
window.addEventListener("load", () => { route(); });

async function route() {
  const app = appEl();
  const path = location.hash.replace(/^#\/?/, "") || "tasks";
  try {
    if (!localStorage.getItem("at_token")) { renderLogin(app); return; }
    if (path === "login") { location.hash = "#/tasks"; return; }
    const [name, id] = path.split("/");
    if (name === "tasks" && id === "new") await renderTaskEditor(app, null);
    else if (name === "tasks" && id) await renderTaskDetail(app, id);
    else if (name === "tasks") await renderTaskList(app);
    else if (name === "students") await renderStudents(app);
    else if (name === "mine") renderMine(app);
    else { location.hash = "#/tasks"; }
  } catch (e) {
    if (!(e instanceof ApiError)) { console.error(e); toast("页面加载失败，请重试"); }
  }
}

function renderLogin(app) {
  app.innerHTML = `
  <div class="auth-wrap card">
    <div class="brand">
      <div class="logo">📚</div>
      <h1>AI 作业智能评定</h1>
      <p>家长（家庭）账号 · 作业任务管理</p>
    </div>
    <div class="tabs"><button id="tab-login" class="active">登录</button><button id="tab-reg">注册</button></div>
    <form id="auth-form">
      <label>登录名</label><input name="login_name" required minlength="3" placeholder="邮箱 / 手机号 / 自定义" autocomplete="username" />
      <label>密码</label><input name="password" type="password" required minlength="8" autocomplete="current-password" />
      <div id="reg-extra" class="hidden"><label>家庭显示名</label><input name="display_name" maxlength="32" placeholder="如：小明一家" /></div>
      <div style="height:14px"></div>
      <button class="btn block" type="submit">登 录</button>
    </form>
  </div>`;
  const mode = { now: "login" };
  const tabLogin = app.querySelector("#tab-login");
  const tabReg = app.querySelector("#tab-reg");
  const extra = app.querySelector("#reg-extra");
  tabLogin.onclick = () => { mode.now = "login"; tabLogin.classList.add("active"); tabReg.classList.remove("active"); extra.classList.add("hidden"); };
  tabReg.onclick = () => { mode.now = "reg"; tabReg.classList.add("active"); tabLogin.classList.remove("active"); extra.classList.remove("hidden"); };
  app.querySelector("#auth-form").onsubmit = async (ev) => {
    ev.preventDefault();
    const f = new FormData(ev.target);
    const btn = ev.target.querySelector("button"); btn.disabled = true;
    try {
      if (mode.now === "login") {
        const data = await req("/family/login", { method: "POST", body: { login_name: f.get("login_name"), password: f.get("password") }, auth: false });
        localStorage.setItem("at_token", data.token);
        localStorage.setItem("at_login", f.get("login_name"));
        toast("登录成功");
        location.hash = "#/tasks";
      } else {
        await req("/family/register", { method: "POST", body: { login_name: f.get("login_name"), password: f.get("password"), display_name: f.get("display_name") || f.get("login_name") }, auth: false });
        toast("注册成功，请登录");
        tabLogin.click();
      }
    } catch (e) { toast(e.message); btn.disabled = false; }
  };
}

/* ================= 任务列表 ================= */
async function renderTaskList(app) {
  if (!STATE.students.length) await loadStudents();
  STATE.tasks = await loadTasks();
  const studentsById = Object.fromEntries(STATE.students.map((s) => [s.student_id, s]));
  const statusOpts = ["", "draft", "published", "in_progress", "closed"].map((v) => `<option value="${v}" ${STATE.filter.status === v ? "selected" : ""}>${v ? STATUS_TEXT[v] : "全部状态"}</option>`).join("");
  const studentOpts = `<option value="">全部学生</option>` + STATE.students.map((s) => `<option value="${s.student_id}" ${STATE.filter.student_id === s.student_id ? "selected" : ""}>${esc(s.name)}</option>`).join("");
  const rows = STATE.tasks.length ? STATE.tasks.map((t) => {
    const st = studentsById[t.student_id];
    return `<div class="card row" style="align-items:flex-start">
      <div class="body" data-task="${t.task_id}" style="cursor:pointer">
        <div class="title">${esc(t.title)}</div>
        <div class="sub">${esc(st ? st.name : "")} · ${subjText(t.subject)}${t.item_count ? " · " + t.item_count + " 题" : ""} · 截止 ${fmtTime(t.deadline)}</div>
      </div>
      <span class="badge ${t.status}">${STATUS_TEXT[t.status]}</span>
    </div>`;
  }).join("") : `<div class="card empty">还没有任务，点右下角 + 创建第一条作业任务</div>`;
  app.innerHTML = `
    <div class="topbar"><h1>作业任务</h1></div>
    <div class="card"><div class="grid2">
      <div><label style="margin-top:0">状态</label><select id="f-status">${statusOpts}</select></div>
      <div><label style="margin-top:0">学生</label><select id="f-student">${studentOpts}</select></div>
    </div></div>
    ${rows}
    <button class="fab" id="fab-new">＋</button>
    ${navBar("tasks")}`;
  app.querySelector("#f-status").onchange = (e) => { STATE.filter.status = e.target.value; renderTaskList(app); };
  app.querySelector("#f-student").onchange = (e) => { STATE.filter.student_id = e.target.value; renderTaskList(app); };
  app.querySelector("#fab-new").onclick = () => (location.hash = "#/tasks/new");
  app.querySelectorAll("[data-task]").forEach((el) => (el.onclick = () => (location.hash = "#/tasks/" + el.dataset.task)));
  bindNav(app);
}

/* ================= 任务编辑器（新建/编辑共用） ================= */
function itemRow(it, idx) {
  const typeOpts = `<option value="objective" ${it.item_type === "objective" ? "selected" : ""}>客观题（判对错）</option><option value="subjective" ${it.item_type === "subjective" ? "selected" : ""}>主观题（只评质量）</option>`;
  const subjOpts = SUBJECTS.map((s) => `<option value="${s.v}" ${it.subject === s.v ? "selected" : ""}>${s.t}</option>`).join("");
  return `<div class="item-editor" data-idx="${idx}">
    <div class="muted" style="font-size:13px;font-weight:700">第 ${idx + 1} 题</div>
    <div class="grid2">
      <div><label>题型</label><select name="type">${typeOpts}</select></div>
      <div><label>学科</label><select name="subject">${subjOpts}</select></div>
    </div>
    <label>题干</label><textarea name="stem" rows="2" maxlength="2000" required placeholder="如：12 × 8 = ？">${esc(it.stem)}</textarea>
    <div class="answer-field"><label>参考答案（仅客观题可填，主观题勿填）</label><textarea name="answer" rows="1" maxlength="2000" placeholder="选填">${esc(it.reference_answer || "")}</textarea></div>
    <button type="button" class="remove-item">删除本题</button>
  </div>`;
}

async function renderTaskEditor(app, existing) {
  const students = await loadStudents();
  if (!students.length) {
    toast("请先创建学生档案");
    location.hash = "#/students";
    return;
  }
  const studentOpts = students.map((s) => `<option value="${s.student_id}" ${existing && existing.student_id === s.student_id ? "selected" : ""}>${esc(s.name)}</option>`).join("");
  const subjOpts = SUBJECTS.map((s) => `<option value="${s.v}" ${existing && existing.subject === s.v ? "selected" : ""}>${s.t}</option>`).join("");
  let items = [];
  if (existing) items = (existing.items || []).map((i) => ({ ...i, reference_answer: i.reference_answer || "" }));
  if (!items.length) items = [{ seq: 1, item_type: "objective", subject: "math", stem: "", reference_answer: "" }];

  app.innerHTML = `
    <div class="topbar"><button class="back" id="back">← 返回</button><h1>${existing ? "编辑任务" : "新建任务"}</h1></div>
    <form id="task-form" class="card">
      <label>标题</label><input name="title" maxlength="64" required value="${esc(existing ? existing.title : "")}" placeholder="如：数学口算 20 题" />
      <div class="grid2">
        <div><label>学生</label><select name="student_id" ${existing ? "disabled" : ""}>${studentOpts}</select></div>
        <div><label>学科</label><select name="subject" ${existing ? "disabled" : ""}>${subjOpts}</select></div>
      </div>
      <div class="grid2">
        <div><label>年级/学段（可选）</label><input name="grade_level" maxlength="64" value="${esc(existing ? existing.grade_level || "" : "")}" placeholder="如：三年级" /></div>
        <div><label>截止时间（可选）</label><input name="deadline" type="datetime-local" value="${existing && existing.deadline ? localInputValue(existing.deadline) : ""}" /></div>
      </div>
      <label>作业内容描述（可选）</label><textarea name="content" rows="2" maxlength="2000" placeholder="如：课本 P23 练习">${esc(existing ? existing.content || "" : "")}</textarea>
      <h2 class="section">题目清单（至少 1 题）</h2>
      <div id="items"></div>
      <button type="button" class="btn outline block" id="add-item">＋ 添加一题</button>
      <div style="height:14px"></div>
      <button class="btn block" type="submit">${existing ? "保存修改" : "保存草稿"}</button>
    </form>`;

  const itemsBox = app.querySelector("#items");
  function renderItems() {
    itemsBox.innerHTML = items.map(itemRow).join("");
    itemsBox.querySelectorAll(".item-editor").forEach((el, i) => {
      const typeSel = el.querySelector('select[name="type"]');
      const answerBox = el.querySelector(".answer-field");
      function syncAnswer() { answerBox.classList.toggle("hidden", typeSel.value !== "objective"); }
      typeSel.onchange = syncAnswer; syncAnswer();
      el.querySelector(".remove-item").onclick = () => { items.splice(i, 1); if (!items.length) items.push(blankItem(items)); renderItems(); };
    });
  }
  function blankItem() { return { seq: 0, item_type: "objective", subject: SUBJECTS[0].v, stem: "", reference_answer: "" }; }
  renderItems();
  app.querySelector("#add-item").onclick = () => { items.push(blankItem()); renderItems(); };
  app.querySelector("#back").onclick = () => (location.hash = existing ? "#/tasks/" + existing.task_id : "#/tasks");

  app.querySelector("#task-form").onsubmit = async (ev) => {
    ev.preventDefault();
    const f = new FormData(ev.target);
    const itemData = [];
    const editors = [...app.querySelectorAll(".item-editor")];
    for (let i = 0; i < editors.length; i++) {
      const el = editors[i];
      const type = el.querySelector('select[name="type"]').value;
      const answer = el.querySelector('textarea[name="answer"]').value.trim();
      if (type === "subjective") { if (answer) { toast(`第 ${i + 1} 题为主观题，不能录入参考答案`); return; } }
      itemData.push({ seq: i + 1, item_type: type, subject: el.querySelector('select[name="subject"]').value, stem: el.querySelector('textarea[name="stem"]').value, reference_answer: type === "objective" ? answer || null : null });
    }
    const deadlineRaw = f.get("deadline");
    const deadline = deadlineRaw ? new Date(deadlineRaw).toISOString() : null;
    const payload = { title: f.get("title"), student_id: existing ? existing.student_id : f.get("student_id"), subject: existing ? existing.subject : f.get("subject"), grade_level: f.get("grade_level") || null, content: f.get("content") || null, deadline, items: itemData };
    const btn = ev.target.querySelector("button[type=submit]"); btn.disabled = true;
    try {
      const saved = existing
        ? await req("/tasks/" + existing.task_id, { method: "PATCH", body: { title: payload.title, content: payload.content, deadline: payload.deadline, items: payload.items } })
        : await req("/tasks", { method: "POST", body: payload });
      STATE.taskCache[saved.task_id] = saved;
      toast(existing ? "已保存" : "草稿已保存");
      location.hash = "#/tasks/" + saved.task_id;
    } catch (e) { toast(e.message); btn.disabled = false; }
  };
}

function localInputValue(iso) {
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/* ================= 任务详情 ================= */
async function renderTaskDetail(app, taskId) {
  // 详情/编辑视角：属主家庭内可见参考答案（include_answers 归属校验在后端）。
  // 列表摘要不含参考答案；详情页始终携带 include_answers=true 以支持草稿/已发布编辑回填。
  const t = await req(`/tasks/${taskId}?include_answers=true`);
  STATE.taskCache[taskId] = t;
  const canEdit = t.status === "draft" || t.status === "published";
  const actions = [];
  if (t.status === "draft") actions.push(`<button class="btn" data-act="publish">发布任务</button>`);
  if (canEdit) actions.push(`<button class="btn ghost" data-act="edit">编辑</button>`);
  if (t.status === "published" || t.status === "in_progress") actions.push(`<button class="btn outline" data-act="close">关闭任务</button>`);
  if (t.status === "closed") actions.push(`<button class="btn ghost" data-act="reopen">重新发布</button>`);
  const itemsHtml = t.items.map((it, i) => `<div class="item-card">
      <div class="tag"><span class="badge ${it.item_type}">${it.item_type === "objective" ? "客观题" : "主观题"}</span> <span class="chip">${subjText(it.subject)}</span></div>
      <div class="q">${i + 1}. ${esc(it.stem)}</div>
      ${it.reference_answer ? `<div class="answer">参考答案：${esc(it.reference_answer)}</div>` : it.item_type === "objective" ? `<div class="muted" style="font-size:12px">客观题未录入参考答案（默认不判对错）</div>` : ""}
    </div>`).join("");
  app.innerHTML = `
    <div class="topbar"><button class="back" id="back">← 返回</button><h1>任务详情</h1></div>
    <div class="card">
      <div style="display:flex;align-items:center;gap:8px"><h2 style="margin:0;font-size:18px;flex:1">${esc(t.title)}</h2><span class="badge ${t.status}">${STATUS_TEXT[t.status]}</span></div>
      <div class="muted" style="margin-top:8px;font-size:13px">学科 ${subjText(t.subject)}${t.grade_level ? " · " + esc(t.grade_level) : ""} · ${t.items.length} 题 · 截止 ${fmtTime(t.deadline)} · 创建 ${fmtTime(t.created_at)}</div>
      ${t.content ? `<div style="margin-top:10px">${esc(t.content)}</div>` : ""}
      <div class="actions">${actions.join("")}</div>
    </div>
    <div class="detail-block">${itemsHtml}</div>
    ${navBar("tasks")}`;
  app.querySelector("#back").onclick = () => (location.hash = "#/tasks");
  const actBtn = app.querySelector('[data-act="edit"]');
  if (actBtn) actBtn.onclick = () => renderTaskEditor(app, t);
  const pub = app.querySelector('[data-act="publish"]');
  if (pub) pub.onclick = () => confirmAction("publish", "确定发布该任务？发布后即可开始上传。");
  const closeBtn = app.querySelector('[data-act="close"]');
  if (closeBtn) closeBtn.onclick = () => confirmAction("close", "确定关闭该任务？关闭后不可再上传或修改。");
  const reopen = app.querySelector('[data-act="reopen"]');
  if (reopen) reopen.onclick = () => confirmAction("reopen", "确定重新发布该任务？");
  async function confirmAction(action, msg) {
    if (!confirm(msg)) return;
    try {
      const data = await req(`/tasks/${taskId}/status`, { method: "POST", body: { action } });
      toast("状态已更新：" + STATUS_TEXT[data.status]);
      delete STATE.taskCache[taskId];
      renderTaskDetail(app, taskId);
    } catch (e) { toast(e.message); }
  }
  bindNav(app);
}

/* ================= 学生档案 ================= */
async function renderStudents(app) {
  const students = await loadStudents();
  await loadSchools();
  const rows = students.map((s) => `<div class="row">
      <div class="body"><div class="title">${esc(s.name)}</div>
      <div class="sub">${esc(s.school.name)}（${stageText(s.school.stage)}）${s.grade_level ? " · " + esc(s.grade_level) : ""}${s.relation ? " · " + esc(s.relation) : ""}</div></div>
      <button class="btn outline small" data-edit="${s.student_id}">编辑</button>
    </div>`).join("") || `<div class="card empty">还没有学生档案，先添加一位学生</div>`;

  app.innerHTML = `
    <div class="topbar"><h1>学生档案</h1></div>
    ${rows}
    <div class="card" id="form-card">
      <h2 class="section" style="margin-top:0" id="form-title">添加学生</h2>
      <form id="student-form">
        <div class="grid2">
          <div><label>姓名</label><input name="name" maxlength="32" required placeholder="学生姓名" /></div>
          <div><label>与账号关系（可选）</label><input name="relation" maxlength="16" placeholder="如：儿子" /></div>
        </div>
        <div class="grid2">
          <div><label>学段</label><select id="stage-select"></select></div>
          <div><label>学校（必选）</label><select name="school_id" required><option value="">请先选择学段</option></select></div>
        </div>
        <label>年级/班级（可选）</label><input name="grade_level" maxlength="64" placeholder="如：三年级 1 班" />
        <div style="height:14px"></div>
        <button class="btn block" type="submit">保存学生档案</button>
        <button type="button" class="hidden" id="cancel-edit">取消编辑</button>
      </form>
    </div>
    ${navBar("students")}`;

  const stageSel = app.querySelector("#stage-select");
  const schoolSel = app.querySelector('select[name="school_id"]');
  stageSel.innerHTML = STAGES.map((s) => `<option value="${s.v}">${s.t}</option>`).join("");
  function renderSchools(stage) {
    const list = STATE.schoolsByStage[stage] || [];
    schoolSel.innerHTML = list.map((sc) => `<option value="${sc.school_id}">${esc(sc.name)}</option>`).join("");
  }
  stageSel.onchange = () => renderSchools(stageSel.value);
  renderSchools(stageSel.value);

  let editingId = null;
  const formTitle = app.querySelector("#form-title");
  const cancelBtn = app.querySelector("#cancel-edit");
  function fillForm(s) {
    if (!s) return;
    editingId = s.student_id;
    formTitle.textContent = "编辑学生";
    cancelBtn.classList.remove("hidden");
    app.querySelector('input[name="name"]').value = s.name;
    app.querySelector('input[name="relation"]').value = s.relation || "";
    app.querySelector('input[name="grade_level"]').value = s.grade_level || "";
    stageSel.value = s.school.stage; renderSchools(s.school.stage);
    schoolSel.value = s.school.school_id;
  }
  app.querySelectorAll("[data-edit]").forEach((b) => (b.onclick = () => fillForm(students.find((s) => s.student_id === b.dataset.edit))));
  cancelBtn.onclick = () => { editingId = null; formTitle.textContent = "添加学生"; cancelBtn.classList.add("hidden"); app.querySelector("#student-form").reset(); };

  app.querySelector("#student-form").onsubmit = async (ev) => {
    ev.preventDefault();
    const f = new FormData(ev.target);
    const payload = { name: f.get("name"), relation: f.get("relation") || null, grade_level: f.get("grade_level") || null, school_id: f.get("school_id") };
    const btn = ev.target.querySelector("button[type=submit]"); btn.disabled = true;
    try {
      if (editingId) await req("/students/" + editingId, { method: "PATCH", body: payload });
      else await req("/students", { method: "POST", body: payload });
      toast("已保存");
      renderStudents(app);
    } catch (e) { toast(e.message); btn.disabled = false; }
  };
  bindNav(app);
}

function stageText(v) { return (STAGES.find((s) => s.v === v) || { t: v }).t; }

/* ================= 我的 ================= */
function renderMine(app) {
  const login = localStorage.getItem("at_login") || "家庭账号";
  app.innerHTML = `
    <div class="topbar"><h1>我的</h1></div>
    <div class="card"><div class="row" style="border:none">
      <div style="width:46px;height:46px;border-radius:50%;background:var(--primary-soft);color:var(--primary);display:flex;align-items:center;justify-content:center;font-size:22px">👪</div>
      <div class="body"><div class="title">${esc(login)}</div><div class="sub">家庭模式 · 数据家庭内隔离</div></div>
    </div></div>
    <div class="card">
      <div class="muted" style="font-size:13px;line-height:1.8">· 任务发布后学生即可开始拍照上传（M002）<br />· 已发布且未开始上传的任务仍可编辑题目<br />· 学校字典为系统预置公共数据</div>
    </div>
    <div style="height:14px"></div>
    <button class="btn danger block" id="logout">退出登录</button>
    ${navBar("mine")}`;
  app.querySelector("#logout").onclick = async () => {
    try { await req("/family/logout", { method: "POST" }); } catch (_) { /* 忽略 */ }
    localStorage.removeItem("at_token");
    location.hash = "#/login";
  };
  bindNav(app);
}

function bindNav(app) {
  app.querySelectorAll("[data-nav]").forEach((b) => (b.onclick = () => (location.hash = "#/" + b.dataset.nav)));
}
