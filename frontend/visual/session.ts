import { expect, type Page } from '@playwright/test';

import { shot } from './shot';

export async function prepare(page: Page) {
  // Fixed date keeps the calendar's "today" cell stable. Resume so timers
  // still run; install() pauses them and locators then wait forever.
  await page.clock.install({ time: new Date('2026-10-06T15:00:00-04:00') });
  await page.clock.resume();
  await page.emulateMedia({ reducedMotion: 'reduce' });
}

export async function signIn(page: Page, phone: string, password: string) {
  await page.goto('/login');
  await page.getByLabel('phone number').pressSequentially(phone.replace('+1', ''));
  await page.getByRole('button', { name: 'continue' }).click();
  await page.getByRole('textbox', { name: 'password' }).fill(password);
  await page.getByRole('button', { name: 'sign in' }).click();
  await page.waitForURL((url) => url.pathname !== '/login');
}

export interface ScreenShot {
  name: string;
  path: string;
  heading?: string;
  text?: string;
  readyUrl?: string;
}

export function screen(
  name: string,
  path: string,
  ready: Pick<ScreenShot, 'heading' | 'text' | 'readyUrl'> = {},
): ScreenShot {
  return { name, path, ...ready };
}

export async function shootAll(page: Page, shots: ScreenShot[]) {
  for (const item of shots) {
    const pending = item.readyUrl
      ? page.waitForResponse(
          (response) => response.url().includes(item.readyUrl ?? '') && response.ok(),
        )
      : null;
    await page.goto(item.path);
    if (pending) await pending;
    if (item.heading) {
      await expect(page.getByRole('heading', { name: item.heading })).toBeVisible();
    }
    if (item.text) {
      await expect(page.getByText(item.text).first()).toBeVisible();
    }
    if (!item.heading && !item.text) {
      await expect(page.getByText('loading…')).toHaveCount(0);
    }
    await shot(page, item.name, { fullPage: true });
  }
}
