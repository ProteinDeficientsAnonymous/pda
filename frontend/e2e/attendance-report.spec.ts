import { expect, type Page, test } from '@playwright/test';

import { seed } from './fixtures';

async function loginAsMember(page: Page, phone: string, password: string) {
  await page.goto('/login');
  await page.getByLabel('phone number').pressSequentially(phone.replace('+1', ''));
  await page.getByRole('button', { name: 'continue' }).click();
  await page.getByRole('textbox', { name: 'password' }).fill(password);
  await page.getByRole('button', { name: 'sign in' }).click();
  await page.waitForURL((url) => url.pathname !== '/login');

  if (page.url().includes('/consent')) {
    await page
      .getByRole('checkbox', {
        name: 'i have read and agree to the community guidelines and community agreements',
      })
      .check();
    await page.getByRole('checkbox', { name: 'i agree to the sms policy' }).check();
    await page.getByRole('button', { name: 'continue' }).click();
    await page.waitForURL((url) => !url.pathname.includes('/consent'));
  }
}

test('host opens check-in report from the kebab menu and sees the attendance breakdown', async ({
  page,
}) => {
  const { event_id, event_title, host_phone, host_password } = seed('attendance-report');

  await loginAsMember(page, host_phone, host_password);
  await page.goto(`/events/${event_id}`);
  await expect(page.getByRole('heading', { name: event_title.toLowerCase() })).toBeVisible();

  await page.getByRole('button', { name: 'event settings' }).click();
  const menu = page.getByRole('menu');
  await expect(menu.getByRole('menuitem', { name: 'check-in' })).toBeVisible();
  await menu.getByRole('menuitem', { name: 'check-in report' }).click();

  await page.waitForURL(`**/events/${event_id}/report`);
  await expect(page.getByRole('heading', { name: 'check-in report' })).toBeVisible();

  // summary pills: 1 attended, 1 no-show, 1 canceled, 0 unmarked
  await expect(page.getByText('1 attended')).toBeVisible();
  await expect(page.getByText('1 no-show')).toBeVisible();
  await expect(page.getByText('1 canceled')).toBeVisible();

  await expect(page.getByRole('heading', { name: 'attended' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'no-shows' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'canceled' })).toBeVisible();
});

test('check-in report csv sheet downloads a file with the selected columns', async ({ page }) => {
  const { event_id, host_phone, host_password } = seed('attendance-report');

  await loginAsMember(page, host_phone, host_password);
  await page.goto(`/events/${event_id}/report`);
  await expect(page.getByRole('heading', { name: 'check-in report' })).toBeVisible();

  await page.getByRole('button', { name: 'export csv' }).click();
  const dialog = page.getByRole('dialog', { name: 'download csv' });
  await expect(dialog).toBeVisible();

  const downloadPromise = page.waitForEvent('download');
  await dialog.getByRole('button', { name: 'download' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.csv$/);
});
