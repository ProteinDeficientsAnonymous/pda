export const NotificationType = {
  EventInvite: 'event_invite',
  JoinRequest: 'join_request',
  CohostAdded: 'cohost_added',
  MagicLinkRequest: 'magic_link_request',
  WaitlistPromoted: 'waitlist_promoted',
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
