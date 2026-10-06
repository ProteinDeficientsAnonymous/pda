import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { chromium } from '@playwright/test';

const screenshotsDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../screenshots');
const outFile = path.join(screenshotsDir, 'login.png');

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1280, height: 800 },
  deviceScaleFactor: 1,
  locale: 'en-US',
  timezoneId: 'America/New_York',
  reducedMotion: 'reduce',
});

try {
  await page.goto('http://127.0.0.1:3000/login', { waitUntil: 'networkidle' });
  await page.getByRole('heading', { name: 'welcome back' }).waitFor();
  await mkdir(screenshotsDir, { recursive: true });
  await page.screenshot({ path: outFile, caret: 'hide' });
} finally {
  await browser.close();
}
