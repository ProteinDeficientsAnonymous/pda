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
    case NotificationType.CommentReaction:
    case NotificationType.RsvpDeclinedNote:
      return n.eventId ? `/events/${n.eventId}` : null;
    case NotificationType.CheckinNudge:
      return n.eventId ? `/events/${n.eventId}/attendance` : null;
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
