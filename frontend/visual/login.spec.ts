import { expect, test } from '@playwright/test';

import { shot } from './shot';

test('login', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'welcome back' })).toBeVisible();
  await shot(page, 'login');
});
