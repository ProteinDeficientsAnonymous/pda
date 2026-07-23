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
  await expect(rsvpSection.getByText('going', { exact: true })).toBeVisible();

  await rsvpSection.getByRole('button', { name: /edit rsvp/i }).click();

  const rsvpDialog = page.getByRole('dialog', { name: 'rsvp' });
  await expect(rsvpDialog).toBeVisible();
});
