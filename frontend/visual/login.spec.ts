import { expect, test } from '@playwright/test';

import { shot } from './shot';

test('login', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'welcome back' })).toBeVisible();
  await shot(page, 'login');
});
