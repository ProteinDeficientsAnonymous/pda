// RSVP mutations. The backend returns the full updated Event on POST/DELETE,
// so we setQueryData instead of invalidating — one fewer round-trip than the
// Flutter app does and the UI updates in the same tick as the mutation.
//
// Input statuses: attending | maybe | cant_go. `waitlisted` is never a valid
// input — the server assigns it automatically when an attending request lands
// over capacity.

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import { useAuthStore } from '@/auth/store';
import { eventKeys } from './events';
import { eventStatsKeys } from './eventStats';
import { mapEvent, type WireEvent } from './eventMapper';
import type { Event } from '@/models/event';
import type { RsvpStatus } from '@/models/event';

type RsvpInput = (typeof RsvpStatus)[keyof typeof RsvpStatus];

interface SetRsvpArgs {
  eventId: string;
  status: RsvpInput;
  hasPlusOne?: boolean;
}

function updateCaches(qc: ReturnType<typeof useQueryClient>, event: Event, isAuthed: boolean) {
  qc.setQueryData(eventKeys.detail(event.id, isAuthed), event);
  // Also patch the list cache if we've got it. The list endpoint returns
  // fewer fields than detail, so we merge conservatively.
  qc.setQueryData<Event[] | undefined>(eventKeys.list(isAuthed), (prev) => {
    if (!prev) return prev;
    return prev.map((e) => (e.id === event.id ? { ...e, ...event } : e));
  });
}

export function useSetRsvp() {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async ({ eventId, status, hasPlusOne = false }: SetRsvpArgs) => {
      const { data } = await apiClient.post<WireEvent>(`/api/community/events/${eventId}/rsvp/`, {
        status,
        has_plus_one: hasPlusOne,
      });
      return mapEvent(data);
    },
    onSuccess: (event) => {
      updateCaches(qc, event, isAuthed);
      // Host stats include cancellations derived from CANT_GO rows — if this
      // user just flipped in/out of that status, the panel must re-fetch.
      void qc.invalidateQueries({ queryKey: eventStatsKeys.detail(event.id) });
    },
  });
}

export function useRemoveRsvp() {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async (eventId: string) => {
      await apiClient.delete(`/api/community/events/${eventId}/rsvp/`);
      return eventId;
    },
    onSuccess: (eventId) => {
      // DELETE returns 204, so we can't patch from the response. Just
      // invalidate — cheaper than a second round-trip.
      void qc.invalidateQueries({ queryKey: eventKeys.detail(eventId, isAuthed) });
      void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
      void qc.invalidateQueries({ queryKey: eventStatsKeys.detail(eventId) });
    },
  });
}
