import { expect, test } from '@playwright/test';

import { seed, signInWithToken } from './fixtures';

const PASSWORD = 'Journey-pass-1!';

function letters(length: number) {
  const alphabet = 'abcdefghijklmnopqrstuvwxyz';
  return Array.from({ length }, () => alphabet[Math.floor(Math.random() * alphabet.length)]).join(
    '',
  );
}

test('approved applicant uses the issued login link and then sees the event location', async ({
  page,
  browser,
}) => {
  const { event_id, event_title, event_location, admin_refresh_token } = seed('membership-journey');
  const firstName = `Play${letters(5)}`;
  const fullName = `${firstName} Applicant`;
  const phone = `202555${String(Math.floor(1000 + Math.random() * 9000))}`;

  await page.goto(`/events/${event_id}`);
  await expect(page.getByRole('heading', { name: event_title })).toBeVisible();
  await expect(page.getByText(event_location)).toBeHidden();

  await page.goto('/join');
  await page.getByLabel('first name').fill(firstName);
  await page.getByLabel('last name').fill('Applicant');
  await page.getByLabel('phone number').pressSequentially(phone);
  await page.getByLabel('email').fill(`${firstName.toLowerCase()}@example.com`);
  await page.getByRole('textbox', { name: /· required/ }).fill('potlucks and mutual aid');
  await page.getByRole('checkbox', { name: /sms policy/i }).check();
  await page.getByRole('checkbox', { name: /community guidelines/i }).check();
  await page.getByRole('button', { name: 'submit request' }).click();
  await expect(page.getByRole('heading', { name: 'request received!' })).toBeVisible();

  const adminContext = await browser.newContext();
  await signInWithToken(adminContext, admin_refresh_token);
  const adminPage = await adminContext.newPage();
  await adminPage.goto('/join-requests');
  const card = adminPage.locator('article').filter({
    has: adminPage.getByRole('heading', { name: fullName, exact: true }),
  });
  await card.getByRole('button', { name: 'approve', exact: true }).click();
  await adminPage
    .getByRole('dialog', { name: 'skip tentative and fully approve?' })
    .getByRole('button', { name: 'yes, fully approve' })
    .click();

  const welcome = adminPage.getByRole('dialog', { name: `welcome ${fullName}` });
  const magicUrl = (await welcome.locator('.font-mono').innerText()).replaceAll(/\s+/g, '');
  await adminContext.close();

  await page.goto(magicUrl);
  await page.waitForURL('**/new-password');
  await page.getByLabel('new password', { exact: true }).fill(PASSWORD);
  await page.getByLabel('confirm new password').fill(PASSWORD);
  await page.getByRole('button', { name: 'save password' }).click();
  await page.getByRole('button', { name: 'do this later' }).click();
  await page.waitForURL((url) => !url.pathname.includes('/new-password'));

  await page.goto(`/events/${event_id}`);
  await expect(page.getByRole('heading', { name: event_title })).toBeVisible();
  await expect(page.getByText(event_location)).toBeVisible();
});
