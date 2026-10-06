import { expect, test } from '@playwright/test';

import { shotThemes } from './shot';

test('login', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'welcome back' })).toBeVisible();
  await shotThemes(page, 'login');
});
