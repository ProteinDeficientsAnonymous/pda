import { useQuery } from '@tanstack/react-query';

import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import type { EventStatus } from '@/models/event';

import { apiClient } from './client';
import { mapEvent, type WireEvent } from './eventMapper';

type EventListStatus = typeof EventStatus.Draft | typeof EventStatus.Cancelled;

export const eventKeys = {
  all: ['events'] as const,
  list: (isAuthed: boolean, status?: EventListStatus) =>
    ['events', 'list', { authed: isAuthed, status: status ?? 'active' }] as const,
  detail: (id: string, isAuthed: boolean, token?: string) =>
    ['events', 'detail', id, { authed: isAuthed, token: token ?? '' }] as const,
};

export async function fetchEvents(status?: EventListStatus): Promise<Event[]> {
  const { data } = await apiClient.get<WireEvent[]>('/api/community/events/', {
    params: status ? { status } : undefined,
  });
  return data.map(mapEvent);
}

export async function fetchEvent(id: string, token?: string): Promise<Event> {
  const { data } = await apiClient.get<WireEvent>(`/api/community/events/${id}/`, {
    params: token ? { token } : undefined,
  });
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

export function useEvent(id: string | undefined, placeholder?: Event, token?: string) {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useQuery({
    queryKey: eventKeys.detail(id ?? '', isAuthed, token),
    queryFn: () => fetchEvent(id ?? '', token),
    enabled: Boolean(id),
    ...(placeholder ? { placeholderData: placeholder } : {}),
  });
}
