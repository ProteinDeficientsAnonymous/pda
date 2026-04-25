export const NotificationType = {
  EventInvite: 'event_invite',
  EventFlagged: 'event_flagged',
  JoinRequest: 'join_request',
  CohostAdded: 'cohost_added', // legacy; pre-#363 invite-approval flow
  CohostInvite: 'cohost_invite',
  CohostInviteAccepted: 'cohost_invite_accepted',
  CohostInviteDeclined: 'cohost_invite_declined',
  MagicLinkRequest: 'magic_link_request',
  WaitlistPromoted: 'waitlist_promoted',
  EventCancelled: 'event_cancelled',
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
