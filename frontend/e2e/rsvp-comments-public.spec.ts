import { expect, test } from '@playwright/test';

import { seed } from './fixtures';

test('non-member with rsvp token can comment, reply, and react', async ({ page }) => {
  const { event_id, rsvp_token } = seed('comments');

  await page.addInitScript((token) => {
    localStorage.setItem('pda-rsvp-token', token);
  }, rsvp_token);

  await page.goto(`/events/${event_id}`);

  const commentsSection = page.locator('section', {
    has: page.getByRole('heading', { name: 'comments' }),
  });
  await commentsSection.scrollIntoViewIfNeeded();

  const commentText = `e2e comment ${String(Date.now())}`;
  await commentsSection.getByLabel('comment', { exact: true }).fill(commentText);
  await commentsSection.getByRole('button', { name: 'post' }).click();

  const postedComment = commentsSection.locator('article', { hasText: commentText });
  await expect(postedComment).toBeVisible();

  await postedComment.getByRole('button', { name: 'reply' }).click();
  const replyText = `e2e reply ${String(Date.now())}`;
  await postedComment.getByLabel('reply', { exact: true }).fill(replyText);
  await postedComment.getByRole('button', { name: 'post' }).click();
  await expect(postedComment.getByText(replyText)).toBeVisible();

  await postedComment.getByRole('button', { name: 'add reaction' }).click();
  await postedComment.getByRole('button', { name: '❤️' }).click();
  await expect(postedComment.getByRole('button', { name: '❤️ 1' })).toBeVisible();
});
