export const EventType = {
  Community: 'community',
  Official: 'official',
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

export function eventClass(e: Event): string {
  if (e.status === EventStatus.Cancelled) return 'pda-evt pda-evt-cancelled';
  if (e.eventType === EventType.Official) return 'pda-evt pda-evt-official';
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
