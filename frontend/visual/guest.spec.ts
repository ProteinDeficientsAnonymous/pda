import { test } from '@playwright/test';

import { seed } from '../e2e/fixtures';
import { prepare, screen, shootAll } from './session';

test('guest screens', async ({ page }) => {
  const data = seed('member-screens');
  await prepare(page);
  await shootAll(page, [
    screen('guest-rsvps', `/my-rsvps?token=${data.guest_token}`, { text: 'potluck' }),
    screen('guest-event', '/events/potluck', { text: 'the park' }),
  ]);
});
