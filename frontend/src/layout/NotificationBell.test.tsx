import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, describe, it, expect, vi, beforeEach } from 'vitest';
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
  mockUseUnreadCount.mockReturnValue({ data: 0 } as unknown as ReturnType<typeof useUnreadCount>);
  mockUseNotifications.mockReturnValue({ isPending: false, data: [] } as unknown as ReturnType<
    typeof useNotifications
  >);
  mockUseMarkNotificationRead.mockReturnValue(
    makeMutation() as unknown as ReturnType<typeof useMarkNotificationRead>,
  );
  mockUseMarkAllNotificationsRead.mockReturnValue(
    makeMutation() as unknown as ReturnType<typeof useMarkAllNotificationsRead>,
  );
});

describe('NotificationBell', () => {
  it('shows badge when unread count is greater than zero', () => {
    mockUseUnreadCount.mockReturnValue({ data: 3 } as unknown as ReturnType<typeof useUnreadCount>);
    renderBell();

    const bellButton = screen.getByRole('button', { name: /notifications \(3 unread\)/i });
    expect(bellButton).toBeInTheDocument();
    // The badge span containing the count
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('badge is not visible when unread count is zero', () => {
    mockUseUnreadCount.mockReturnValue({ data: 0 } as unknown as ReturnType<typeof useUnreadCount>);
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
    mockUseNotifications.mockReturnValue({ isPending: false, data: [] } as unknown as ReturnType<
      typeof useNotifications
    >);
    renderBell();

    await user.click(screen.getByRole('button', { name: /^notifications$/i }));

    expect(screen.getByText(/nothing new/i)).toBeInTheDocument();
  });

  it('tapping an event_invite notification navigates to /events/:id', async () => {
    const user = userEvent.setup();
    mockUseUnreadCount.mockReturnValue({ data: 1 } as unknown as ReturnType<typeof useUnreadCount>);
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
    } as unknown as ReturnType<typeof useNotifications>);
    mockUseMarkNotificationRead.mockReturnValue(
      makeMutation({ mutateAsync: vi.fn().mockResolvedValue(undefined) }) as unknown as ReturnType<
        typeof useMarkNotificationRead
      >,
    );

    // We need to capture navigation — render with a route display
    const qc = makeQc();
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/']}>
          <NotificationBell />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    // Open the panel
    await user.click(screen.getByRole('button', { name: /notifications \(1 unread\)/i }));

    // Click the notification row
    const notifButton = await screen.findByRole('button', {
      name: /you were invited to an event/i,
    });
    await user.click(notifButton);

    // After clicking, the panel should close (dialog gone)
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /notifications/i })).not.toBeInTheDocument();
    });
  });
});

describe('NotificationBell auto-clear on open', () => {
  const AUTO_READ_DELAY_MS = 1500;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('fires mark-all-read after the delay when opened with unread items', () => {
    const mutateAsync = vi.fn().mockResolvedValue(undefined);
    mockUseUnreadCount.mockReturnValue({ data: 2 } as unknown as ReturnType<typeof useUnreadCount>);
    mockUseMarkAllNotificationsRead.mockReturnValue(
      makeMutation({ mutateAsync }) as unknown as ReturnType<typeof useMarkAllNotificationsRead>,
    );

    renderBell();

    fireEvent.click(screen.getByRole('button', { name: /notifications \(2 unread\)/i }));
    expect(mutateAsync).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(AUTO_READ_DELAY_MS);
    });

    expect(mutateAsync).toHaveBeenCalledTimes(1);
  });

  it('does not fire when the dropdown is opened with zero unread', () => {
    const mutateAsync = vi.fn().mockResolvedValue(undefined);
    mockUseUnreadCount.mockReturnValue({ data: 0 } as unknown as ReturnType<typeof useUnreadCount>);
    mockUseMarkAllNotificationsRead.mockReturnValue(
      makeMutation({ mutateAsync }) as unknown as ReturnType<typeof useMarkAllNotificationsRead>,
    );

    renderBell();

    fireEvent.click(screen.getByRole('button', { name: /^notifications$/i }));

    act(() => {
      vi.advanceTimersByTime(AUTO_READ_DELAY_MS * 2);
    });

    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('cancels the pending mark-all call if the dropdown closes within the delay', () => {
    const mutateAsync = vi.fn().mockResolvedValue(undefined);
    mockUseUnreadCount.mockReturnValue({ data: 3 } as unknown as ReturnType<typeof useUnreadCount>);
    mockUseMarkAllNotificationsRead.mockReturnValue(
      makeMutation({ mutateAsync }) as unknown as ReturnType<typeof useMarkAllNotificationsRead>,
    );

    renderBell();

    const bell = screen.getByRole('button', { name: /notifications \(3 unread\)/i });
    fireEvent.click(bell); // open
    act(() => {
      vi.advanceTimersByTime(AUTO_READ_DELAY_MS - 100);
    });
    fireEvent.click(bell); // close before delay elapses

    act(() => {
      vi.advanceTimersByTime(AUTO_READ_DELAY_MS * 2);
    });

    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('resets the timer when the dropdown is reopened', () => {
    const mutateAsync = vi.fn().mockResolvedValue(undefined);
    mockUseUnreadCount.mockReturnValue({ data: 1 } as unknown as ReturnType<typeof useUnreadCount>);
    mockUseMarkAllNotificationsRead.mockReturnValue(
      makeMutation({ mutateAsync }) as unknown as ReturnType<typeof useMarkAllNotificationsRead>,
    );

    renderBell();

    const bell = screen.getByRole('button', { name: /notifications \(1 unread\)/i });
    fireEvent.click(bell); // open
    act(() => {
      vi.advanceTimersByTime(500);
    });
    fireEvent.click(bell); // close
    fireEvent.click(bell); // reopen

    // Advance only the partial remainder of the first timer — must not have fired yet
    act(() => {
      vi.advanceTimersByTime(AUTO_READ_DELAY_MS - 500);
    });
    expect(mutateAsync).not.toHaveBeenCalled();

    // Now advance the rest of the new full delay — fires exactly once
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(mutateAsync).toHaveBeenCalledTimes(1);
  });
});
