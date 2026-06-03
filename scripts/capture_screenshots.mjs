import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dirname, '../docs/presentation/screenshots');
mkdirSync(OUT, { recursive: true });

const FRONTEND = 'http://localhost:3000';
const API = 'http://localhost:8000';

async function shot(page, name, url, opts = {}) {
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: resolve(OUT, `${name}.png`), fullPage: opts.fullPage ?? true });
    console.log(`  ✓ ${name}.png`);
  } catch (e) {
    console.log(`  ✗ ${name}.png — ${e.message.split('\n')[0]}`);
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  // 1. API Health
  console.log('\n1. API Health');
  const apiPage = await ctx.newPage();
  await shot(apiPage, 'api-health', `${FRONTEND}/api-health`);

  // 2. Login page
  console.log('\n2. Login Page');
  const loginPage = await ctx.newPage();
  await shot(loginPage, 'login-page', `${FRONTEND}/login`);

  // 3. Signup page
  console.log('\n3. Signup Page');
  const signPage = await ctx.newPage();
  await shot(signPage, 'signup', `${FRONTEND}/signup`);

  // 4. Assessment workspace (authenticated)
  console.log('\n4. Assessment Workspace');
  const wsPage = await ctx.newPage();
  try {
    const demoKeyResp = await fetch(`${API}/api/v1/setup/demo-key`);
    if (demoKeyResp.ok) {
      const data = await demoKeyResp.json();
      const key = data.api_key || data.key;
      await wsPage.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
      await wsPage.evaluate((k) => { localStorage.setItem('rm_api_key', k); }, key);
    }
  } catch (e) { /* ignore */ }
  await shot(wsPage, 'assessment-workspace', `${FRONTEND}/`);

  // 5. History page
  console.log('\n5. History Page');
  const histPage = await ctx.newPage();
  await shot(histPage, 'history', `${FRONTEND}/history`);

  // 6. Analytics page
  console.log('\n6. Analytics Page');
  const anPage = await ctx.newPage();
  await shot(anPage, 'analytics', `${FRONTEND}/analytics`);

  // 7. Settings page
  console.log('\n7. Settings Page');
  const setPage = await ctx.newPage();
  await shot(setPage, 'settings', `${FRONTEND}/settings`);

  // 8. Admin dashboard
  console.log('\n8. Admin Dashboard');
  const adminPage = await ctx.newPage();
  await shot(adminPage, 'admin-dashboard', `${FRONTEND}/admin`);

  // 9. Knowledge graph
  console.log('\n9. Knowledge Graph');
  const kgPage = await ctx.newPage();
  await shot(kgPage, 'knowledge-graph', `${FRONTEND}/knowledge-graph`);

  // 10. Demo assessment report
  console.log('\n10. Demo Assessment Report');
  try {
    const demoResp = await fetch(`${API}/api/v1/demo/0`, { method: 'POST' });
    if (demoResp.ok) {
      const demo = await demoResp.json();
      const jobId = demo.job_id || demo.assessment_id;
      if (jobId) {
        const reportPage = await ctx.newPage();
        await shot(reportPage, 'report', `${FRONTEND}/reports/${jobId}`);
      }
    }
  } catch (e) { console.log('  Demo endpoint unavailable'); }

  // 11. Compare page
  console.log('\n11. Compare Page');
  const comparePage = await ctx.newPage();
  await shot(comparePage, 'compare', `${FRONTEND}/compare`);

  await browser.close();
  console.log('\n✅ All screenshots captured in docs/presentation/screenshots/');
}

main().catch(console.error);
