import { chromium } from 'playwright';

const FRONTEND = 'http://localhost:3000';
const API = 'http://localhost:8000';
const OUT = '/Users/ekeministephen/PycharmProjects/RetroMindAI/docs/presentation/screenshots';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  // Set API key in localStorage first
  const page = await ctx.newPage();
  await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => { localStorage.setItem('rm_api_key', 'dev-admin-key'); });
  await page.waitForTimeout(500);

  // Capture report page
  const jobId = '42bfceb3-b311-492c-bec0-7aba18e39728';
  await page.goto(`${FRONTEND}/reports/${jobId}`, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/report.png`, fullPage: true });
  console.log('  ✓ report.png');

  // Capture job assessment page
  await page.goto(`${FRONTEND}/history`, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/history-with-data.png`, fullPage: true });
  console.log('  ✓ history-with-data.png');

  await browser.close();
  console.log('Done');
}

main().catch(console.error);
