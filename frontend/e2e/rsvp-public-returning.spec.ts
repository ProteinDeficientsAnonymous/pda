import { expect, test } from '@playwright/test';

import { seed } from './fixtures';

test('returning non-member with stored token skips phone-check', async ({ page }) => {
  const { event_id, event_title, rsvp_token } = seed('public-returning');

  await page.addInitScript((token) => {
    localStorage.setItem('pda-rsvp-token', token);
  }, rsvp_token);

  await page.goto(`/events/${event_id}`);
  await expect(page.getByRole('heading', { name: event_title })).toBeVisible();

  const rsvpSection = page.getByLabel('rsvp');
  await expect(rsvpSection.getByLabel('phone number')).not.toBeVisible();
  await expect(rsvpSection.getByText("i'm going", { exact: true })).toBeVisible();

  await rsvpSection.getByRole('button', { name: /edit rsvp/i }).click();

  const rsvpDialog = page.getByRole('dialog', { name: 'rsvp' });
  await expect(rsvpDialog).toBeVisible();
});

test('phone-width page shows cant go without a reload', async ({ page }) => {
  const { event_id, event_title, rsvp_token } = seed('public-returning');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript((token) => {
    localStorage.setItem('pda-rsvp-token', token);
  }, rsvp_token);

  await page.goto(`/events/${event_id}`);
  await expect(page.getByRole('heading', { name: event_title })).toBeVisible();

  const rsvpSection = page.getByLabel('rsvp');
  await rsvpSection.getByRole('button', { name: /edit rsvp/i }).click();
  const dialog = page.getByRole('dialog', { name: 'rsvp' });
  await dialog.getByRole('button', { name: "can't go" }).click();
  await dialog.getByRole('button', { name: 'save' }).click();

  await expect(dialog).toBeHidden();
  await expect(rsvpSection.getByRole('status')).toHaveText("i can't go");
});
