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

export type EventStatus = 'active' | 'draft' | 'cancelled';

export interface EventFormValues {
  title: string;
  description: string;
  location: string;
  startDatetime: string; // ISO
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
  invitedUserIds: string[];
  status: EventStatus;
}

type WireBody = Record<string, unknown>;

function toWireBody(values: EventFormValues): WireBody {
  return {
    title: values.title,
    description: values.description,
    location: values.location,
    start_datetime: values.startDatetime,
    end_datetime: values.endDatetime,
    datetime_tbd: values.datetimeTbd,
    event_type: values.eventType,
    visibility: values.visibility,
    invite_permission: values.invitePermission,
    rsvp_enabled: values.rsvpEnabled,
    allow_plus_ones: values.allowPlusOnes,
    max_attendees: values.maxAttendees,
    whatsapp_link: values.whatsappLink,
    partiful_link: values.partifulLink,
    other_link: values.otherLink,
    price: values.price,
    venmo_link: values.venmoLink,
    cashapp_link: values.cashappLink,
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
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't save the event — try again";
}

export function emptyEventFormValues(): EventFormValues {
  return {
    title: '',
    description: '',
    location: '',
    startDatetime: '',
    endDatetime: null,
    datetimeTbd: false,
    eventType: 'community',
    visibility: 'members_only',
    invitePermission: 'all_members',
    rsvpEnabled: true,
    allowPlusOnes: false,
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
    startDatetime: e.startDatetime.toISOString(),
    endDatetime: e.endDatetime ? e.endDatetime.toISOString() : null,
    datetimeTbd: e.datetimeTbd,
    eventType: e.eventType as 'community' | 'official',
    visibility: e.visibility as 'public' | 'members_only' | 'invite_only',
    invitePermission: e.invitePermission as 'all_members' | 'co_hosts_only',
    rsvpEnabled: e.rsvpEnabled,
    allowPlusOnes: e.allowPlusOnes,
    maxAttendees: e.maxAttendees,
    whatsappLink: e.whatsappLink,
    partifulLink: e.partifulLink,
    otherLink: e.otherLink,
    price: e.price,
    venmoLink: e.venmoLink,
    cashappLink: e.cashappLink,
    zelleInfo: e.zelleInfo,
    coHostIds: e.coHostIds,
    invitedUserIds: e.invitedUserIds,
    status: e.status as EventStatus,
  };
}
