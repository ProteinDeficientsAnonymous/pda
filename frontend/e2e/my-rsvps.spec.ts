import { expect, test } from '@playwright/test';

import { seed } from './fixtures';

test('non-member sees their rsvp as a row linking to the event page', async ({ page }) => {
  const { event_title, rsvp_token } = seed('my-rsvps');

  await page.goto(`/my-rsvps?token=${rsvp_token}`);

  const row = page.getByRole('link', { name: new RegExp(event_title) });
  await expect(row).toBeVisible();
  await expect(row).toHaveAttribute('href', /^\/events\//);
});

test('invalid manage token shows the re-rsvp prompt, not an error', async ({ page }) => {
  await page.goto('/my-rsvps?token=definitely-not-a-real-token');

  await expect(page.getByText("this link's expired or invalid", { exact: false })).toBeVisible();
  await expect(page.locator('a[href^="/events/"]')).toBeHidden();
});
