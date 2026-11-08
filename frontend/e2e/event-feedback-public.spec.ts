import { expect, test } from '@playwright/test';

import { seed } from './fixtures';

test('logged-out attendee opens their emailed feedback link and submits', async ({ page }) => {
  const { event_title, question_label, feedback_url } = seed('event-feedback');
  const link = new URL(feedback_url);

  // path + fragment only, so the test doesn't depend on FRONTEND_BASE_URL matching baseURL
  await page.goto(link.pathname + link.hash);

  await expect(page.getByRole('heading', { name: /^feedback for: / })).toContainText(event_title);
  const answer = page.getByLabel(question_label);
  await expect(answer).toBeVisible();

  await answer.fill('the food was great');
  await page.getByRole('button', { name: 'submit' }).click();

  await expect(page.getByRole('status')).toBeVisible();
  await expect(page.getByRole('button', { name: 'submit' })).toBeHidden();
});
