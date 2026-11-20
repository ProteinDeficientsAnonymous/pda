import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { type Locator, type Page } from '@playwright/test';

const screenshotsDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../screenshots');

// Tailwind `transition-colors` ignores reduced motion, so a theme switch is still fading at capture.
const FREEZE_MOTION =
  '*, *::before, *::after { animation: none !important; transition: none !important; }';
// fullPage and element captures paint position:fixed chrome at its viewport offset, over content.
const HIDE_FIXED_CHROME =
  'nav[aria-label="primary"], button[aria-label="send feedback"] { display: none !important; }';
const FREEZE_MOTION_ID = 'visual-freeze-motion';

interface ShotOptions {
  locator?: Locator;
  fullPage?: boolean;
  themes?: boolean;
}

export function shotPath(name: string) {
  return path.join(screenshotsDir, `${name}.png`);
}

async function freezeMotion(page: Page) {
  if (await page.locator(`#${FREEZE_MOTION_ID}`).count()) return;
  const tag = await page.addStyleTag({ content: FREEZE_MOTION });
  await tag.evaluate((el, id) => {
    (el as HTMLStyleElement).id = id;
  }, FREEZE_MOTION_ID);
}

async function writeShot(page: Page, name: string, options?: ShotOptions) {
  const file = shotPath(name);
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

async function writeShots(page: Page, name: string, options?: ShotOptions) {
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

export async function shot(page: Page, name: string, options?: ShotOptions) {
  await freezeMotion(page);
  if (!options?.fullPage && !options?.locator) {
    await writeShots(page, name, options);
    return;
  }
  const hideChrome = await page.addStyleTag({ content: HIDE_FIXED_CHROME });
  try {
    await writeShots(page, name, options);
  } finally {
    await hideChrome.evaluate((el) => {
      (el as HTMLStyleElement).remove();
    });
  }
}
