import { type QueryClient, useQuery } from '@tanstack/react-query';

import { useAuthStore } from '@/auth/store';
import type { Event, EventRsvpQuestion, EventStatus } from '@/models/event';

import { apiClient } from './client';
import { mapEvent, mapEventGuests, type WireEvent, type WireEventGuests } from './eventMapper';

type EventListStatus = typeof EventStatus.Draft | typeof EventStatus.Cancelled;

export const eventKeys = {
  all: ['events'] as const,
  list: (isAuthed: boolean, status?: EventListStatus) =>
    ['events', 'list', { authed: isAuthed, status: status ?? 'active' }] as const,
  detail: (id: string, isAuthed: boolean, token?: string) =>
    ['events', 'detail', id, { authed: isAuthed, token: token ?? '' }] as const,
  guests: (id: string, token?: string) => ['events', 'guests', id, { token: token ?? '' }] as const,
};

/**
 * Write an event into its detail cache under BOTH its uuid and its slug.
 * Routes use `eventPath` (slug when present), so a uuid-only write lands on a
 * key nothing is reading and the open page keeps showing stale data.
 */
export function setEventDetailData(
  qc: QueryClient,
  event: Event,
  isAuthed: boolean,
  token?: string,
): void {
  // token is omitted at every call site — all are host/admin mutations, never reachable by an rsvp-token holder.
  for (const key of new Set([event.id, event.slug].filter(Boolean))) {
    qc.setQueryData(eventKeys.detail(key, isAuthed, token), event);
  }
}

/**
 * Invalidate an event's detail cache. Callers often hold only one of the two
 * identifiers (a route param is a slug, a mutation arg is usually a uuid), so
 * match on the cached event itself rather than reconstructing an exact key.
 */
export function invalidateEventDetail(qc: QueryClient, eventIdOrSlug: string): void {
  void qc.invalidateQueries({
    queryKey: eventKeys.all,
    predicate: (query) => {
      if (query.queryKey[1] !== 'detail') return false;
      if (query.queryKey[2] === eventIdOrSlug) return true;
      const cached = query.state.data as Event | undefined;
      return cached?.id === eventIdOrSlug || cached?.slug === eventIdOrSlug;
    },
  });
}

export function invalidateEventGuests(qc: QueryClient, eventId: string): void {
  void qc.invalidateQueries({
    queryKey: eventKeys.all,
    predicate: (query) => query.queryKey[1] === 'guests' && query.queryKey[2] === eventId,
  });
}

/** Patch rsvpQuestions on every cached detail entry for this event (uuid or slug keys). */
export function patchEventDetailRsvpQuestions(
  qc: QueryClient,
  eventId: string,
  rsvpQuestions: EventRsvpQuestion[],
): void {
  for (const [key, cached] of qc.getQueriesData<Event>({ queryKey: eventKeys.all })) {
    if (key[1] !== 'detail' || !cached) continue;
    if (cached.id !== eventId && key[2] !== eventId) continue;
    qc.setQueryData(key, { ...cached, rsvpQuestions });
  }
}

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

export async function fetchEventGuests(
  id: string,
  token?: string,
): Promise<ReturnType<typeof mapEventGuests>> {
  const { data } = await apiClient.get<WireEventGuests>(`/api/community/events/${id}/guests/`, {
    params: token ? { token } : undefined,
  });
  return mapEventGuests(data);
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

/** Full signed guest photos; merge onto the live guest list, do not replace it. */
export function useEventGuests(id: string | undefined, token?: string) {
  return useQuery({
    queryKey: eventKeys.guests(id ?? '', token),
    queryFn: () => fetchEventGuests(id ?? '', token),
    enabled: Boolean(id),
  });
}
