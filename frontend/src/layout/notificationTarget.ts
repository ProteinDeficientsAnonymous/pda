// Maps a notification to the in-app route it should open when clicked. Shared by
// the bell dropdown and the full notifications page so both navigate alike.

import { type AppNotification, NotificationType } from '@/models/notification';

export function notificationTarget(n: AppNotification): string | null {
  switch (n.notificationType) {
    case NotificationType.EventInvite:
    case NotificationType.CohostAdded:
    case NotificationType.CohostInvite:
    case NotificationType.CohostInviteAccepted:
    case NotificationType.CohostInviteDeclined:
    case NotificationType.CohostRemoved:
    case NotificationType.WaitlistPromoted:
    case NotificationType.EventCancelled:
    case NotificationType.CommentReply:
    case NotificationType.EventComment:
      return n.eventId ? `/events/${n.eventId}` : null;
    case NotificationType.EventFlagged:
      return '/admin/flagged-events';
    case NotificationType.JoinRequest:
      return '/join-requests';
    case NotificationType.MagicLinkRequest:
      return n.relatedUserId ? `/admin/members/${n.relatedUserId}` : '/admin/members';
    default:
      return null;
  }
}
