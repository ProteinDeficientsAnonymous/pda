import { readFile } from 'node:fs/promises';
import { expect, type Page, test } from '@playwright/test';

import { seed, signInWithToken } from './fixtures';

function section(page: Page, title: string) {
  return page.locator('section').filter({
    has: page.getByRole('heading', { name: title, exact: true }),
  });
}

test('host opens check-in report from the kebab menu and sees the attendance breakdown', async ({
  context,
  page,
}) => {
  const data = seed('attendance-report');
  await signInWithToken(context, data.refresh_token);

  await page.goto(`/events/${data.event_id}`);
  await expect(page.getByRole('heading', { name: data.event_title.toLowerCase() })).toBeVisible();

  await page.getByRole('button', { name: 'event settings' }).click();
  const menu = page.getByRole('menu');
  await expect(menu.getByRole('menuitem', { name: 'check-in', exact: true })).toBeVisible();
  await menu.getByRole('menuitem', { name: 'check-in report' }).click();

  await page.waitForURL(`**/events/${data.event_id}/report`);
  await expect(page.getByRole('heading', { name: 'check-in report' })).toBeVisible();

  await expect(page.getByText('1 attended')).toBeVisible();
  await expect(page.getByText('1 no-show')).toBeVisible();
  await expect(page.getByText('1 canceled')).toBeVisible();

  const attended = section(page, 'attended');
  const noShows = section(page, 'no-shows');
  const canceled = section(page, 'canceled');
  await expect(attended.getByRole('listitem')).toHaveText([data.attended_name]);
  await expect(noShows.getByRole('listitem')).toHaveText([data.no_show_name]);
  await expect(canceled.getByRole('listitem')).toHaveCount(1);
  await expect(canceled.getByRole('listitem')).toContainText(data.canceled_name);
});

test('check-in report csv sheet downloads only the selected columns', async ({ context, page }) => {
  const data = seed('attendance-report');
  await signInWithToken(context, data.refresh_token);

  await page.goto(`/events/${data.event_id}/report`);
  await expect(page.getByRole('heading', { name: 'check-in report' })).toBeVisible();

  await page.getByRole('button', { name: 'export csv' }).click();
  const dialog = page.getByRole('dialog', { name: 'download csv' });
  await dialog.getByRole('checkbox', { name: 'phone' }).uncheck();
  await dialog.getByRole('checkbox', { name: 'canceled time' }).uncheck();
  await dialog.getByRole('checkbox', { name: 'plus-one' }).uncheck();

  const downloadPromise = page.waitForEvent('download');
  await dialog.getByRole('button', { name: 'download' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(`check-in-report-${data.event_id}.csv`);

  const [header, ...rows] = (await readFile(await download.path(), 'utf-8')).trim().split(/\r?\n/);
  expect(header).toBe('name,rsvp_status,attendance');
  expect(rows.sort()).toEqual(
    [
      `${data.attended_name},attending,attended`,
      `${data.canceled_name},cant_go,unknown`,
      `${data.no_show_name},attending,didnt_go`,
    ].sort(),
  );
});
