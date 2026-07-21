import { expect, test } from '@playwright/test';

import { seed } from './fixtures';

test('recognized non-member (prior rsvp, no stored token) is emailed a link, not re-asked', async ({
  page,
}) => {
  const { event_id, event_title, user_phone } = seed('public-recognized');

  await page.goto(`/events/${event_id}`);
  await expect(page.getByRole('heading', { name: event_title })).toBeVisible();

  const rsvpSection = page.getByLabel('rsvp');
  await rsvpSection.getByRole('button', { name: "i'm going" }).click();
  await rsvpSection.getByLabel('phone number').pressSequentially(user_phone.replace('+1', ''));
  await rsvpSection.getByRole('button', { name: 'continue' }).click();

  // Their phone is recognized from a prior rsvp, so the flow stops at the
  // "check your email" step instead of showing the new-contact form.
  await expect(rsvpSection.getByText('we recognized your number', { exact: false })).toBeVisible();
  await expect(rsvpSection.getByLabel('first name')).toBeHidden();
});
