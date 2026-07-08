// Notifications API + the query hooks that keep them fresh.
//
// The notification bell relies on unread-count polling (cheap), deferring the
// full list fetch until the sheet opens. When SSE is connected we poll every
// 5 min as a safety net; when disconnected we poll every 30 s. Tab visibility
// is handled by TanStack Query's refetchIntervalInBackground: false.

import {
  type InfiniteData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import { useAuthStore } from '@/auth/store';
import type { AppNotification } from '@/models/notification';

import { apiClient } from './client';

interface WireNotification {
  id: string;
  notification_type: string;
  event_id: string | null;
  related_user_id: string | null;
  message: string;
  is_read: boolean;
  created_at: string;
}

function mapNotification(n: WireNotification): AppNotification {
  return {
    id: n.id,
    notificationType: n.notification_type,
    eventId: n.event_id,
    relatedUserId: n.related_user_id,
    message: n.message,
    isRead: n.is_read,
    createdAt: n.created_at,
  };
}

// How many notifications the bell dropdown shows before "see more" takes over.
export const BELL_NOTIFICATION_LIMIT = 10;
// Page size the full notifications screen requests per "load more".
export const NOTIFICATIONS_PAGE_SIZE = 30;

export const notificationKeys = {
  all: ['notifications'] as const,
  // The bell dropdown's capped list and the full-history page are kept under
  // distinct keys so the two caches don't clobber each other. Both still sit
  // under `all`, so mark-read / SSE invalidations cover them in one sweep.
  bell: ['notifications', 'list', 'bell'] as const,
  page: ['notifications', 'list', 'page'] as const,
  unread: ['notifications', 'unread-count'] as const,
};

async function fetchUnreadCount(): Promise<number> {
  const { data } = await apiClient.get<{ count: number }>('/api/notifications/unread-count/');
  return data.count;
}

async function fetchNotifications(params?: {
  limit?: number;
  offset?: number;
}): Promise<AppNotification[]> {
  const { data } = await apiClient.get<WireNotification[]>('/api/notifications/', {
    params: { limit: params?.limit, offset: params?.offset },
  });
  return data.map(mapNotification);
}

export function useUnreadCount(sseConnected: boolean) {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useQuery({
    queryKey: notificationKeys.unread,
    queryFn: fetchUnreadCount,
    enabled: isAuthed,
    refetchInterval: sseConnected ? 300_000 : 30_000,
    refetchIntervalInBackground: false,
  });
}

// Bell dropdown: the most recent `BELL_NOTIFICATION_LIMIT`. Fetched lazily when
// the sheet opens. Older history lives on the full notifications page.
export function useNotifications(enabled: boolean) {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useQuery({
    queryKey: notificationKeys.bell,
    queryFn: () => fetchNotifications({ limit: BELL_NOTIFICATION_LIMIT }),
    enabled: isAuthed && enabled,
  });
}

// Full notifications page: the complete history, paged in via "load more".
export function useNotificationHistory() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useInfiniteQuery({
    queryKey: notificationKeys.page,
    queryFn: ({ pageParam }) =>
      fetchNotifications({ limit: NOTIFICATIONS_PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    // A short page means we've reached the end — stop offering "load more".
    getNextPageParam: (lastPage, allPages) =>
      lastPage.length < NOTIFICATIONS_PAGE_SIZE
        ? undefined
        : allPages.length * NOTIFICATIONS_PAGE_SIZE,
    enabled: isAuthed,
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.post(`/api/notifications/${id}/read/`);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await apiClient.post('/api/notifications/read-all/');
    },
    onMutate: () => {
      qc.setQueryData<number>(notificationKeys.unread, 0);
      qc.setQueryData<AppNotification[]>(notificationKeys.bell, (prev) =>
        prev ? prev.map((n) => ({ ...n, isRead: true })) : prev,
      );
      qc.setQueryData<InfiniteData<AppNotification[]>>(notificationKeys.page, (prev) =>
        prev
          ? {
              ...prev,
              pages: prev.pages.map((page) => page.map((n) => ({ ...n, isRead: true }))),
            }
          : prev,
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}
