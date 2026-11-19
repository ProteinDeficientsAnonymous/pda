import { expect, test } from '@playwright/test';

import { seed } from './fixtures';

test('toast close button stays inside a phone viewport', async ({ page }) => {
  const { rsvp_token } = seed('public-returning');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript((token) => {
    localStorage.setItem('pda-rsvp-token', token);
  }, rsvp_token);
  await page.goto('/');

  await page.getByRole('button', { name: 'send feedback' }).click();
  await page.getByLabel('title').fill('toast check');
  await page.getByLabel('description').fill('checking the close button');
  await page.getByRole('button', { name: 'submit' }).click();

  const toast = page.locator('[data-sonner-toast][data-mounted="true"]');
  const close = toast.getByRole('button', { name: 'Close toast' });
  await expect(close).toBeVisible();
  // The toast slides in from above the viewport. Measure it after that movement stops.
  let previousY = Number.NaN;
  await expect
    .poll(async () => {
      const y = (await close.boundingBox())?.y ?? -1;
      const stable = Math.abs(y - previousY) < 0.5;
      previousY = y;
      return stable ? y : -1;
    })
    .toBeGreaterThanOrEqual(0);
  const box = await close.boundingBox();
  expect(box).not.toBeNull();
  if (box === null) return;
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.y + box.height).toBeLessThanOrEqual(844);
  expect(box.x + box.width).toBeLessThanOrEqual(390);
});
