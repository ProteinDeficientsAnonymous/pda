import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { type Locator, type Page } from '@playwright/test';

const screenshotsDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../screenshots');

interface ShotOptions {
  locator?: Locator;
  fullPage?: boolean;
  themes?: boolean;
}

async function freezeMotion(page: Page) {
  // Tailwind `transition-colors` ignores reduced motion, so a theme switch
  // is still fading when the screenshot is taken.
  await page.addStyleTag({
    content: '*, *::before, *::after { animation: none !important; transition: none !important; }',
  });
}

async function writeShot(page: Page, name: string, options?: ShotOptions) {
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

export async function shot(page: Page, name: string, options?: ShotOptions) {
  await freezeMotion(page);
  if (options?.themes === false) {
    await writeShot(page, name, options);
    return;
  }
  for (const theme of ['light', 'dark'] as const) {
    await page.emulateMedia({ reducedMotion: 'reduce', colorScheme: theme });
    await page.locator(`html.${theme}`).waitFor({ state: 'attached' });
    await writeShot(page, `${name}-${theme}`, options);
  }
}
