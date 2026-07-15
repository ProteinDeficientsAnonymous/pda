import { hasPermission, Permission } from './permissions';
import type { User } from './user';

export const EventType = {
  Community: 'community',
  Official: 'official',
  Club: 'club',
} as const;

export const EventVisibility = {
  Public: 'public',
  MembersOnly: 'members_only',
  InviteOnly: 'invite_only',
} as const;

export const EventStatus = {
  Active: 'active',
  Cancelled: 'cancelled',
  Draft: 'draft',
  Deleted: 'deleted',
} as const;

export const InvitePermission = {
  AllMembers: 'all_members',
  CoHostsOnly: 'co_hosts_only',
} as const;

export const RsvpStatus = {
  Attending: 'attending',
  Maybe: 'maybe',
  CantGo: 'cant_go',
} as const;

export type RsvpInputStatus = (typeof RsvpStatus)[keyof typeof RsvpStatus];

export const RSVP_STATUS_LABELS: { status: RsvpInputStatus; label: string }[] = [
  { status: RsvpStatus.Attending, label: "i'm going" },
  { status: RsvpStatus.Maybe, label: 'maybe' },
  { status: RsvpStatus.CantGo, label: "can't go" },
];

export function isRsvpInputStatus(status: string | null): status is RsvpInputStatus {
  return RSVP_STATUS_LABELS.some((s) => s.status === status);
}

export const RsvpServerStatus = {
  ...RsvpStatus,
  Waitlisted: 'waitlisted',
} as const;

export const AttendanceStatus = {
  Unknown: 'unknown',
  Attended: 'attended',
  NoShow: 'no_show',
} as const;
export type AttendanceStatusValue = (typeof AttendanceStatus)[keyof typeof AttendanceStatus];

// A curated, admin-managed event tag (e.g. "walk", "restaurant meetup").
export interface EventTag {
  id: string;
  name: string;
  slug: string;
}

export interface EventGuest {
  userId: string;
  name: string;
  status: string;
  phone: string | null;
  photoUrl: string;
  hasPlusOne: boolean;
  attendance: AttendanceStatusValue;
}

export interface EventCancellation {
  userId: string;
  name: string;
  cancelledAt: Date;
  daysBeforeEvent: number;
}

export interface EventStats {
  goingCount: number;
  maybeCount: number;
  cantGoCount: number;
  noResponseCount: number;
  waitlistedCount: number;
  attendedCount: number;
  noShowCount: number;
  notMarkedCount: number;
  cancellations: EventCancellation[];
}

export interface Event {
  id: string;
  title: string;
  description: string;
  startDatetime: Date | null;
  endDatetime: Date | null;

  location: string;
  latitude: number | null;
  longitude: number | null;

  whatsappLink: string;
  partifulLink: string;
  otherLink: string;
  venmoLink: string;
  cashappLink: string;
  zelleInfo: string;
  price: string;

  rsvpEnabled: boolean;
  allowPlusOnes: boolean;
  maxAttendees: number | null;
  attendingCount: number;
  waitlistedCount: number;
  invitedCount: number;

  datetimeTbd: boolean;
  hasPoll: boolean;
  datetimePollSlug: string | null;

  createdById: string | null;
  createdByName: string | null;
  createdByPhotoUrl: string;
  coHostIds: string[];
  coHostNames: string[];
  coHostPhotoUrls: string[];
  coHostInviteIds: (string | null)[];

  guests: EventGuest[];
  myRsvp: string | null;
  // The resolved viewer's own user id — carried from the backend so a
  // token-holding (logged-out) viewer can find their own entry in `guests`,
  // since useAuthStore has no user for them.
  viewerUserId: string | null;
  surveySlugs: string[];
  invitedUserIds: string[];
  invitedUserNames: string[];
  invitedUserPhotoUrls: string[];
  invitePermission: string;

  pendingCohostInvites: PendingCohostInvite[];
  myPendingCohostInviteId: string | null;

  eventType: string;
  visibility: string;
  photoUrl: string;
  photoUpdatedAt: string | null;

  // Curated tags assigned to the event. Present on both list and detail.
  tags: EventTag[];

  isPast: boolean;
  status: string;
}

export interface PendingCohostInvite {
  id: string;
  userId: string;
  userName: string;
  userPhotoUrl: string;
  invitedAt: Date;
}

export function canManageEvent(event: Event, user: User | null): boolean {
  if (!user) return false;
  if (user.id === event.createdById) return true;
  if (event.coHostIds.includes(user.id)) return true;
  return hasPermission(user, Permission.ManageEvents);
}

export function canPublicRsvp(event: Event): boolean {
  return (
    event.eventType === EventType.Official &&
    event.visibility === EventVisibility.Public &&
    event.rsvpEnabled &&
    event.status !== EventStatus.Cancelled &&
    !event.isPast
  );
}

export function eventClass(e: Event): string {
  if (e.status === EventStatus.Cancelled) return 'pda-evt pda-evt-cancelled';
  if (e.eventType === EventType.Official) return 'pda-evt pda-evt-official';
  if (e.eventType === EventType.Club) return 'pda-evt pda-evt-club';
  if (e.visibility === EventVisibility.InviteOnly) return 'pda-evt pda-evt-invite';
  if (e.visibility === EventVisibility.MembersOnly) return 'pda-evt pda-evt-members';
  return 'pda-evt pda-evt-community';
}

export function spotsLeft(e: Event): number | null {
  if (e.maxAttendees === null) return null;
  return Math.max(0, e.maxAttendees - e.attendingCount);
}

export function myRsvpLabel(e: Event): string | null {
  switch (e.myRsvp) {
    case RsvpServerStatus.Attending:
      return 'going';
    case RsvpServerStatus.Maybe:
      return 'maybe';
    case RsvpServerStatus.CantGo:
      return "can't go";
    case RsvpServerStatus.Waitlisted:
      return 'waitlisted';
    default:
      return null;
  }
}
