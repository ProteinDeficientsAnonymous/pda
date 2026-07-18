import { expect, test } from '@playwright/test';

import { seed } from './fixtures';

test('non-member views and cancels rsvp via my-rsvps manage link', async ({ page }) => {
  const { event_title, rsvp_token } = seed('my-rsvps');

  await page.goto(`/my-rsvps?token=${rsvp_token}`);

  await expect(page.getByRole('heading', { name: 'your rsvps' })).toBeVisible();
  const card = page.getByLabel(event_title);
  await expect(card).toBeVisible();
  await expect(card.getByText("you're going")).toBeVisible();

  await card.getByRole('button', { name: 'cancel rsvp' }).click();
  await expect(page.getByText('rsvp cancelled')).toBeVisible();
});
