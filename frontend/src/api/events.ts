// Events API — list + detail. Uses apiClient (sends Bearer if authed, still
// succeeds unauthed via optional_jwt on the backend).
//
// The backend returns different field sets for unauthed vs authed callers
// (member-only fields blanked), so we re-fetch on auth transition by wiring
// the query key to the accessToken presence, not the user id.

import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import type { EventStatus } from '@/models/event';
import { mapEvent, type WireEvent } from './eventMapper';

type EventListStatus = typeof EventStatus.Draft | typeof EventStatus.Cancelled;

export const eventKeys = {
  all: ['events'] as const,
  list: (isAuthed: boolean, status?: EventListStatus) =>
    ['events', 'list', { authed: isAuthed, status: status ?? 'active' }] as const,
  detail: (id: string, isAuthed: boolean) =>
    ['events', 'detail', id, { authed: isAuthed }] as const,
};

export async function fetchEvents(status?: EventListStatus): Promise<Event[]> {
  const { data } = await apiClient.get<WireEvent[]>('/api/community/events/', {
    params: status ? { status } : undefined,
  });
  return data.map(mapEvent);
}

export async function fetchEvent(id: string): Promise<Event> {
  const { data } = await apiClient.get<WireEvent>(`/api/community/events/${id}/`);
  return mapEvent(data);
}

export function useEvents(status?: EventListStatus) {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useQuery({
    queryKey: eventKeys.list(isAuthed, status),
    queryFn: () => fetchEvents(status),
    // Drafts and cancelled lists require auth — backend returns 403 otherwise.
    enabled: status ? isAuthed : true,
  });
}

export function useEvent(id: string | undefined, placeholder?: Event) {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useQuery({
    queryKey: eventKeys.detail(id ?? '', isAuthed),
    queryFn: () => fetchEvent(id ?? ''),
    enabled: Boolean(id),
    ...(placeholder ? { placeholderData: placeholder } : {}),
  });
}
