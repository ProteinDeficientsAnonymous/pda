import fs from 'node:fs/promises';
import { expect, type Page, test } from '@playwright/test';

import { shot, shotPath } from './shot';

const RED = 'rgb(255, 0, 0)';

async function withTempShot(name: string, run: () => Promise<void>) {
  try {
    await run();
  } finally {
    // The visual job uploads every file in screenshots/.
    await Promise.all(
      [name, `${name}-light`, `${name}-dark`].map((file) => fs.rm(shotPath(file), { force: true })),
    );
  }
}

async function columnHasRed(page: Page, name: string, x: number) {
  const base64 = (await fs.readFile(shotPath(name))).toString('base64');
  return page.evaluate(
    async ({ src, column }) => {
      const img = new Image();
      img.src = src;
      await img.decode();
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      if (!ctx) throw new Error('no 2d context');
      ctx.drawImage(img, 0, 0);
      const { data } = ctx.getImageData(column, 0, 1, img.height);
      for (let i = 0; i < data.length; i += 4) {
        const [r = 0, g = 0, b = 0] = data.subarray(i, i + 3);
        if (r > 200 && g < 50 && b < 50) return true;
      }
      return false;
    },
    { src: `data:image/png;base64,${base64}`, column: x },
  );
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

test('should drop the fixed nav from fullPage shots only', async ({ page }) => {
  await page.setContent(`
    <body style="margin: 0">
      <div style="height: 2400px"></div>
      <nav aria-label="primary" style="position: fixed; inset-inline: 0; bottom: 0; height: 40px; background: ${RED}"></nav>
    </body>
  `);
  const nav = page.getByRole('navigation', { name: 'primary' });
  await withTempShot('fixed-chrome-full', async () => {
    await shot(page, 'fixed-chrome-full', { fullPage: true, themes: false });
    expect(await columnHasRed(page, 'fixed-chrome-full', 10)).toBe(false);
    await expect(nav).toBeVisible();
  });
  await withTempShot('fixed-chrome-viewport', async () => {
    await shot(page, 'fixed-chrome-viewport', { themes: false });
    expect(await columnHasRed(page, 'fixed-chrome-viewport', 10)).toBe(true);
  });
});
