import { expect, test } from '@playwright/test';

import { seed } from '../e2e/fixtures';
import { prepare, signIn } from './session';
import { shot } from './shot';

test('waitlisted member edits their rsvp', async ({ page }) => {
  const data = seed('waitlist-screens');
  await prepare(page);
  await signIn(page, data.wren_phone, data.password);

  await page.goto('/events/supper');
  await expect(page.getByText("you're on the waitlist")).toBeVisible();
  await shot(page, 'event-waitlisted', { fullPage: true });

  await page.getByRole('button', { name: 'edit', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByText('stay on the waitlist')).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'add +1' })).toBeVisible();
  await shot(page, 'event-waitlist-edit');
});

test('waitlisted guest edits their rsvp', async ({ page }) => {
  const data = seed('waitlist-screens');
  await prepare(page);
  await page.goto(`/events/supper?rsvp_token=${data.guest_token}`);
  await expect(page.getByText("you're on the waitlist")).toBeVisible();
  await page.getByRole('button', { name: 'edit', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByText('+1s are for members only')).toBeVisible();
  await shot(page, 'guest-waitlist-edit');
});
