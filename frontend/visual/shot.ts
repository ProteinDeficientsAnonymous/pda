import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { type Locator, type Page } from '@playwright/test';

const screenshotsDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../screenshots');

export async function shot(
  page: Page,
  name: string,
  options?: { locator?: Locator; fullPage?: boolean },
) {
  const file = path.join(screenshotsDir, `${name}.png`);
  if (options?.locator) {
    await options.locator.screenshot({ path: file, caret: 'hide' });
    return;
  }
  await page.screenshot({
    path: file,
    caret: 'hide',
    fullPage: options?.fullPage,
  });
}
