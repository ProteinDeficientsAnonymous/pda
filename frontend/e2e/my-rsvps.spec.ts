import { expect, test } from '@playwright/test';

import { seed } from './fixtures';

test('non-member views, updates, and cancels rsvp via my-rsvps manage link', async ({ page }) => {
  const { event_title, rsvp_token } = seed('my-rsvps');

  await page.goto(`/my-rsvps?token=${rsvp_token}`);

  await expect(page.getByRole('heading', { name: 'your rsvps' })).toBeVisible();
  const card = page.getByLabel(event_title);
  await expect(card).toBeVisible();
  await expect(card.getByText("you're going")).toBeVisible();

  await card.getByRole('button', { name: 'maybe' }).click();
  await expect(page.getByText('rsvp updated', { exact: false })).toBeVisible();
  await expect(card.getByText("you're a maybe")).toBeVisible();

  await card.getByRole('button', { name: 'cancel rsvp' }).click();
  await expect(page.getByText('rsvp cancelled')).toBeVisible();
});

test('invalid manage token shows the re-rsvp prompt, not an error', async ({ page }) => {
  await page.goto('/my-rsvps?token=definitely-not-a-real-token');

  await expect(page.getByText("this link's expired or invalid", { exact: false })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'your rsvps' })).toBeHidden();
});
