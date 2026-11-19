import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, type Page, test } from '@playwright/test';

const SEED_FILE = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../backend/community/management/commands/_seed_staging_data.py',
);

function requiredMatch(source: string, pattern: RegExp, label: string): string {
  const value = pattern.exec(source)?.[1];
  if (value === undefined) {
    throw new Error(`${label} is missing from ${SEED_FILE}`);
  }
  return value;
}

function stagingLogin(): { phone: string; password: string } {
  const envPhone = process.env.STAGING_PHONE;
  const envPassword = process.env.STAGING_PASSWORD;
  if (envPhone && envPassword) return { phone: envPhone, password: envPassword };

  const source = readFileSync(SEED_FILE, 'utf8');
  const password = requiredMatch(source, /^PASSWORD = "([^"]+)"/m, 'PASSWORD');
  const prefix = requiredMatch(
    source,
    /def status_phone\(index: int\) -> str:\n {4}return f"(\+\d+)\{index:02d\}"/,
    'status_phone',
  );
  return { phone: envPhone ?? `${prefix}00`, password: envPassword ?? password };
}

async function signIn(page: Page, phone: string, password: string) {
  await page.goto('/login');
  await page.getByLabel('phone number').pressSequentially(phone.replace(/^\+1/, ''));
  await page.getByRole('button', { name: 'continue' }).click();
  await page.getByRole('textbox', { name: 'password' }).fill(password);
  await page.getByRole('button', { name: 'sign in' }).click();
  await page.waitForURL((url) => url.pathname !== '/login');
}

async function showsText(page: Page, route: string, text: string) {
  await page.goto(route);
  await expect(page.getByText(text).first()).toBeVisible();
}

async function openCalendarView(page: Page, name: 'week' | 'day' | 'list') {
  await page
    .locator('label')
    .filter({ hasText: new RegExp(`^${name}$`) })
    .click();
  await expect(page).toHaveURL(new RegExp(`view=${name === 'list' ? 'agenda' : name}`));
}

test('logged-out pages render', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('link', { name: 'calendar' })).toBeVisible();

  await page.goto('/calendar');
  await expect(page.getByRole('radio', { name: 'month' })).toBeChecked();
  await openCalendarView(page, 'week');
  await openCalendarView(page, 'day');
  await openCalendarView(page, 'list');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/calendar');
  await expect(page.getByRole('radio', { name: 'month' })).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 720 });

  const pages = [
    ['/faq', 'faq'],
    ['/guidelines', 'community guidelines'],
    ['/donate', 'donate'],
    ['/install', 'install the app'],
    ['/sms-policy', 'sms policy'],
    ['/feedback', "this feedback link doesn't work"],
  ] as const;
  for (const [route, text] of pages) {
    await test.step(route, async () => {
      await showsText(page, route, text);
    });
  }

  await page.goto('/join');
  await expect(page.getByRole('heading', { name: 'request to join pda' })).toBeVisible();
  await page.getByLabel('phone number').fill('2125550199');
  await expect(page.getByLabel('phone number')).toHaveValue('+1 212 555 0199');
  const submit = page.getByRole('button', { name: 'submit request' });
  await submit.evaluate((el) => {
    el.scrollIntoView({ block: 'center' });
  });
  await submit.click();
  await expect(page.getByText('first name required')).toBeVisible();
  await expect(page).toHaveURL(/\/join$/);
});

test('signed-in smoke does not save changes', async ({ page }) => {
  const { phone, password } = stagingLogin();
  await signIn(page, phone, password);

  await page.goto('/members');
  await page.getByRole('textbox', { name: 'search' }).fill(phone.replace(/^\+1/, ''));
  await expect(page.getByRole('link', { name: /\(702\) 555-0700/ })).toBeVisible();

  const pages = [
    ['/profile', '(702) 555-0700'],
    ['/events/mine', 'upcoming'],
    ['/admin', 'join requests'],
    ['/admin/planning', 'event planning'],
    ['/events/manage', 'manage events'],
    ['/join-requests', 'join requests'],
    ['/admin/members', 'filter by role'],
    ['/docs', 'create document'],
    ['/admin/surveys', 'new survey'],
    ['/admin/attendance', 'who actually showed up'],
    ['/notifications', 'notifications'],
    ['/admin/flagged-events', 'flagged events'],
    ['/admin/join-form', 'questions shown to applicants'],
    ['/admin/event-speech', 'event speech'],
    ['/settings', 'change password'],
    ['/volunteer', 'volunteer'],
    ['/faq', 'faq'],
  ] as const;
  for (const [route, text] of pages) {
    await test.step(route, async () => {
      await showsText(page, route, text);
    });
  }

  await page.goto('/admin/planning');
  for (const tab of ['schedule', 'my availability', 'slots', 'checklist', 'guidelines'] as const) {
    await test.step(tab, async () => {
      await page
        .locator('label')
        .filter({ hasText: new RegExp(`^${tab}$`) })
        .click();
      await expect(page.getByRole('radio', { name: tab })).toBeChecked();
    });
  }

  await page.goto('/events/mine');
  await page.locator('main a[href^="/events/"]').first().click();
  await page.getByRole('button', { name: /rsvp/i }).click();
  await expect(page.getByRole('heading', { name: 'rsvp' })).toBeVisible();
  await page.getByRole('button', { name: 'cancel', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'rsvp' })).toBeHidden();

  await page.goto('/settings');
  await page.getByRole('button', { name: 'change password' }).click();
  await expect(page.getByRole('heading', { name: 'change password' })).toBeVisible();
  await page.getByRole('button', { name: 'cancel' }).click();
  await expect(page.getByRole('heading', { name: 'change password' })).toBeHidden();

  await page.getByRole('button', { name: 'send feedback' }).click();
  await expect(page.getByRole('heading', { name: 'send feedback' })).toBeVisible();
  await page.getByRole('button', { name: 'cancel' }).click();

  await page.getByRole('button', { name: 'open menu' }).click();
  await expect(page.getByRole('button', { name: 'log out' })).toBeVisible();
});
