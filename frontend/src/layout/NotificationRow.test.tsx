import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { NotificationType } from '@/models/notification';

import { NotificationRow } from './NotificationRow';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({ useNavigate: () => mockNavigate }));

function magicLinkNotification() {
  return {
    id: 'n1',
    notificationType: NotificationType.MagicLinkRequest,
    eventId: null,
    relatedUserId: 'u123',
    message: 'someone requested a new login link',
    isRead: false,
    createdAt: '2026-07-10T00:00:00Z',
  };
}

describe('NotificationRow', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('navigates before closing the menu so the tap is not dropped mid-unmount (Issue 436)', async () => {
    const calls: string[] = [];
    mockNavigate.mockImplementation(() => calls.push('navigate'));
    const onActivate = vi.fn(() => calls.push('activate'));

    render(
      <NotificationRow n={magicLinkNotification()} onMarkRead={vi.fn()} onActivate={onActivate} />,
    );
    await userEvent.click(screen.getByRole('button'));

    expect(mockNavigate).toHaveBeenCalledWith('/admin/members/u123');
    expect(onActivate).toHaveBeenCalledTimes(1);
    // Navigation must be queued before the menu-close unmounts this row.
    expect(calls).toEqual(['navigate', 'activate']);
  });

  it('marks the notification read on click', async () => {
    const onMarkRead = vi.fn();
    render(
      <NotificationRow n={magicLinkNotification()} onMarkRead={onMarkRead} onActivate={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole('button'));
    expect(onMarkRead).toHaveBeenCalledTimes(1);
  });

  it('navigates to event for rsvp status changed notification', async () => {
    const rsvpNotification = {
      id: 'n2',
      notificationType: NotificationType.RsvpStatusChanged,
      eventId: 'e456',
      relatedUserId: null,
      message: 'someone is going',
      isRead: false,
      createdAt: '2026-07-10T00:00:00Z',
    };

    render(<NotificationRow n={rsvpNotification} onMarkRead={vi.fn()} onActivate={vi.fn()} />);
    await userEvent.click(screen.getByRole('button'));

    expect(mockNavigate).toHaveBeenCalledWith('/events/e456');
  });

  it('navigates to event for payment revoked notification', async () => {
    const paymentRevokedNotification = {
      id: 'n3',
      notificationType: NotificationType.PaymentRevoked,
      eventId: 'e789',
      relatedUserId: null,
      message: 'your payment needs attention',
      isRead: false,
      createdAt: '2026-08-02T00:00:00Z',
    };

    render(
      <NotificationRow n={paymentRevokedNotification} onMarkRead={vi.fn()} onActivate={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole('button'));

    expect(mockNavigate).toHaveBeenCalledWith('/events/e789');
  });
});
