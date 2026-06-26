// Canned events for mock mode. Typed off the generated OpenAPI schema so the
// fixtures stay in lockstep with the real wire shape (EventListOut for the
// list, EventOut for detail). All user-facing strings are lowercase per the
// project copy convention.

import type { components } from '@/api/types.gen';

import { mockUser } from './user';

type EventListOut = components['schemas']['EventListOut'];
type EventOut = components['schemas']['EventOut'];

// Dates are relative to load time so the calendar always has something
// upcoming to render regardless of when the mock server boots.
const DAY = 24 * 60 * 60 * 1000;
const now = Date.now();
const inDays = (n: number, hour: number) => {
  const d = new Date(now + n * DAY);
  d.setHours(hour, 0, 0, 0);
  return d.toISOString();
};

// Shared fields common to the list and detail shapes — keeps the two fixtures
// from drifting apart and avoids restating two dozen defaults per event.
const baseEvent = {
  allow_plus_ones: false,
  attending_count: 8,
  cashapp_link: '',
  co_host_ids: [],
  co_host_names: [],
  co_host_photo_urls: [],
  comment_count: 2,
  created_by_id: mockUser.id,
  created_by_name: mockUser.display_name,
  created_by_photo_url: '',
  datetime_tbd: false,
  event_type: 'community',
  has_poll: false,
  invited_count: 0,
  is_past: false,
  latitude: null,
  longitude: null,
  max_attendees: null,
  other_link: '',
  partiful_link: '',
  photo_url: '',
  price: '',
  status: 'active',
  venmo_link: '',
  visibility: 'public',
  waitlisted_count: 0,
  whatsapp_link: '',
  zelle_info: '',
};

export const mockEventList: EventListOut[] = [
  {
    ...baseEvent,
    id: 'event-potluck',
    title: 'vegan potluck in the park',
    description: 'bring a dish to share — all plant-based, all welcome',
    location: 'prospect park, brooklyn',
    start_datetime: inDays(3, 17),
    end_datetime: inDays(3, 20),
    attending_count: 14,
  },
  {
    ...baseEvent,
    id: 'event-cooking',
    title: 'tofu scramble cooking class',
    description: 'learn the perfect weekend brunch scramble',
    location: 'community kitchen, queens',
    start_datetime: inDays(7, 11),
    end_datetime: inDays(7, 13),
    attending_count: 6,
  },
  {
    ...baseEvent,
    id: 'event-cleanup',
    title: 'beach cleanup + picnic',
    description: 'pick up trash, then share snacks',
    location: 'rockaway beach',
    start_datetime: inDays(12, 9),
    end_datetime: inDays(12, 14),
    attending_count: 22,
  },
];

export const mockEventDetail: EventOut = {
  ...baseEvent,
  id: 'event-potluck',
  title: 'vegan potluck in the park',
  description: 'bring a dish to share — all plant-based, all welcome',
  location: 'prospect park, brooklyn',
  start_datetime: inDays(3, 17),
  end_datetime: inDays(3, 20),
  attending_count: 14,
  rsvp_enabled: true,
  invite_permission: 'all_members',
  invited_user_ids: [],
  invited_user_names: [],
  invited_user_photo_urls: [],
  co_host_invite_ids: [],
  datetime_poll_slug: null,
  guests: [
    {
      user_id: mockUser.id,
      name: mockUser.display_name,
      status: 'attending',
      photo_url: '',
      has_plus_one: false,
      attendance: 'unknown',
    },
  ],
  my_pending_cohost_invite_id: null,
  my_rsvp: 'attending',
  pending_cohost_invites: [],
  survey_slugs: [],
};
