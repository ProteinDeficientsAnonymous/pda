import { expect, test } from '@playwright/test';

import { seed } from './fixtures';

test('member phone in the public rsvp form is bounced to sign-in', async ({ page }) => {
  const { event_id, user_phone } = seed('member');

  await page.goto(`/events/${event_id}`);

  const rsvpSection = page.getByLabel('rsvp');
  await rsvpSection.getByRole('button', { name: "i'm going" }).click();
  await rsvpSection.getByLabel('phone number').pressSequentially(user_phone.replace('+1', ''));
  await rsvpSection.getByRole('button', { name: 'continue' }).click();

  await expect(page.getByText('looks like you already have an account')).toBeVisible();
  await expect(rsvpSection.getByRole('link', { name: 'sign in' })).toBeVisible();
  await expect(rsvpSection.getByLabel('first name')).toBeHidden();
});
