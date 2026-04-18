// Event domain model. The backend blanks out member-only fields for unauthed
// users (empty strings, false bools, empty lists) — we render exactly what the
// server gives us and don't attempt to gate again client-side.

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
} as const;

export const InvitePermission = {
  AllMembers: 'all_members',
  CoHostsOnly: 'co_hosts_only',
} as const;

// Accepted input statuses for POST /rsvp/.
// `waitlisted` is server-assigned only (when an `attending` request comes in
// over capacity). See backend _event_rsvps.py _coerce_status.
export const RsvpStatus = {
  Attending: 'attending',
  Maybe: 'maybe',
  CantGo: 'cant_go',
} as const;

// Statuses the server may return on a guest's `status` field.
export const RsvpServerStatus = {
  ...RsvpStatus,
  Waitlisted: 'waitlisted',
} as const;

export interface EventGuest {
  userId: string;
  name: string;
  status: string;
  phone: string | null;
  photoUrl: string;
  hasPlusOne: boolean;
}

// List endpoint returns a subset; detail endpoint returns everything.
// We model them as one interface with the detail-only fields optional.
export interface Event {
  id: string;
  title: string;
  description: string;
  startDatetime: Date;
  endDatetime: Date | null;

  location: string;
  latitude: number | null;
  longitude: number | null;

  // Member-only (blanked '' for unauthed).
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

  // Detail-only.
  guests: EventGuest[];
  myRsvp: string | null;
  surveySlugs: string[];
  invitedUserIds: string[];
  invitedUserNames: string[];
  invitedUserPhotoUrls: string[];
  invitePermission: string;

  eventType: string;
  visibility: string;
  photoUrl: string;

  isPast: boolean;
  status: string;
}

// Maps an event to its chip/calendar css classes. Colocated with the model so
// any list/detail/badge view can reuse the same color mapping. Returns two
// classes: the shared .pda-evt base + one of the type/visibility variants.
// Precedence matches the Flutter frontend: cancelled > official > invite-only
// > members-only > community.
export function eventClass(e: Event): string {
  if (e.status === EventStatus.Cancelled) return 'pda-evt pda-evt-cancelled';
  if (e.eventType === EventType.Official) return 'pda-evt pda-evt-official';
  if (e.visibility === EventVisibility.InviteOnly) return 'pda-evt pda-evt-invite';
  if (e.visibility === EventVisibility.MembersOnly) return 'pda-evt pda-evt-members';
  return 'pda-evt pda-evt-community';
}
