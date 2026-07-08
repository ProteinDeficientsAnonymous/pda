import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import {
  notificationKeys,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
  useUnreadCount,
} from '@/api/notifications';
import { useAuthStore } from '@/auth/store';
import { useEventSource } from '@/hooks/useEventSource';
import { reportError } from '@/utils/errorReporter';

import { NotificationRow } from './NotificationRow';

const ROUTE = '/notifications';

const AUTO_READ_DELAY_MS = 1500;

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
      // Silent cache invalidation for live event changes (co-host edits,
      // etc.) — no notification row, no bell bump. Just keep the UI fresh
      // for anyone who happens to be looking at the event right now.
      event_updated: () => {
        void qc.invalidateQueries({ queryKey: ['events'] });
      },
    },
  });

  const { data: count = 0 } = useUnreadCount(sseConnected);
  const notificationsQuery = useNotifications(open);
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();

  // Auto-mark all as read after the dropdown has been open for a beat — giving
  // the user time to actually see what's new before we clear the badge.
  // Closing (or unmounting) within the window cancels the pending call; a new
  // SSE-pushed notification bumps `count`, which resets the timer.
  //
  // We use `mutate` (not `mutateAsync`) with an inline `onError` so a rejected
  // mark-all never becomes an unhandled promise rejection. After a failure we
  // latch `autoMarkFailedRef` so the effect won't re-fire in a tight loop while
  // `count` stays non-zero; the latch clears whenever the dropdown closes, so
  // the next open retries once.
  const markAllMutate = markAll.mutate;
  const markAllPending = markAll.isPending;
  const autoMarkFailedRef = useRef(false);
  useEffect(() => {
    if (!open) {
      autoMarkFailedRef.current = false;
      return;
    }
    if (count === 0 || markAllPending || autoMarkFailedRef.current) return;
    const timer = setTimeout(() => {
      markAllMutate(undefined, {
        onError: (err) => {
          autoMarkFailedRef.current = true;
          void reportError(err, ROUTE, { action: 'mark-all-read' });
        },
      });
    }, AUTO_READ_DELAY_MS);
    return () => {
      clearTimeout(timer);
    };
  }, [open, count, markAllPending, markAllMutate]);

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
        className="text-foreground-secondary hover:bg-surface-dim relative inline-flex h-9 w-9 items-center justify-center rounded-md"
      >
        <BellIcon />
        {count > 0 ? (
          <span className="bg-destructive absolute end-1 top-1 flex h-4 min-w-[1rem] items-center justify-center rounded-full px-1 text-[10px] font-medium text-white">
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
            className="border-border bg-surface absolute end-0 top-10 z-20 w-80 overflow-hidden rounded-lg border shadow-(--shadow-lg)"
          >
            <div className="border-border border-b px-3 py-2">
              <span className="text-sm font-medium">notifications</span>
            </div>
            <div className="max-h-96 overflow-y-auto">
              {notificationsQuery.isPending ? (
                <p className="text-muted p-4 text-sm">loading…</p>
              ) : notificationsQuery.data && notificationsQuery.data.length > 0 ? (
                <ul className="divide-y divide-neutral-100">
                  {notificationsQuery.data.map((n) => (
                    <li key={n.id}>
                      <NotificationRow
                        n={n}
                        onMarkRead={() => {
                          if (!n.isRead) {
                            markRead.mutate(n.id, {
                              onError: (err) => {
                                void reportError(err, ROUTE, {
                                  action: 'mark-read',
                                  notificationId: n.id,
                                });
                              },
                            });
                          }
                        }}
                        onActivate={() => {
                          setOpen(false);
                        }}
                      />
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted p-4 text-sm">nothing new 🌿</p>
              )}
            </div>
            <div className="border-border border-t">
              <Link
                to={ROUTE}
                onClick={() => {
                  setOpen(false);
                }}
                className="text-info hover:bg-background block px-3 py-2 text-center text-sm font-medium"
              >
                see more
              </Link>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
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
