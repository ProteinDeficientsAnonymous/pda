import { expect, test } from '@playwright/test';

import { seed } from './fixtures';

test('member phone in the public rsvp form is redirected to the login password step', async ({
  page,
}) => {
  const { event_id, user_phone } = seed('member');

  await page.goto(`/events/${event_id}`);

  const rsvpSection = page.getByLabel('rsvp');
  await rsvpSection.getByRole('button', { name: "i'm going" }).click();
  await rsvpSection.getByLabel('phone number').pressSequentially(user_phone.replace('+1', ''));
  await rsvpSection.getByRole('button', { name: 'continue' }).click();

  // Lands straight on the password step with the phone already verified —
  // no re-entering the number, no rsvp contact form.
  await page.waitForURL('**/login');
  await expect(page.getByRole('textbox', { name: 'password' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: /phone number/i })).toBeHidden();
  await expect(page.getByLabel('first name')).toBeHidden();
});
