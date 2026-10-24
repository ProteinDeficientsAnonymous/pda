import { describe, expect, it } from 'vitest';

import { type AppNotification, NotificationType } from '@/models/notification';

import { notificationTarget } from './notificationTarget';

function notification(overrides: Partial<AppNotification>): AppNotification {
  return {
    id: 'n1',
    notificationType: NotificationType.EventInvite,
    eventId: 'e1',
    relatedUserId: null,
    message: '',
    isRead: false,
    createdAt: '2026-10-20T12:00:00Z',
    ...overrides,
  };
}

describe('notificationTarget', () => {
  it('sends new feedback to the host feedback page', () => {
    const n = notification({ notificationType: NotificationType.EventFeedback });
    expect(notificationTarget(n)).toBe('/events/e1/feedback');
  });

  it('has no target for feedback without an event', () => {
    const n = notification({ notificationType: NotificationType.EventFeedback, eventId: null });
    expect(notificationTarget(n)).toBeNull();
  });
});
