/**
 * Task-011 / Task-014 ④ 浏览器级验收（Edge + playwright-core，真实服务 + dist 托管）。
 *
 * 覆盖：
 *  - 剧本 7：任务列表页筛选请求不再 422（Network 原文）
 *  - 剧本 1~3：窗口分组（day / weekend）与归属日在真实响应体中的呈现
 *  - 剧本 5（Task-014 去替身复审版）：3 张作业照片经**真实 AI 装配路径**（app/core/ai → Mock
 *    Provider，`mock=True`，非三方联调）产出挂接建议 → UI 呈现「AI 建议：…」并自动填充目标 →
 *    逐张采纳建议（确认挂接）→ 门控满足 → 生成完成分析草稿 → 家长确认
 *  - 剧本 6：AI 建议采纳后「手工挂接」兜底入口（B6）仍可用（API 面手工挂接见
 *    tests/e2e/test_acceptance_scenarios.py::test_scenario6_*）
 *
 * 证据分域：本文件全部为**浏览器级**（Playwright UI 交互 + Network 原文 + 截图）；
 * API/服务级证据在 pytest 用例（`tests/e2e/`、`tests/integration/`），两域不得混同。
 *
 * 产出：.e2e/shots/*.png（截图）+ .e2e/browser_evidence.json（Network 摘要 + 断言）
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

const BASE = process.env.AT_BASE || 'http://127.0.0.1:8010';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const SHOTS = path.join(HERE, 'shots');
fs.mkdirSync(SHOTS, { recursive: true });

const records = [];
const pending = [];
const checks = [];
const notes = [];

function check(name, ok, detail) {
  checks.push({ name, ok: Boolean(ok), detail });
  console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${detail ? ` | ${detail}` : ''}`);
}

function attach(page) {
  page.on('response', (res) => {
    const url = res.url();
    if (!url.includes('/api/v1/')) return;
    const p = (async () => {
      const ct = res.headers()['content-type'] || '';
      let body;
      try {
        if (ct.includes('json')) body = await res.json();
        else if (ct.startsWith('image/') || ct.includes('octet-stream')) body = `<binary ${ct}>`;
        else body = `<${ct || 'unknown'}>`;
      } catch {
        body = '<unreadable>';
      }
      records.push({
        method: res.request().method(),
        url: url.replace(BASE, ''),
        status: res.status(),
        body,
      });
    })();
    pending.push(p);
  });
}

function lastRecord(method, urlPart) {
  return [...records].reverse().find((r) => r.method === method && r.url.includes(urlPart));
}

/** 精确匹配「列表接口」：`/api/v1/photos?` 与 `/api/v1/tasks?`（排除 /photos/{id}/content 等）。 */
function firstListRecord(urlPart) {
  return records.find((r) => r.method === 'GET' && r.url.startsWith(urlPart));
}

const browser = await chromium.launch({ channel: 'msedge', headless: true });
const ctx = await browser.newContext({ viewport: { width: 420, height: 920 } });
const page = await ctx.newPage();
page.setDefaultTimeout(15000);
attach(page);

try {
  // ---------- 登录（UI） ----------
  await page.goto(`${BASE}/#/login`, { waitUntil: 'networkidle' });
  await page.fill('input[name="login_name"]', 'acceptance');
  await page.fill('input[name="password"]', 'acceptance123');
  await page.locator('button[type="submit"]').click();
  await page.waitForURL('**/#/tasks', { timeout: 15000 });
  await page.waitForTimeout(1200);

  const loginRec = lastRecord('POST', '/family/login');
  check('UI 家长登录成功', loginRec && loginRec.status === 200, 'POST /family/login ' + (loginRec && loginRec.status));

  // ---------- 剧本 7：任务列表页不再 422 ----------
  await page.waitForSelector('h1');
  const tasksH1 = (await page.locator('h1').first().textContent())?.trim();
  const taskListRec = firstListRecord('/api/v1/tasks?');
  check(
    '剧本7 任务列表页 GET /tasks 非 422',
    taskListRec && taskListRec.status === 200,
    `GET ${taskListRec && taskListRec.url} → ${taskListRec && taskListRec.status}`
  );
  const taskCount = Array.isArray(taskListRec?.body?.items) ? taskListRec.body.items.length : -1;
  check('剧本7 列表页渲染任务条数 = 4', taskCount === 4, `items=${taskCount}`);

  // 筛选交互（原先空串会 422）：切换状态筛选触发请求
  const statusSelect = page.locator('.filter-grid select').first();
  await statusSelect.selectOption('published');
  await page.waitForTimeout(800);
  const filteredRec = lastRecord('GET', '/tasks?');
  check(
    '剧本7 状态筛选请求非 422',
    filteredRec && filteredRec.status === 200,
    `GET ${filteredRec && filteredRec.url} → ${filteredRec && filteredRec.status}`
  );
  await statusSelect.selectOption('');
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(SHOTS, '01_tasks.png'), fullPage: true });
  notes.push(`任务列表页标题=${tasksH1}`);

  // ---------- 作业域（剧本 1~3 / 5 / 6） ----------
  await page.goto(`${BASE}/#/photos`);
  await page.waitForTimeout(2000);

  const groupsRec = lastRecord('GET', '/task-groups');
  const groups = Array.isArray(groupsRec?.body?.items) ? groupsRec.body.items : [];
  const dayGroup = groups.find((g) => g.window_type === 'day');
  const weekendGroup = groups.find((g) => g.window_type === 'weekend');
  check('剧本1 存在 day 窗口聚合（group_key=归属日）', Boolean(dayGroup), JSON.stringify(dayGroup && { group_key: dayGroup.group_key, display_name: dayGroup.display_name }));
  check('剧本2 存在 weekend 窗口聚合（周五~周日合并）', Boolean(weekendGroup && weekendGroup.group_key === 'W:2026-09-11'), JSON.stringify(weekendGroup && { group_key: weekendGroup.group_key, display_name: weekendGroup.display_name, subjects: (weekendGroup.subjects || []).map((s) => s.subject) }));
  check('剧本1/2 窗口显示名正确（09-10 周四 / 周末作业）', dayGroup?.display_name === '09-10 周四' && weekendGroup?.display_name === '周末作业', `${dayGroup?.display_name} | ${weekendGroup?.display_name}`);

  const daySubject = (dayGroup?.subjects || [])[0];
  check('剧本3 聚合学科子任务携带 policy_version', Boolean(dayGroup?.policy_version), String(dayGroup?.policy_version));

  const photosRec = firstListRecord('/api/v1/photos?');
  const photos = Array.isArray(photosRec?.body?.items) ? photosRec.body.items : [];
  const photosWithSuggestion = photos.filter(
    (p) =>
      (p.links || []).some((l) => l.source === 'ai' && !l.confirmed_at && !l.rejected_at)
  );
  check(
    '剧本5 3 张作业照片经真实 AI 通路产出挂接建议（link.source=ai 未确认）',
    photos.length === 3 && photosWithSuggestion.length === 3,
    `n=${photos.length} withAiSuggestion=${photosWithSuggestion.length} status=${photos.map((p) => p.status).join(',')} aiLinks=${photos.map((p) => (p.links || []).filter((l) => l.source === 'ai' && !l.confirmed_at).length).join(',')}`
  );

  const suggestLines = await page.locator('.suggest-line', { hasText: 'AI 建议' }).count();
  const acceptBtns = await page.getByRole('button', { name: '采纳建议' }).count();
  check('剧本5 UI 呈现 AI 挂接建议（自动填充目标）', suggestLines >= 3, `suggest-line=${suggestLines}`);
  check('剧本5 UI 呈现「采纳建议」入口', acceptBtns > 0, `acceptBtn=${acceptBtns}`);
  await page.screenshot({ path: path.join(SHOTS, '02_photos_ai_suggested.png'), fullPage: true });

  // ---------- 剧本 5：逐张采纳 AI 建议（确认挂接）----------
  let acceptClicks = 0;
  for (let i = 0; i < 12; i += 1) {
    const btn = page.getByRole('button', { name: '采纳建议' }).first();
    if ((await btn.count()) === 0) break;
    await btn.click();
    acceptClicks += 1;
    await page.waitForTimeout(900);
  }
  const linkRecs = records.filter((r) => r.method === 'POST' && /\/photos\/[^/]+\/links$/.test(r.url));
  check(
    '剧本5 逐张采纳 AI 建议（全部 200）',
    acceptClicks > 0 && linkRecs.length === acceptClicks && linkRecs.every((r) => r.status === 200),
    `clicks=${acceptClicks} posts=${linkRecs.length} status=[${linkRecs.map((r) => r.status).join(',')}]`
  );

  const photosAfterRec = lastRecord('GET', '/api/v1/photos?');
  const photosAfter = Array.isArray(photosAfterRec?.body?.items) ? photosAfterRec.body.items : [];
  check(
    '剧本5 3 张照片全部已确认挂接',
    photosAfter.length === 3 &&
      photosAfter.every((p) => p.status === 'assigned' && (p.links || []).some((l) => l.confirmed_at)),
    `status=${photosAfter.map((p) => p.status).join(',')}`
  );

  const gateRec = lastRecord('GET', '/photo-gates');
  const allGates = Array.isArray(gateRec?.body) ? gateRec.body : [];
  const targetGate = allGates.find(
    (g) => g.total_photos === 3 && g.pending_photos === 0 && g.satisfied === true
  );
  check('剧本5 门控满足（total=3 / pending=0 / satisfied）', Boolean(targetGate), JSON.stringify(allGates));

  const manualBtns = await page.getByRole('button', { name: /挂接到|追加挂接/ }).count();
  check('剧本6 手工挂接兜底入口仍可用（B6）', manualBtns > 0, `manual=${manualBtns}`);
  await page.screenshot({ path: path.join(SHOTS, '03_photos_assigned.png'), fullPage: true });

  // ---------- 剧本 5：生成分析草稿 → 家长确认 ----------
  await page.getByRole('button', { name: '生成分析' }).first().click();
  await page.waitForTimeout(1500);
  const genRec = lastRecord('POST', '/completion-analyses');
  check('剧本5 生成完成分析草稿 201', genRec && genRec.status === 201, `POST /completion-analyses → ${genRec && genRec.status} ${JSON.stringify(genRec?.body)?.slice(0, 400)}`);
  check('剧本5 草稿 status=draft 且带 evidence_photo_ids', Boolean(genRec?.body?.items?.length && genRec.body.items.every((x) => x.status === 'draft' && x.evidence_photo_ids.length === 3)), JSON.stringify(genRec?.body?.items?.map((x) => ({ status: x.status, evidence: x.evidence_photo_ids.length, conclusion: x.conclusion }))));

  await page.locator('.analysis-item button', { hasText: '确认' }).first().click();
  await page.waitForTimeout(600);
  await page.locator('.van-popup button', { hasText: '确认结论' }).first().click();
  await page.waitForTimeout(1500);
  const confirmRec = lastRecord('POST', '/confirmation');
  check('剧本5 确认结论成功（回写判定单元）', confirmRec && confirmRec.status === 200, `POST .../confirmation → ${confirmRec && confirmRec.status}`);
  await page.screenshot({ path: path.join(SHOTS, '04_analysis_confirmed.png'), fullPage: true });
} catch (err) {
  check('浏览器级验收脚本异常', false, String(err && err.stack ? err.stack : err));
} finally {
  await Promise.allSettled(pending);
  const evidence = {
    base: BASE,
    generated_at: new Date().toISOString(),
    checks,
    notes,
    network: records,
  };
  fs.writeFileSync(path.join(HERE, 'browser_evidence.json'), JSON.stringify(evidence, null, 2), 'utf-8');
  await browser.close();
  const failed = checks.filter((c) => !c.ok);
  console.log(`\nCHECKS total=${checks.length} pass=${checks.length - failed.length} fail=${failed.length}`);
  console.log('EVIDENCE_WRITTEN');
  if (failed.length) process.exitCode = 1;
}
