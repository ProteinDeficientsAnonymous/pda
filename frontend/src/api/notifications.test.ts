import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

// Mutable auth-status sentinel — tests flip this to simulate authed/unauthed.
let mockAuthStatus = 'authed';

vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn((selector: (s: { status: string }) => unknown) =>
    selector({ status: mockAuthStatus }),
  ),
}));

import { apiClient } from '@/api/client';
import { useNotifications, useUnreadCount, useMarkAllNotificationsRead } from './notifications';

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  vi.clearAllMocks();
  mockAuthStatus = 'authed';
});

// ---------------------------------------------------------------------------
// useNotifications
// ---------------------------------------------------------------------------

describe('useNotifications', () => {
  it('returns mapped list of notifications on success', async () => {
    mockedGet.mockResolvedValueOnce({
      data: [
        {
          id: 'notif-1',
          notification_type: 'event_invite',
          event_id: 'evt-42',
          related_user_id: null,
          message: 'You have been invited',
          is_read: false,
          created_at: '2024-05-01T10:00:00Z',
        },
      ],
    });

    const { result } = renderHook(() => useNotifications(true), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([
      {
        id: 'notif-1',
        notificationType: 'event_invite',
        eventId: 'evt-42',
        relatedUserId: null,
        message: 'You have been invited',
        isRead: false,
        createdAt: '2024-05-01T10:00:00Z',
      },
    ]);

    expect(mockedGet).toHaveBeenCalledWith('/api/notifications/');
  });

  it('does not fetch when user is not authenticated', async () => {
    mockAuthStatus = 'unauthed';

    const { result } = renderHook(() => useNotifications(true), {
      wrapper: wrapper(),
    });

    // Query is disabled — stays in idle/pending without fetching
    expect(result.current.isPending).toBe(true);
    expect(result.current.fetchStatus).toBe('idle');
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it('propagates error on API failure', async () => {
    const apiError = new Error('server error');
    mockedGet.mockRejectedValueOnce(apiError);

    const { result } = renderHook(() => useNotifications(true), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(apiError);
  });
});

// ---------------------------------------------------------------------------
// useUnreadCount
// ---------------------------------------------------------------------------

describe('useUnreadCount', () => {
  it('returns unread count from API response', async () => {
    mockedGet.mockResolvedValueOnce({ data: { count: 7 } });

    const { result } = renderHook(() => useUnreadCount(false), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBe(7);
    expect(mockedGet).toHaveBeenCalledWith('/api/notifications/unread-count/');
  });
});

// ---------------------------------------------------------------------------
// useMarkAllNotificationsRead
// ---------------------------------------------------------------------------

describe('useMarkAllNotificationsRead', () => {
  it('POSTs read-all and invalidates the notifications query cache', async () => {
    mockedPost.mockResolvedValueOnce({ data: {} });

    const { result } = renderHook(() => useMarkAllNotificationsRead(), {
      wrapper: wrapper(),
    });

    await result.current.mutateAsync();

    expect(mockedPost).toHaveBeenCalledWith('/api/notifications/read-all/');
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});
