import { test } from '@playwright/test';

import { seed } from '../e2e/fixtures';
import { prepare, screen, shootAll, signIn } from './session';

test('admin screens', async ({ page }) => {
  test.setTimeout(180_000);
  const data = seed('member-screens');
  await prepare(page);
  await signIn(page, data.admin_phone, data.password);
  await shootAll(page, [
    screen('admin-hub', '/admin', { text: 'join requests' }),
    screen('admin-members', '/admin/members', { heading: 'members', text: 'Jamie Okafor' }),
    screen('admin-member', `/admin/members/${data.jamie_id}`, { heading: 'Jamie Okafor' }),
    screen('join-requests', '/join-requests', { heading: 'join requests', text: 'Sam Applicant' }),
    screen('manage-events', '/events/manage', { heading: 'manage events' }),
    screen('flagged-events', '/admin/flagged-events', { heading: 'flagged events' }),
    screen('attendance', '/admin/attendance', {
      heading: 'attendance',
      text: 'no attendance marked yet',
    }),
    screen('surveys', '/admin/surveys', { heading: 'surveys' }),
    screen('survey', `/admin/surveys/${data.survey_id}`, { heading: 'potluck feedback' }),
    screen('survey-responses', `/admin/surveys/${data.survey_id}/responses`, {
      heading: 'potluck feedback',
    }),
    screen('join-form', '/admin/join-form', { heading: 'join form' }),
    screen('docs', '/docs', { heading: 'docs' }),
    screen('doc', `/docs/${data.doc_id}`, { heading: 'house rules' }),
    screen('feature-flags', '/admin/feature-flags', {
      heading: 'feature flags',
      text: 'environment: local',
    }),
  ]);
});
