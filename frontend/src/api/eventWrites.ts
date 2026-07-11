// Event create/edit + photo upload mutations.
//
// Separated from events.ts so phase-2 read hooks stay focused. The POST path
// has a hard 10/day rate limit per backend _events.py; we surface that as a
// dedicated error so the UI can show a sane message.

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/auth/store';
import {
  type Event,
  EventStatus as EventStatusEnum,
  EventType as EventTypeEnum,
  EventVisibility,
  InvitePermission,
} from '@/models/event';
import { reportError } from '@/utils/errorReporter';
import { fromCashAppUrl, fromVenmoUrl, toCashAppUrl, toVenmoUrl } from '@/utils/paymentHandle';

import { extractApiErrorOr, getApiStatus } from './apiErrors';
import { apiClient } from './client';
import { mapEvent, type WireEvent } from './eventMapper';
import { eventKeys } from './events';
import { textRecipientsKeys } from './textRecipients';

const ROUTE = '/events';

export type EventStatus = (typeof EventStatusEnum)[keyof typeof EventStatusEnum];

export interface EventFormValues {
  title: string;
  description: string;
  location: string;
  latitude: number | null;
  longitude: number | null;
  startDatetime: string | null; // null when datetimeTbd
  endDatetime: string | null;
  datetimeTbd: boolean;
  eventType: 'community' | 'official';
  visibility: 'public' | 'members_only' | 'invite_only';
  invitePermission: 'all_members' | 'co_hosts_only';
  rsvpEnabled: boolean;
  allowPlusOnes: boolean;
  maxAttendees: number | null;
  whatsappLink: string;
  partifulLink: string;
  otherLink: string;
  price: string;
  venmoLink: string;
  cashappLink: string;
  zelleInfo: string;
  coHostIds: string[];
  tagIds: string[];
  status: EventStatus;
}

type WireBody = Record<string, unknown>;

// Per-field mapping from a form value to its wire key + serialized value.
// Each encoder receives *only its own field's value*, so the same map drives
// both the full-body and partial-body builders without ever casting a
// `Partial<EventFormValues>` to the full type.
type WireField<K extends keyof EventFormValues> = readonly [
  wireKey: string,
  encode: (value: EventFormValues[K]) => unknown,
];

type WireFieldMap = { [K in keyof EventFormValues]?: WireField<K> };

const FIELD_TO_WIRE: WireFieldMap = {
  title: ['title', (v) => v],
  description: ['description', (v) => v],
  eventType: ['event_type', (v) => v],
  visibility: ['visibility', (v) => v],
  location: ['location', (v) => v],
  latitude: ['latitude', (v) => v],
  longitude: ['longitude', (v) => v],
  startDatetime: ['start_datetime', (v) => v],
  endDatetime: ['end_datetime', (v) => v],
  datetimeTbd: ['datetime_tbd', (v) => v],
  invitePermission: ['invite_permission', (v) => v],
  rsvpEnabled: ['rsvp_enabled', (v) => v],
  allowPlusOnes: ['allow_plus_ones', (v) => v],
  maxAttendees: ['max_attendees', (v) => v],
  whatsappLink: ['whatsapp_link', (v) => v],
  partifulLink: ['partiful_link', (v) => v],
  otherLink: ['other_link', (v) => v],
  price: ['price', (v) => v],
  venmoLink: ['venmo_link', (v) => toVenmoUrl(v)],
  cashappLink: ['cashapp_link', (v) => toCashAppUrl(v)],
  zelleInfo: ['zelle_info', (v) => v],
  coHostIds: ['co_host_ids', (v) => v],
  tagIds: ['tag_ids', (v) => v],
  status: ['status', (v) => v],
};

// Encode a single field by key, looking up its wire entry. The generic `K`
// keeps the field value and its encoder bound to the same key, so TS verifies
// each encoder only ever receives its own field's value — no cast required.
function encodeField<K extends keyof EventFormValues>(
  key: K,
  value: EventFormValues[K],
): readonly [string, unknown] | undefined {
  const field = FIELD_TO_WIRE[key];
  if (!field) return undefined;
  const [wireKey, encode] = field;
  return [wireKey, encode(value)];
}

function toWireBody(values: EventFormValues): WireBody {
  const body: WireBody = {};
  for (const key of Object.keys(FIELD_TO_WIRE) as (keyof EventFormValues)[]) {
    const encoded = encodeField(key, values[key]);
    if (!encoded) continue;
    body[encoded[0]] = encoded[1];
  }
  return body;
}

// Build a PATCH body from only the keys present in the Partial. Each encoder
// reads only its own field's value, so no `Partial → full` cast is needed.
export function toPartialWireBody(values: Partial<EventFormValues>): WireBody {
  const body: WireBody = {};
  for (const key of Object.keys(values) as (keyof EventFormValues)[]) {
    if (values[key] === undefined) continue;
    const encoded = encodeField(key, values[key]);
    if (!encoded) continue;
    body[encoded[0]] = encoded[1];
  }
  return body;
}

export function useCreateEvent() {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async (values: EventFormValues) => {
      const { data } = await apiClient.post<WireEvent>(
        '/api/community/events/',
        toWireBody(values),
      );
      return mapEvent(data);
    },
    onSuccess: (event) => {
      qc.setQueryData(eventKeys.detail(event.id, isAuthed), event);
      void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
    },
    onError: (err) => {
      void reportError(err, ROUTE, { action: 'create-event' });
    },
  });
}

// Invite-only mutation. Lives outside useUpdateEvent because the event form
// no longer manages invitations — they're handled exclusively by the
// per-event invite endpoint, which is add-only (set-union semantics) and so
// can't accidentally clobber an existing invitee list.
export function useInviteToEvent(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async (userIds: string[]) => {
      const { data } = await apiClient.post<WireEvent>(
        `/api/community/events/${eventId}/invitations/`,
        { user_ids: userIds },
      );
      return mapEvent(data);
    },
    onSuccess: (event) => {
      qc.setQueryData(eventKeys.detail(event.id, isAuthed), event);
      void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
      void qc.invalidateQueries({ queryKey: textRecipientsKeys.detail(event.id) });
    },
    onError: (err) => {
      void reportError(err, ROUTE, { action: 'invite-to-event', eventId });
    },
  });
}

export function useUpdateEvent(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async (values: Partial<EventFormValues>) => {
      // PATCH is partial: build the wire body from only the provided keys.
      // Falsy values other than undefined still carry meaning (false/""/null).
      const body = toPartialWireBody(values);
      const { data } = await apiClient.patch<WireEvent>(`/api/community/events/${eventId}/`, body);
      return mapEvent(data);
    },
    onSuccess: (event) => {
      qc.setQueryData(eventKeys.detail(event.id, isAuthed), event);
      void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
    },
    onError: (err) => {
      void reportError(err, ROUTE, { action: 'update-event', eventId });
    },
  });
}

// Cancel an event (active → cancelled). Notifies attendees; the backend
// no-ops notifications on draft→cancelled transitions.
export function useCancelEvent(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async () => {
      const body: WireBody = {
        status: EventStatusEnum.Cancelled,
        notify_attendees: true,
      };
      const { data } = await apiClient.patch<WireEvent>(`/api/community/events/${eventId}/`, body);
      return mapEvent(data);
    },
    onSuccess: (event) => {
      qc.setQueryData(eventKeys.detail(event.id, isAuthed), event);
      void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
    },
    onError: (err) => {
      void reportError(err, ROUTE, { action: 'cancel-event', eventId });
    },
  });
}

// Delete an event. PATCHes status=deleted, which the backend accepts from
// draft/active/cancelled. Active events with attendees must be cancelled first.
export function useDeleteEvent(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async () => {
      const body: WireBody = { status: EventStatusEnum.Deleted };
      const { data } = await apiClient.patch<WireEvent>(`/api/community/events/${eventId}/`, body);
      return mapEvent(data);
    },
    onSuccess: (event) => {
      qc.setQueryData(eventKeys.detail(event.id, isAuthed), event);
      void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
    },
    onError: (err) => {
      void reportError(err, ROUTE, { action: 'delete-event', eventId });
    },
  });
}

// The event id is a mutation variable, not a hook argument: on the create
// flow the id doesn't exist until create-event resolves, so binding it at
// hook-call time (when it's still '') POSTed to a route with no id → 404 and
// the photo was silently dropped (Issue 668).
export function useUploadEventPhoto() {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async ({ eventId, blob }: { eventId: string; blob: Blob }) => {
      const formData = new FormData();
      formData.append('photo', blob, 'event.png');
      const { data } = await apiClient.post<WireEvent>(
        `/api/community/events/${eventId}/photo/`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      );
      return mapEvent(data);
    },
    onSuccess: (event) => {
      qc.setQueryData(eventKeys.detail(event.id, isAuthed), event);
      void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
    },
    onError: (err, { eventId }) => {
      void reportError(err, ROUTE, { action: 'upload-event-photo', eventId });
    },
  });
}

export function useDeleteEventPhoto(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.delete<WireEvent>(`/api/community/events/${eventId}/photo/`);
      return mapEvent(data);
    },
    onSuccess: (event) => {
      qc.setQueryData(eventKeys.detail(event.id, isAuthed), event);
      void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
    },
    onError: (err) => {
      void reportError(err, ROUTE, { action: 'delete-event-photo', eventId });
    },
  });
}

export function extractEventError(err: unknown): string {
  // Event-create has a hard daily rate limit; surface that specifically.
  if (getApiStatus(err) === 429) {
    return "you've hit the daily event-creation limit — try again tomorrow";
  }
  return extractApiErrorOr(err, "couldn't save the event — try again");
}

export function emptyEventFormValues(): EventFormValues {
  return {
    title: '',
    description: '',
    location: '',
    latitude: null,
    longitude: null,
    startDatetime: null,
    endDatetime: null,
    datetimeTbd: false,
    eventType: 'community',
    visibility: 'public',
    invitePermission: 'all_members',
    rsvpEnabled: true,
    allowPlusOnes: true,
    maxAttendees: null,
    whatsappLink: '',
    partifulLink: '',
    otherLink: '',
    price: '',
    venmoLink: '',
    cashappLink: '',
    zelleInfo: '',
    coHostIds: [],
    tagIds: [],
    status: 'active',
  };
}

// Coerce an arbitrary wire string to a known union value, falling back to a
// safe default on anything unexpected. The server *should* only ever send
// known values, but a stale client / schema drift shouldn't blow up the form.
function coerceEnum<T extends string>(value: string, allowed: readonly T[], fallback: T): T {
  return (allowed as readonly string[]).includes(value) ? (value as T) : fallback;
}

const FORM_EVENT_TYPES = [EventTypeEnum.Community, EventTypeEnum.Official] as const;
const FORM_VISIBILITIES = [
  EventVisibility.Public,
  EventVisibility.MembersOnly,
  EventVisibility.InviteOnly,
] as const;
const FORM_INVITE_PERMISSIONS = [
  InvitePermission.AllMembers,
  InvitePermission.CoHostsOnly,
] as const;
const FORM_STATUSES = [
  EventStatusEnum.Active,
  EventStatusEnum.Draft,
  EventStatusEnum.Cancelled,
  EventStatusEnum.Deleted,
] as const;

export function eventToFormValues(e: Event): EventFormValues {
  const eventType = coerceEnum(e.eventType, FORM_EVENT_TYPES, EventTypeEnum.Community);
  const visibility = coerceEnum(e.visibility, FORM_VISIBILITIES, EventVisibility.Public);
  return {
    title: e.title,
    description: e.description,
    location: e.location,
    latitude: e.latitude,
    longitude: e.longitude,
    startDatetime: e.startDatetime ? e.startDatetime.toISOString() : null,
    endDatetime: e.endDatetime ? e.endDatetime.toISOString() : null,
    datetimeTbd: e.datetimeTbd,
    eventType,
    visibility,
    invitePermission: coerceEnum(
      e.invitePermission,
      FORM_INVITE_PERMISSIONS,
      InvitePermission.AllMembers,
    ),
    rsvpEnabled: e.rsvpEnabled,
    allowPlusOnes: e.allowPlusOnes,
    maxAttendees: e.maxAttendees,
    whatsappLink: e.whatsappLink,
    partifulLink: e.partifulLink,
    otherLink: e.otherLink,
    price: e.price,
    venmoLink: fromVenmoUrl(e.venmoLink),
    cashappLink: fromCashAppUrl(e.cashappLink),
    zelleInfo: e.zelleInfo,
    coHostIds: e.coHostIds,
    tagIds: e.tags.map((t) => t.id),
    status: coerceEnum(e.status, FORM_STATUSES, EventStatusEnum.Active),
  };
}
