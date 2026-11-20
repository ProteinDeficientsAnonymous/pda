import { expect, test } from '@playwright/test';

import { seed, signInWithToken } from './fixtures';

test('view-only planner reaches event planning from profile > admin', async ({ context, page }) => {
  const data = seed('view-planner');
  await signInWithToken(context, data.refresh_token);

  await page.goto('/');
  await page.getByRole('link', { name: 'profile', exact: true }).click();
  await page.waitForURL('**/profile');

  await page.getByRole('link', { name: 'admin', exact: true }).click();
  await page.waitForURL('**/admin');

  await page.getByRole('link', { name: /event planning/ }).click();
  await page.waitForURL('**/admin/planning**');
  await expect(page.getByRole('heading', { name: 'event planning' })).toBeVisible();
  await expect(page.getByRole('radio', { name: 'my availability' })).toBeVisible();
  await expect(page.getByRole('radio', { name: 'slots', exact: true })).toHaveCount(0);
});
