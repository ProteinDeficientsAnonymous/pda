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

test('admin switches to the members tab and sees pause candidates ranked first', async ({
  page,
}) => {
  const { admin_phone, admin_password, at_risk_name } = seed('attendance-analytics');

  await loginAsMember(page, admin_phone, admin_password);
  await page.goto('/admin/attendance');
  await expect(page.getByRole('heading', { name: 'attendance' })).toBeVisible();

  const tabs = page.getByRole('tablist', { name: 'attendance view' });
  await expect(tabs).toBeVisible();
  await tabs.getByRole('tab', { name: 'members' }).click();

  // the at-risk (400-day-stale) member is a pause candidate and shows the badge
  await expect(page.getByText(at_risk_name)).toBeVisible();
  await expect(page.getByText('pause candidate').first()).toBeVisible();

  await page.getByRole('button', { name: 'at risk' }).click();
  await expect(page.getByText(at_risk_name)).toBeVisible();
});

test('admin with manage_users can pause an at-risk member', async ({ page }) => {
  const { admin_phone, admin_password, at_risk_name } = seed('attendance-analytics');

  await loginAsMember(page, admin_phone, admin_password);
  await page.goto('/admin/attendance');
  await page
    .getByRole('tablist', { name: 'attendance view' })
    .getByRole('tab', { name: 'members' })
    .click();
  await page.getByRole('button', { name: 'at risk' }).click();

  const card = page.getByRole('listitem').filter({ hasText: at_risk_name });
  await card.getByRole('button', { name: 'pause member' }).click();

  const confirm = page.getByRole('dialog', { name: 'pause this member?' });
  await confirm.getByRole('button', { name: 'pause' }).click();

  await expect(page.getByText('paused').first()).toBeVisible();
});

// Bug probe (Issue filed): the events tab links every row to /events/:id/report,
// which is gated by the SEPARATE host_attendance_report flag. With only
// admin_attendance_analytics enabled, clicking a row bounces the admin to
// /calendar via RequireFlag. This test documents the current broken behavior;
// flip the assertion once the cross-flag dead-link is fixed.
test('events-tab row dead-links to /calendar when host flag is off (known bug)', async ({
  page,
}) => {
  const { admin_phone, admin_password } = seed('attendance-analytics');

  await loginAsMember(page, admin_phone, admin_password);
  await page.goto('/admin/attendance');

  const row = page.locator('a[href*="/report"]').first();
  const rowCount = await row.count();
  test.skip(rowCount === 0, 'no marked events seeded on the events tab');

  await row.click();
  // BUG: expected to land on the report, actually bounced to /calendar.
  await expect(page).toHaveURL(/\/calendar/);
});
