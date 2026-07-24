import { expect, type Page, test } from '@playwright/test';

import { seed } from './fixtures';

async function loginAsMember(page: Page, phone: string, password: string) {
  await page.goto('/login');
  await page.getByLabel('phone number').pressSequentially(phone.replace('+1', ''));
  await page.getByRole('button', { name: 'continue' }).click();
  await page.getByRole('textbox', { name: 'password' }).fill(password);
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
}

test('member A comment appears live in member B open event view via SSE', async ({ browser }) => {
  const { event_id, user_a_phone, user_a_password, user_b_phone, user_b_password } =
    seed('live-updates');

  const contextA = await browser.newContext();
  const contextB = await browser.newContext();
  const pageA = await contextA.newPage();
  const pageB = await contextB.newPage();

  try {
    await loginAsMember(pageA, user_a_phone, user_a_password);
    await loginAsMember(pageB, user_b_phone, user_b_password);

    await pageA.goto(`/events/${event_id}`);
    await pageB.goto(`/events/${event_id}`);

    const rsvpSectionA = pageA.getByLabel('rsvp');
    await rsvpSectionA.getByRole('button', { name: 'rsvp' }).click();
    await pageA
      .getByRole('dialog', { name: 'rsvp' })
      .getByRole('button', { name: 'confirm' })
      .click();
    await expect(rsvpSectionA.getByRole('button', { name: /edit rsvp/i })).toBeVisible();

    const commentsSectionA = pageA.locator('section', {
      has: pageA.getByRole('heading', { name: 'comments' }),
    });
    await commentsSectionA.scrollIntoViewIfNeeded();

    const commentText = `live e2e comment ${String(Date.now())}`;
    await commentsSectionA.getByLabel('comment', { exact: true }).fill(commentText);
    await commentsSectionA.getByRole('button', { name: 'post' }).click();
    await expect(commentsSectionA.getByText(commentText)).toBeVisible();

    await expect(pageB.getByText(commentText)).toBeVisible({ timeout: 15_000 });
  } finally {
    await contextA.close();
    await contextB.close();
  }
});
