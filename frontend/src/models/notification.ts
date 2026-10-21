export const NotificationType = {
  EventInvite: 'event_invite',
  EventFlagged: 'event_flagged',
  JoinRequest: 'join_request',
  CohostAdded: 'cohost_added', // legacy; pre-#363 invite-approval flow
  CohostInvite: 'cohost_invite',
  CohostInviteAccepted: 'cohost_invite_accepted',
  CohostInviteDeclined: 'cohost_invite_declined',
  CohostRemoved: 'cohost_removed',
  MagicLinkRequest: 'magic_link_request',
  WaitlistPromoted: 'waitlist_promoted',
  EventCancelled: 'event_cancelled',
  CommentReply: 'comment_reply',
  EventComment: 'event_comment',
  CommentReaction: 'comment_reaction',
  RsvpDeclinedNote: 'rsvp_declined_note',
  RsvpStatusChanged: 'rsvp_status_changed',
  CheckinNudge: 'checkin_nudge',
  PaymentRevoked: 'payment_revoked',
} as const;

export interface AppNotification {
  id: string;
  notificationType: string;
  eventId: string | null;
  relatedUserId: string | null;
  message: string;
  isRead: boolean;
  createdAt: string;
}
