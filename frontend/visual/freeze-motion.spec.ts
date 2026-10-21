import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

import { shot } from './shot';

const shotFile = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../screenshots/freeze-motion.png',
);

test('should use the settled color when a fade is running', async ({ page }) => {
  await page.setContent(
    '<button id="swatch" style="background-color: rgb(255, 0, 0); transition: background-color 30s linear">x</button>',
  );
  await page.locator('#swatch').evaluate((el) => {
    el.style.backgroundColor = 'rgb(0, 0, 255)';
  });
  try {
    await shot(page, 'freeze-motion', { themes: false });
    const color = await page
      .locator('#swatch')
      .evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(color).toBe('rgb(0, 0, 255)');
  } finally {
    // The visual job uploads every file in screenshots/.
    await fs.rm(shotFile, { force: true });
  }
});
