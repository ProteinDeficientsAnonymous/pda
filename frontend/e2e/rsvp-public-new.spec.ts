import { expect,test } from '@playwright/test';

import { seed } from './fixtures';

test('new non-member rsvps via public event link', async ({ page }) => {
  const { event_id, event_title } = seed('public-new');

  await page.goto(`/events/${event_id}`);
  await expect(page.getByRole('heading', { name: event_title })).toBeVisible();

  const phone = '202555' + String(Math.floor(1000 + Math.random() * 9000));

  const rsvpSection = page.getByLabel('rsvp');
  await rsvpSection.getByRole('button', { name: "i'm going" }).click();
  await rsvpSection.getByLabel('phone number').pressSequentially(phone);
  await rsvpSection.getByRole('button', { name: 'continue' }).click();

  await rsvpSection.getByLabel('first name').fill('Playwright');
  await rsvpSection.getByLabel('last name').fill('Tester');
  await rsvpSection.getByLabel('email').fill('playwright-new@example.com');
  await rsvpSection.getByRole('button', { name: 'rsvp' }).click();

  await expect(page.getByLabel('rsvp').getByText("you're going")).toBeVisible();
});
