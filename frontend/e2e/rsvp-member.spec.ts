import { test, expect } from '@playwright/test';
import { seed } from './fixtures';

test('member rsvps to an event from event detail', async ({ page }) => {
  const { event_id, event_title, user_phone, user_password } = seed('member');

  await page.goto('/login');
  await page.getByLabel('phone number').pressSequentially(user_phone.replace('+1', ''));
  await page.getByRole('button', { name: 'continue' }).click();
  await page.getByRole('textbox', { name: 'password' }).fill(user_password);
  await page.getByRole('button', { name: 'sign in' }).click();
  await page.waitForURL((url) => url.pathname !== '/login');

  if (page.url().includes('/consent')) {
    await page
      .getByRole('checkbox', {
        name: 'i have read and agree to the community guidelines and community agreements',
      })
      .check();
    await page.getByRole('checkbox', { name: 'i agree to the sms policy' }).check();
    await page.getByRole('button', { name: 'continue' }).click();
    await page.waitForURL((url) => !url.pathname.includes('/consent'));
  }

  await page.goto(`/events/${event_id}`);
  await expect(page.getByRole('heading', { name: event_title })).toBeVisible();

  const rsvpSection = page.getByLabel('rsvp');
  await rsvpSection.getByRole('button', { name: "i'm going" }).click();

  const rsvpDialog = page.getByRole('dialog', { name: 'rsvp' });
  await rsvpDialog.getByRole('button', { name: 'confirm' }).click();

  await expect(rsvpSection.getByText("you're going")).toBeVisible();
});
