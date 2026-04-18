// Wire (snake_case, ISO strings) → Event (camelCase, Date objects) mapper.
// Kept separate from events.ts so the caller module stays ≤150 lines.

import type { Event, EventGuest } from '@/models/event';

interface WireGuest {
  user_id: string;
  name: string;
  status: string;
  phone?: string | null;
  photo_url?: string;
  has_plus_one?: boolean;
}

export interface WireEvent {
  id: string;
  title: string;
  description?: string;
  start_datetime: string;
  end_datetime?: string | null;

  location?: string;
  latitude?: number | null;
  longitude?: number | null;

  whatsapp_link?: string;
  partiful_link?: string;
  other_link?: string;
  venmo_link?: string;
  cashapp_link?: string;
  zelle_info?: string;
  price?: string;

  rsvp_enabled?: boolean;
  allow_plus_ones?: boolean;
  max_attendees?: number | null;
  attending_count?: number;
  waitlisted_count?: number;
  invited_count?: number;

  datetime_tbd?: boolean;
  has_poll?: boolean;
  datetime_poll_slug?: string | null;

  created_by_id?: string | null;
  created_by_name?: string | null;
  created_by_photo_url?: string;
  co_host_ids?: string[];
  co_host_names?: string[];
  co_host_photo_urls?: string[];

  guests?: WireGuest[];
  my_rsvp?: string | null;
  survey_slugs?: string[];
  invited_user_ids?: string[];
  invited_user_names?: string[];
  invited_user_photo_urls?: string[];
  invite_permission?: string;

  event_type?: string;
  visibility?: string;
  photo_url?: string;

  is_past?: boolean;
  status?: string;
}

function mapGuest(g: WireGuest): EventGuest {
  return {
    userId: g.user_id,
    name: g.name,
    status: g.status,
    phone: g.phone ?? null,
    photoUrl: g.photo_url ?? '',
    hasPlusOne: g.has_plus_one ?? false,
  };
}

export function mapEvent(e: WireEvent): Event {
  return {
    id: e.id,
    title: e.title,
    description: e.description ?? '',
    startDatetime: new Date(e.start_datetime),
    endDatetime: e.end_datetime ? new Date(e.end_datetime) : null,

    location: e.location ?? '',
    latitude: e.latitude ?? null,
    longitude: e.longitude ?? null,

    whatsappLink: e.whatsapp_link ?? '',
    partifulLink: e.partiful_link ?? '',
    otherLink: e.other_link ?? '',
    venmoLink: e.venmo_link ?? '',
    cashappLink: e.cashapp_link ?? '',
    zelleInfo: e.zelle_info ?? '',
    price: e.price ?? '',

    rsvpEnabled: e.rsvp_enabled ?? false,
    allowPlusOnes: e.allow_plus_ones ?? false,
    maxAttendees: e.max_attendees ?? null,
    attendingCount: e.attending_count ?? 0,
    waitlistedCount: e.waitlisted_count ?? 0,
    invitedCount: e.invited_count ?? 0,

    datetimeTbd: e.datetime_tbd ?? false,
    hasPoll: e.has_poll ?? false,
    datetimePollSlug: e.datetime_poll_slug ?? null,

    createdById: e.created_by_id ?? null,
    createdByName: e.created_by_name ?? null,
    createdByPhotoUrl: e.created_by_photo_url ?? '',
    coHostIds: e.co_host_ids ?? [],
    coHostNames: e.co_host_names ?? [],
    coHostPhotoUrls: e.co_host_photo_urls ?? [],

    guests: (e.guests ?? []).map(mapGuest),
    myRsvp: e.my_rsvp ?? null,
    surveySlugs: e.survey_slugs ?? [],
    invitedUserIds: e.invited_user_ids ?? [],
    invitedUserNames: e.invited_user_names ?? [],
    invitedUserPhotoUrls: e.invited_user_photo_urls ?? [],
    invitePermission: e.invite_permission ?? 'all_members',

    eventType: e.event_type ?? 'community',
    visibility: e.visibility ?? 'public',
    photoUrl: e.photo_url ?? '',

    isPast: e.is_past ?? false,
    status: e.status ?? 'active',
  };
}
