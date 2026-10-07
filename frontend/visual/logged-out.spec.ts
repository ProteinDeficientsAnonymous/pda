import { test } from '@playwright/test';

import { seed } from '../e2e/fixtures';
import { prepare, screen, shootAll } from './session';

const loggedOutScreens = [
  screen('home', '/', { readyUrl: '/api/community/home/' }),
  screen('faq', '/faq', { heading: 'faq' }),
  screen('donate', '/donate', { heading: 'donate' }),
  screen('guidelines', '/guidelines', { heading: 'community guidelines' }),
  screen('install', '/install', { heading: 'install the app' }),
  screen('sms-policy', '/sms-policy', { heading: 'sms policy' }),
  screen('join', '/join', { heading: 'request to join pda' }),
  screen('join-success', '/join/success', { heading: 'request received!' }),
  screen('magic-login', '/magic-login/00000000-0000-0000-0000-000000000000', {
    heading: 'link expired',
  }),
  screen('calendar', '/calendar?date=2026-10-09&view=month', { text: 'october 2026' }),
];

test('logged out screens', async ({ page }) => {
  seed('member-screens');
  await prepare(page);
  await shootAll(page, loggedOutScreens);
});
