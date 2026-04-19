// Bell + unread-count badge + dropdown sheet of notifications. Subscribes to
// SSE when authed — server pushes `notification` events that trigger a
// count refetch. Polling is a fallback (30s when SSE is disconnected, 5 min
// when connected).

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/auth/store';
import {
  notificationKeys,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
  useUnreadCount,
} from '@/api/notifications';
import { useEventSource } from '@/hooks/useEventSource';
import { NotificationType, type AppNotification } from '@/models/notification';
import { Button } from '@/components/ui/Button';
import { cn } from '@/utils/cn';

export function NotificationBell() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [sseConnected, setSseConnected] = useState(false);
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();

  useEventSource({
    url: '/api/notifications/stream/',
    token: accessToken,
    onStatusChange: setSseConnected,
    events: {
      // A push from the server means *something* a notification can point at
      // just changed. Invalidate the notification caches so the bell updates,
      // and the query keys for every screen a notification can link to so
      // whatever screen the user happens to be on refetches in place.
      notification: () => {
        void qc.invalidateQueries({ queryKey: notificationKeys.all });
        void qc.invalidateQueries({ queryKey: ['join-requests'] });
        void qc.invalidateQueries({ queryKey: ['events'] });
        void qc.invalidateQueries({ queryKey: ['users'] });
      },
    },
  });

  const { data: count = 0 } = useUnreadCount(sseConnected);
  const notificationsQuery = useNotifications(open);
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();

  const display = count > 99 ? '99+' : String(count);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          setOpen((v) => !v);
        }}
        aria-label={count > 0 ? `notifications (${display} unread)` : 'notifications'}
        aria-expanded={open}
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-md text-neutral-700 hover:bg-neutral-100"
      >
        <BellIcon />
        {count > 0 ? (
          <span className="absolute end-1 top-1 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-medium text-white">
            {display}
          </span>
        ) : null}
      </button>

      {open ? (
        <>
          <button
            type="button"
            aria-label="close notifications"
            className="fixed inset-0 z-10 cursor-default"
            onClick={() => {
              setOpen(false);
            }}
          />
          <div
            role="dialog"
            aria-label="notifications"
            className="absolute end-0 top-10 z-20 w-80 overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-lg"
          >
            <div className="flex items-center justify-between border-b border-neutral-200 px-3 py-2">
              <span className="text-sm font-medium">notifications</span>
              {count > 0 ? (
                <Button
                  variant="ghost"
                  onClick={() => {
                    void markAll.mutateAsync();
                  }}
                  disabled={markAll.isPending}
                >
                  mark all read
                </Button>
              ) : null}
            </div>
            <div className="max-h-96 overflow-y-auto">
              {notificationsQuery.isPending ? (
                <p className="p-4 text-sm text-neutral-500">loading…</p>
              ) : notificationsQuery.data && notificationsQuery.data.length > 0 ? (
                <ul className="divide-y divide-neutral-100">
                  {notificationsQuery.data.map((n) => (
                    <li key={n.id}>
                      <NotificationRow
                        n={n}
                        onMarkRead={() => {
                          if (!n.isRead) void markRead.mutateAsync(n.id);
                        }}
                        onClose={() => {
                          setOpen(false);
                        }}
                      />
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="p-4 text-sm text-neutral-500">nothing new 🌿</p>
              )}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}

function NotificationRow({
  n,
  onMarkRead,
  onClose,
}: {
  n: AppNotification;
  onMarkRead: () => void;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  function onClick() {
    onMarkRead();
    onClose();
    const target = notificationTarget(n);
    if (target) void navigate(target);
  }
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full items-start gap-2 px-3 py-2 text-start hover:bg-neutral-50',
        !n.isRead && 'bg-blue-50',
      )}
    >
      {!n.isRead ? (
        <span aria-hidden="true" className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-blue-600" />
      ) : (
        <span aria-hidden="true" className="mt-1.5 h-2 w-2 shrink-0" />
      )}
      <span className="text-sm text-neutral-800">{n.message}</span>
    </button>
  );
}

function notificationTarget(n: AppNotification): string | null {
  switch (n.notificationType) {
    case NotificationType.EventInvite:
    case NotificationType.CohostAdded:
    case NotificationType.WaitlistPromoted:
      return n.eventId ? `/events/${n.eventId}` : null;
    case NotificationType.JoinRequest:
      return '/join-requests';
    case NotificationType.MagicLinkRequest:
      return n.relatedUserId ? `/members/${n.relatedUserId}` : '/members';
    default:
      return null;
  }
}

function BellIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  );
}
