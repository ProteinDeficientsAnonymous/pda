import { expect, test } from '@playwright/test';

import { seed } from './fixtures';

test('non-member with email, no stored token, is emailed a link and not re-asked', async ({
  page,
}) => {
  const { event_id, event_title, user_phone } = seed('public-recognized');

  await page.goto(`/events/${event_id}`);
  await expect(page.getByRole('heading', { name: event_title })).toBeVisible();

  const rsvpSection = page.getByLabel('rsvp');
  await rsvpSection.getByRole('button', { name: "i'm going" }).click();
  await rsvpSection.getByLabel('phone number').pressSequentially(user_phone.replace('+1', ''));
  await rsvpSection.getByRole('button', { name: 'continue' }).click();

  await expect(rsvpSection.getByText('we recognized your number', { exact: false })).toBeVisible();
  await expect(rsvpSection.getByLabel('first name')).toBeHidden();
});
