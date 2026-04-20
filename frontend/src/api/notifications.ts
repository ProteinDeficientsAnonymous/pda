// Notifications API + the query hooks that keep them fresh.
//
// The notification bell relies on unread-count polling (cheap), deferring the
// full list fetch until the sheet opens. When SSE is connected we poll every
// 5 min as a safety net; when disconnected we poll every 30 s. Tab visibility
// is handled by TanStack Query's refetchIntervalInBackground: false.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import { useAuthStore } from '@/auth/store';
import type { AppNotification } from '@/models/notification';

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

export const notificationKeys = {
  all: ['notifications'] as const,
  list: ['notifications', 'list'] as const,
  unread: ['notifications', 'unread-count'] as const,
};

async function fetchUnreadCount(): Promise<number> {
  const { data } = await apiClient.get<{ count: number }>('/api/notifications/unread-count/');
  return data.count;
}

async function fetchNotifications(): Promise<AppNotification[]> {
  const { data } = await apiClient.get<WireNotification[]>('/api/notifications/');
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

export function useNotifications(enabled: boolean) {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useQuery({
    queryKey: notificationKeys.list,
    queryFn: fetchNotifications,
    enabled: isAuthed && enabled,
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
      qc.setQueryData<AppNotification[]>(notificationKeys.list, (prev) =>
        prev ? prev.map((n) => ({ ...n, isRead: true })) : prev,
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}
