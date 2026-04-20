// Event create/edit + photo upload mutations.
//
// Separated from events.ts so phase-2 read hooks stay focused. The POST path
// has a hard 10/day rate limit per backend _events.py; we surface that as a
// dedicated error so the UI can show a sane message.

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { isAxiosError } from 'axios';
import { apiClient } from './client';
import { useAuthStore } from '@/auth/store';
import { eventKeys } from './events';
import { mapEvent, type WireEvent } from './eventMapper';
import type { Event } from '@/models/event';
import { fromCashAppUrl, fromVenmoUrl, toCashAppUrl, toVenmoUrl } from '@/utils/paymentHandle';

export type EventStatus = 'active' | 'draft' | 'cancelled';

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
  invitedUserIds: string[];
  status: EventStatus;
}

type WireBody = Record<string, unknown>;

function toWireBody(values: EventFormValues): WireBody {
  const { visibility, eventType } = visibilityChoiceToFields(values.visibilityChoice);
  return {
    title: values.title,
    description: values.description,
    location: values.location,
    latitude: values.latitude,
    longitude: values.longitude,
    start_datetime: values.startDatetime,
    end_datetime: values.endDatetime,
    datetime_tbd: values.datetimeTbd,
    event_type: eventType,
    visibility,
    invite_permission: values.invitePermission,
    rsvp_enabled: values.rsvpEnabled,
    allow_plus_ones: values.allowPlusOnes,
    max_attendees: values.maxAttendees,
    whatsapp_link: values.whatsappLink,
    partiful_link: values.partifulLink,
    other_link: values.otherLink,
    price: values.price,
    venmo_link: toVenmoUrl(values.venmoLink),
    cashapp_link: toCashAppUrl(values.cashappLink),
    zelle_info: values.zelleInfo,
    co_host_ids: values.coHostIds,
    invited_user_ids: values.invitedUserIds,
    status: values.status,
  };
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
  });
}

export function useUpdateEvent(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async (values: Partial<EventFormValues>) => {
      // Strip undefined: PATCH is partial. Falsy values other than undefined
      // should still be sent — false/""/null carry meaning.
      const full = values as EventFormValues;
      const wire = toWireBody(full);
      const body = Object.fromEntries(
        Object.entries(wire).filter(
          ([k]) => (values as Record<string, unknown>)[kebabToCamel(k)] !== undefined,
        ),
      );
      const { data } = await apiClient.patch<WireEvent>(`/api/community/events/${eventId}/`, body);
      return mapEvent(data);
    },
    onSuccess: (event) => {
      qc.setQueryData(eventKeys.detail(event.id, isAuthed), event);
      void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
    },
  });
}

function kebabToCamel(s: string): string {
  return s.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
}

// Archive (a.k.a. cancel) an event. The backend has no DELETE route for
// events — the only destructive path is PATCH status=cancelled. We always
// send notify_attendees=true so RSVPs get pinged; the backend no-ops the
// notification on draft→cancelled transitions.
export function useArchiveEvent(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async () => {
      const body: WireBody = {
        status: 'cancelled' satisfies EventStatus,
        notify_attendees: true,
      };
      const { data } = await apiClient.patch<WireEvent>(`/api/community/events/${eventId}/`, body);
      return mapEvent(data);
    },
    onSuccess: (event) => {
      qc.setQueryData(eventKeys.detail(event.id, isAuthed), event);
      void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
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
  });
}

export function extractEventError(err: unknown): string {
  if (isAxiosError(err)) {
    if (err.response?.status === 429) {
      return "you've hit the daily event-creation limit — try again tomorrow";
    }
    const data = err.response?.data as Record<string, unknown> | undefined;
    if (data) {
      // Django Ninja returns { detail: [{ type, loc, msg, ctx }, ...] }
      // for validation errors.
      if (typeof data.detail === 'string') return data.detail;
      if (Array.isArray(data.detail)) {
        const msgs = (data.detail as { msg?: string }[]).map((e) => e.msg).filter(Boolean);
        if (msgs.length > 0) return msgs.join(', ');
      }
    }
  }
  return "couldn't save the event — try again";
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
    visibility: 'members_only',
    visibilityChoice: 'members_only',
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
    invitedUserIds: [],
    status: 'active',
  };
}

export function eventToFormValues(e: Event): EventFormValues {
  return {
    title: e.title,
    description: e.description,
    location: e.location,
    latitude: e.latitude,
    longitude: e.longitude,
    startDatetime: e.startDatetime ? e.startDatetime.toISOString() : null,
    endDatetime: e.endDatetime ? e.endDatetime.toISOString() : null,
    datetimeTbd: e.datetimeTbd,
    eventType: e.eventType as 'community' | 'official',
    visibility: e.visibility as 'public' | 'members_only' | 'invite_only',
    visibilityChoice: fieldsToVisibilityChoice(
      e.visibility as 'public' | 'members_only' | 'invite_only',
      e.eventType as 'community' | 'official',
    ),
    invitePermission: e.invitePermission as 'all_members' | 'co_hosts_only',
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
    invitedUserIds: e.invitedUserIds,
    status: e.status as EventStatus,
  };
}
