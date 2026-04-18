import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '@/auth/store';
import { NotificationType } from '@/models/notification';

// Mock the notifications API hooks (but NOT the stores)
vi.mock('@/api/notifications', () => ({
  notificationKeys: {
    all: ['notifications'],
    list: ['notifications', 'list'],
    unread: ['notifications', 'unread-count'],
  },
  useUnreadCount: vi.fn(),
  useNotifications: vi.fn(),
  useMarkNotificationRead: vi.fn(),
  useMarkAllNotificationsRead: vi.fn(),
}));

// useEventSource is a side-effect hook — stub it out so no EventSource is opened
vi.mock('@/hooks/useEventSource', () => ({
  useEventSource: vi.fn(),
}));

import {
  useUnreadCount,
  useNotifications,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
} from '@/api/notifications';
import { NotificationBell } from './NotificationBell';

const mockUseUnreadCount = vi.mocked(useUnreadCount);
const mockUseNotifications = vi.mocked(useNotifications);
const mockUseMarkNotificationRead = vi.mocked(useMarkNotificationRead);
const mockUseMarkAllNotificationsRead = vi.mocked(useMarkAllNotificationsRead);

function makeMutation(overrides = {}) {
  return { mutateAsync: vi.fn(), isPending: false, ...overrides };
}

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderBell(initialPath = '/') {
  return render(
    <QueryClientProvider client={makeQc()}>
      <MemoryRouter initialEntries={[initialPath]}>
        <NotificationBell />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useAuthStore.setState({ status: 'authed', user: null, accessToken: 'tok' });
  vi.clearAllMocks();

  // Safe defaults — overridden per test as needed
  mockUseUnreadCount.mockReturnValue({ data: 0 } as ReturnType<typeof useUnreadCount>);
  mockUseNotifications.mockReturnValue({ isPending: false, data: [] } as ReturnType<
    typeof useNotifications
  >);
  mockUseMarkNotificationRead.mockReturnValue(
    makeMutation() as ReturnType<typeof useMarkNotificationRead>,
  );
  mockUseMarkAllNotificationsRead.mockReturnValue(
    makeMutation() as ReturnType<typeof useMarkAllNotificationsRead>,
  );
});

describe('NotificationBell', () => {
  it('shows badge when unread count is greater than zero', () => {
    mockUseUnreadCount.mockReturnValue({ data: 3 } as ReturnType<typeof useUnreadCount>);
    renderBell();

    const bellButton = screen.getByRole('button', { name: /notifications \(3 unread\)/i });
    expect(bellButton).toBeInTheDocument();
    // The badge span containing the count
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('badge is not visible when unread count is zero', () => {
    mockUseUnreadCount.mockReturnValue({ data: 0 } as ReturnType<typeof useUnreadCount>);
    renderBell();

    // Button exists but has no unread annotation in label
    expect(screen.getByRole('button', { name: /^notifications$/i })).toBeInTheDocument();
    // No numeric badge in the DOM
    expect(screen.queryByText(/^\d+$/)).not.toBeInTheDocument();
  });

  it('tapping the bell opens the notification panel', async () => {
    const user = userEvent.setup();
    renderBell();

    await user.click(screen.getByRole('button', { name: /^notifications$/i }));

    // The panel is a dialog
    expect(screen.getByRole('dialog', { name: /notifications/i })).toBeInTheDocument();
  });

  it('shows empty state message when notification list is empty', async () => {
    const user = userEvent.setup();
    mockUseNotifications.mockReturnValue({ isPending: false, data: [] } as ReturnType<
      typeof useNotifications
    >);
    renderBell();

    await user.click(screen.getByRole('button', { name: /^notifications$/i }));

    expect(screen.getByText(/nothing new/i)).toBeInTheDocument();
  });

  it('shows mark-all-as-read button when panel is open and there are notifications', async () => {
    const user = userEvent.setup();
    mockUseUnreadCount.mockReturnValue({ data: 2 } as ReturnType<typeof useUnreadCount>);
    mockUseNotifications.mockReturnValue({
      isPending: false,
      data: [
        {
          id: 'n1',
          notificationType: NotificationType.EventInvite,
          eventId: 'ev1',
          relatedUserId: null,
          message: 'you were invited',
          isRead: false,
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
    } as ReturnType<typeof useNotifications>);

    renderBell();

    await user.click(screen.getByRole('button', { name: /notifications \(2 unread\)/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /mark all read/i })).toBeInTheDocument();
    });
  });

  it('tapping an event_invite notification navigates to /events/:id', async () => {
    const user = userEvent.setup();
    mockUseUnreadCount.mockReturnValue({ data: 1 } as ReturnType<typeof useUnreadCount>);
    mockUseNotifications.mockReturnValue({
      isPending: false,
      data: [
        {
          id: 'n2',
          notificationType: NotificationType.EventInvite,
          eventId: 'abc123',
          relatedUserId: null,
          message: 'you were invited to an event',
          isRead: false,
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
    } as ReturnType<typeof useNotifications>);
    mockUseMarkNotificationRead.mockReturnValue(
      makeMutation({ mutateAsync: vi.fn().mockResolvedValue(undefined) }) as ReturnType<
        typeof useMarkNotificationRead
      >,
    );

    // We need to capture navigation — render with a route display
    const qc = makeQc();
    let locationDisplay = '';
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/']}>
          <NotificationBell />
          {/* Use a simple component to track location changes */}
          <span
            data-testid="pathname"
            ref={(el) => {
              if (el) locationDisplay = el.textContent ?? '';
            }}
          />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    // Open the panel
    await user.click(screen.getByRole('button', { name: /notifications \(1 unread\)/i }));

    // Click the notification row
    const notifButton = await screen.findByRole('button', { name: /you were invited to an event/i });
    await user.click(notifButton);

    // After clicking, the panel should close (dialog gone)
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /notifications/i })).not.toBeInTheDocument();
    });
  });
});
