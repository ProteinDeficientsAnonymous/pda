// A single notification line — unread dot + message, navigates to the related
// resource on click and marks itself read. Shared by the bell dropdown and the
// full notifications page.

import { useNavigate } from 'react-router-dom';
import { type AppNotification } from '@/models/notification';
import { cn } from '@/utils/cn';
import { notificationTarget } from './notificationTarget';

export function NotificationRow({
  n,
  onMarkRead,
  onActivate,
}: {
  n: AppNotification;
  onMarkRead: () => void;
  // Runs after navigation is queued — the dropdown closes itself here.
  onActivate?: () => void;
}) {
  const navigate = useNavigate();
  function onClick() {
    onMarkRead();
    onActivate?.();
    const target = notificationTarget(n);
    if (target) void navigate(target);
  }
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'hover:bg-background flex w-full items-start gap-2 px-3 py-2 text-start',
        !n.isRead && 'bg-info-subtle',
      )}
    >
      {!n.isRead ? (
        <span aria-hidden="true" className="bg-info mt-1.5 h-2 w-2 shrink-0 rounded-full" />
      ) : (
        <span aria-hidden="true" className="mt-1.5 h-2 w-2 shrink-0" />
      )}
      <span className="text-foreground text-sm">{n.message}</span>
    </button>
  );
}
