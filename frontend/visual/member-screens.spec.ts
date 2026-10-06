import { expect, type Page, test } from '@playwright/test';

import { seed } from '../e2e/fixtures';
import { prepare, screen, shootAll, signIn } from './session';
import { shot } from './shot';

const ONBOARDING_PASSWORD = 'E2e-test-pass-1';

async function hideBottomNav(page: Page) {
  // The fixed bar is painted over the bottom of a tall element screenshot.
  await page.locator('nav[aria-label="primary"]').evaluate((el) => {
    el.style.display = 'none';
  });
}

function section(page: Page, label: string) {
  return page.locator('section').filter({
    has: page.getByRole('heading', { name: label, exact: true }),
  });
}

async function patchMe(page: Page, token: string, data: Record<string, unknown>) {
  const response = await page.request.patch('/api/auth/me/', {
    headers: { Authorization: `Bearer ${token}` },
    data,
  });
  expect(response.ok()).toBeTruthy();
}

test('member screens', async ({ page }) => {
  test.setTimeout(120_000);
  const data = seed('member-screens');
  await prepare(page);
  await signIn(page, data.seed_phone, data.password);

  await page.goto('/settings');
  const profile = section(page, 'profile');
  await expect(profile.getByText('june 15, 1990')).toBeVisible();
  await hideBottomNav(page);
  await shot(page, 'settings-profile', { locator: profile });

  const privacy = section(page, 'privacy');
  await expect(privacy.getByText('show my last name to other members')).toBeVisible();
  await hideBottomNav(page);
  await shot(page, 'settings-privacy', { locator: privacy });

  await page.goto('/profile');
  await expect(page.getByText('🎂 june 15, 1990')).toBeVisible();
  await shot(page, 'own-profile-with-birthday', { fullPage: true });

  await page.goto(`/members/${data.jamie_id}`);
  await expect(page.getByText('🎂 march 2, 1991')).toBeVisible();
  await shot(page, 'member-profile-with-birthday', { fullPage: true });

  await patchMe(page, data.seed_token, { birthday: null });
  await page.goto('/profile');
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Seed Member' })).toBeVisible();
  await expect(page.getByText('🎂')).toHaveCount(0);
  await shot(page, 'own-profile', { fullPage: true });

  await patchMe(page, data.jamie_token, { show_birthday: false });
  await page.goto(`/members/${data.jamie_id}`);
  await expect(page.getByRole('heading', { name: 'Jamie Okafor' })).toBeVisible();
  await expect(page.getByText('🎂')).toHaveCount(0);
  await shot(page, 'member-profile', { fullPage: true });

  await shootAll(page, [
    screen('notifications', '/notifications', { heading: 'notifications' }),
    screen('members', '/members', { text: 'Jamie Okafor' }),
    screen('my-events', '/events/mine', { text: 'potluck' }),
    screen('event', '/events/potluck', { text: 'the park' }),
    screen('calendar-member', '/calendar?date=2026-10-09&view=month', { text: 'potluck' }),
    screen('volunteer', '/volunteer', { heading: 'volunteer' }),
    screen('join-member', '/join', { heading: "you're already in" }),
    screen('admin', '/admin', { text: 'nothing available to you yet' }),
  ]);
});

test('onboarding profile', async ({ page }) => {
  const data = seed('member-screens');
  await prepare(page);
  await signIn(page, data.ash_phone, data.password);
  await expect(page.getByLabel('first name')).toHaveValue('Ash');
  await page.getByLabel('email').fill('ash@example.com');
  await page.getByRole('textbox', { name: 'password' }).fill(ONBOARDING_PASSWORD);
  await page.getByRole('button', { name: 'continue' }).click();
  await expect(page.getByRole('heading', { name: 'make it yours' })).toBeVisible();
  await expect(page.getByText('add your birthday')).toBeVisible();
  await shot(page, 'onboarding', { fullPage: true });
});

test('weekly digest', async ({ page }) => {
  const data = seed('member-screens');
  await page.setContent(data.digest_html);
  await expect(page.getByText('potluck')).toBeVisible();
  await expect(page.getByRole('link', { name: 'see the full calendar' })).toBeVisible();
  await shot(page, 'digest', { fullPage: true, themes: false });
});
