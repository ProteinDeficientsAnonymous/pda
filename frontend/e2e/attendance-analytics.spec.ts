import { expect, type Page, test } from '@playwright/test';

import { seed, signInWithToken } from './fixtures';

async function openMembersTab(page: Page, search: string) {
  await page.goto('/admin/attendance');
  await page
    .getByRole('tablist', { name: 'attendance view' })
    .getByRole('tab', { name: 'members' })
    .click();
  await page.getByLabel('search').fill(search);
}

test('members tab ranks pause candidates first and the at-risk filter hides compliant members', async ({
  context,
  page,
}) => {
  const data = seed('attendance-analytics');
  await signInWithToken(context, data.refresh_token);
  await openMembersTab(page, data.search);

  const cards = page.getByRole('article');
  await expect(cards).toHaveCount(2);
  await expect(cards.nth(0)).toContainText(data.at_risk_name);
  await expect(cards.nth(0)).toContainText('pause candidate');
  await expect(cards.nth(1)).toContainText(data.compliant_name);
  await expect(cards.nth(1).getByText('compliant', { exact: true })).toBeVisible();
  await expect(cards.nth(1)).not.toContainText('pause candidate');

  await page.getByRole('button', { name: 'at risk' }).click();
  await expect(cards).toHaveCount(1);
  await expect(cards.first()).toContainText(data.at_risk_name);
});

test('admin with manage_users can pause an at-risk member', async ({ context, page }) => {
  const data = seed('attendance-analytics');
  await signInWithToken(context, data.refresh_token);
  await openMembersTab(page, data.search);

  const card = page.getByRole('article').filter({ hasText: data.at_risk_name });
  await card.getByRole('button', { name: 'pause member' }).click();
  await page
    .getByRole('dialog', { name: 'pause this member?' })
    .getByRole('button', { name: 'pause' })
    .click();

  await expect(card.getByText('paused', { exact: true })).toBeVisible();
  await expect(card.getByRole('button', { name: 'pause member' })).toHaveCount(0);
});
