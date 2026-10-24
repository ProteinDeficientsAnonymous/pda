import { expect, test } from '@playwright/test';

import { seed, signInWithToken } from '../e2e/fixtures';

test('built app returns openapi and shows event location only after sign-in', async ({
  page,
  request,
  context,
  baseURL,
}) => {
  expect((await request.get('/api/openapi.json')).status()).toBe(200);

  const home = await request.get('/');
  expect(home.status()).toBe(200);
  const html = await home.text();
  expect(html).toContain('/assets/');
  expect(html).not.toContain('/src/main.tsx');

  const data = seed('attendance-report');
  const locationLink = page.getByRole('link', {
    name: `open ${data.event_location} in maps`,
    exact: true,
  });

  await page.goto(`/events/${data.event_id}`);
  await expect(page.getByRole('heading', { name: data.event_title })).toBeVisible();
  await expect(locationLink).toHaveCount(0);

  if (!baseURL) {
    throw new Error('baseURL is required');
  }
  await signInWithToken(context, data.refresh_token, baseURL);
  await page.goto(`/events/${data.event_id}`);
  await expect(page.getByRole('heading', { name: data.event_title })).toBeVisible();
  await expect(locationLink).toBeVisible();
});
