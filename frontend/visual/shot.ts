import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { type Page } from '@playwright/test';

const screenshotsDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../screenshots');

export async function shot(page: Page, name: string) {
  await page.screenshot({
    path: path.join(screenshotsDir, `${name}.png`),
    caret: 'hide',
  });
}
