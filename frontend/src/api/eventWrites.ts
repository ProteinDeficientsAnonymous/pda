// Event create/edit + photo upload mutations.
//
// Separated from events.ts so phase-2 read hooks stay focused. The POST path
// has a hard 10/day rate limit per backend _events.py; we surface that as a
// dedicated error so the UI can show a sane message.

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import { extractApiErrorOr, getApiStatus } from './apiErrors';
import { useAuthStore } from '@/auth/store';
import { eventKeys } from './events';
import { mapEvent, type WireEvent } from './eventMapper';
import {
  EventStatus as EventStatusEnum,
  EventType as EventTypeEnum,
  EventVisibility,
  InvitePermission,
  type Event,
} from '@/models/event';
import { reportError } from '@/utils/errorReporter';
import { fromCashAppUrl, fromVenmoUrl, toCashAppUrl, toVenmoUrl } from '@/utils/paymentHandle';

const ROUTE = '/events';

export type EventStatus = (typeof EventStatusEnum)[keyof typeof EventStatusEnum];

export type VisibilityChoice = 'official' | 'public' | 'members_only' | 'invite_only';

export function visibilityChoiceToFields(choice: VisibilityChoice): {
  visibility: EventFormValues['visibility'];
  eventType: EventFormValues['eventType'];
} {
  if (choice === 'official') return { visibility: 'public', eventType: 'official' };
  return { visibility: choice, eventType: 'community' };
}

export function fieldsToVisibilityChoice(
  visibility: EventFormValues['visibility'],
  eventType: EventFormValues['eventType'],
): VisibilityChoice {
  if (eventType === 'official') return 'official';
  return visibility as VisibilityChoice;
}

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
  visibilityChoice: VisibilityChoice;
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
  status: EventStatus;
}

type WireBody = Record<string, unknown>;

// Per-field mapping from a form value to its wire key + serialized value.
// `visibilityChoice` is virtual on the wire — it expands into `visibility` +
// `event_type` — so it's handled separately rather than living in this map.
type WireField = readonly [wireKey: string, encode: (values: EventFormValues) => unknown];

const FIELD_TO_WIRE: Partial<Record<keyof EventFormValues, WireField>> = {
  title: ['title', (v) => v.title],
  description: ['description', (v) => v.description],
  location: ['location', (v) => v.location],
  latitude: ['latitude', (v) => v.latitude],
  longitude: ['longitude', (v) => v.longitude],
  startDatetime: ['start_datetime', (v) => v.startDatetime],
  endDatetime: ['end_datetime', (v) => v.endDatetime],
  datetimeTbd: ['datetime_tbd', (v) => v.datetimeTbd],
  invitePermission: ['invite_permission', (v) => v.invitePermission],
  rsvpEnabled: ['rsvp_enabled', (v) => v.rsvpEnabled],
  allowPlusOnes: ['allow_plus_ones', (v) => v.allowPlusOnes],
  maxAttendees: ['max_attendees', (v) => v.maxAttendees],
  whatsappLink: ['whatsapp_link', (v) => v.whatsappLink],
  partifulLink: ['partiful_link', (v) => v.partifulLink],
  otherLink: ['other_link', (v) => v.otherLink],
  price: ['price', (v) => v.price],
  venmoLink: ['venmo_link', (v) => toVenmoUrl(v.venmoLink)],
  cashappLink: ['cashapp_link', (v) => toCashAppUrl(v.cashappLink)],
  zelleInfo: ['zelle_info', (v) => v.zelleInfo],
  coHostIds: ['co_host_ids', (v) => v.coHostIds],
  status: ['status', (v) => v.status],
};

function toWireBody(values: EventFormValues): WireBody {
  const { visibility, eventType } = visibilityChoiceToFields(values.visibilityChoice);
  const body: WireBody = { visibility, event_type: eventType };
  for (const field of Object.values(FIELD_TO_WIRE)) {
    const [wireKey, encode] = field;
    body[wireKey] = encode(values);
  }
  return body;
}

// Build a PATCH body from only the keys present in the Partial. Avoids the
// unsafe Partial→full cast: we never read a field that wasn't provided.
// `visibilityChoice` (if present) expands into `visibility` + `event_type`.
export function toPartialWireBody(values: Partial<EventFormValues>): WireBody {
  const body: WireBody = {};
  for (const key of Object.keys(values) as (keyof EventFormValues)[]) {
    if (values[key] === undefined) continue;
    if (key === 'visibilityChoice') {
      const choice = values.visibilityChoice;
      if (choice === undefined) continue;
      const { visibility, eventType } = visibilityChoiceToFields(choice);
      body.visibility = visibility;
      body.event_type = eventType;
      continue;
    }
    const field = FIELD_TO_WIRE[key];
    if (!field) continue;
    const [wireKey, encode] = field;
    body[wireKey] = encode(values as EventFormValues);
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

export function useUploadEventPhoto(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async (blob: Blob) => {
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
    onError: (err) => {
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
    visibilityChoice: 'public',
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
    visibilityChoice: fieldsToVisibilityChoice(visibility, eventType),
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
    status: coerceEnum(e.status, FORM_STATUSES, EventStatusEnum.Active),
  };
}
