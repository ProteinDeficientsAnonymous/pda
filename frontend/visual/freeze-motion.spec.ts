import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

import { shot } from './shot';

const screenshotsDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../screenshots');

async function withTempShot(name: string, run: () => Promise<void>) {
  try {
    await run();
  } finally {
    // The visual job uploads every file in screenshots/.
    await fs.rm(path.join(screenshotsDir, `${name}.png`), { force: true });
  }
}

test('should use the settled color when a fade is running', async ({ page }) => {
  await page.setContent(
    '<button id="swatch" style="background-color: rgb(255, 0, 0); transition: background-color 30s linear">x</button>',
  );
  await page.locator('#swatch').evaluate((el) => {
    el.style.backgroundColor = 'rgb(0, 0, 255)';
  });
  await withTempShot('freeze-motion', async () => {
    await shot(page, 'freeze-motion', { themes: false });
    const color = await page
      .locator('#swatch')
      .evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(color).toBe('rgb(0, 0, 255)');
  });
});

test('should hide fixed bottom nav so fullPage stitches do not reprint it', async ({ page }) => {
  await page.setContent(`
    <div style="height: 2400px">tall</div>
    <nav aria-label="primary" style="position: fixed; inset-inline: 0; bottom: 0">nav</nav>
    <button aria-label="send feedback" style="position: fixed; right: 1rem; bottom: 4rem">?</button>
  `);
  await withTempShot('hide-fixed-chrome', async () => {
    await shot(page, 'hide-fixed-chrome', { fullPage: true, themes: false });
    await expect(page.getByRole('navigation', { name: 'primary' })).toBeHidden();
    await expect(page.getByRole('button', { name: 'send feedback' })).toBeHidden();
  });
});
