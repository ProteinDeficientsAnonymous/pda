import { test } from '@playwright/test';

import { seed } from '../e2e/fixtures';
import { prepare, screen, shootAll, signIn } from './session';

test('new password gate', async ({ page }) => {
  const data = seed('member-screens');
  await prepare(page);
  await signIn(page, data.reset_phone, data.password);
  await shootAll(page, [
    screen('new-password', '/new-password', { heading: 'set a new password' }),
  ]);
});

test('consent gate', async ({ page }) => {
  const data = seed('member-screens');
  await prepare(page);
  await signIn(page, data.consent_phone, data.password);
  await shootAll(page, [screen('consent', '/consent', { heading: 'before you continue' })]);
});
