import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import type { RsvpStatus } from '@/models/event';

import { apiClient } from './client';
import { eventCommentKeys } from './eventComments';
import { mapEvent, type WireEvent } from './eventMapper';
import { eventKeys, invalidateEventGuests } from './events';
import { eventStatsKeys } from './eventStats';

type RsvpInput = (typeof RsvpStatus)[keyof typeof RsvpStatus];

interface SetRsvpArgs {
  eventId: string;
  status: RsvpInput;
  hasPlusOne?: boolean;
  // Not persisted server-side — a non-empty comment is posted once, as a
  // public EventComment or a host-only decline notification.
  comment?: string;
  paidConfirmed?: boolean;
  questionnaireResponses?: Record<string, string | string[]>;
}

// EventDetailScreen's :id route param can be the event's uuid or slug, so the cache key varies.
function isDetailQueryForEvent(queryKey: readonly unknown[], event: Pick<Event, 'id' | 'slug'>) {
  return queryKey[1] === 'detail' && (queryKey[2] === event.id || queryKey[2] === event.slug);
}

function updateCaches(qc: ReturnType<typeof useQueryClient>, event: Event, isAuthed: boolean) {
  qc.setQueryData(eventKeys.detail(event.id, isAuthed), event);
  qc.setQueriesData<Event | undefined>(
    { queryKey: eventKeys.all, predicate: (query) => isDetailQueryForEvent(query.queryKey, event) },
    () => event,
  );
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
    mutationFn: async ({
      eventId,
      status,
      hasPlusOne = false,
      comment,
      paidConfirmed,
      questionnaireResponses = {},
    }: SetRsvpArgs) => {
      const { data } = await apiClient.post<WireEvent>(`/api/community/events/${eventId}/rsvp/`, {
        status,
        has_plus_one: hasPlusOne,
        questionnaire_responses: questionnaireResponses,
        ...(comment === undefined ? {} : { comment }),
        ...(paidConfirmed ? { paid_confirmed: true } : {}),
      });
      return mapEvent(data);
    },
    onSuccess: (event) => {
      updateCaches(qc, event, isAuthed);
      // Host stats include cancellations derived from CANT_GO rows — if this
      // user just flipped in/out of that status, the panel must re-fetch.
      void qc.invalidateQueries({ queryKey: eventStatsKeys.detail(event.id) });
      // can_post on the comments list depends on RSVP existence — refresh it.
      void qc.invalidateQueries({ queryKey: eventCommentKeys.list(event.id) });
      invalidateEventGuests(qc, event.id);
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
      // DELETE returns 204, so we can't patch from the response — invalidate instead.
      void qc.invalidateQueries({
        queryKey: eventKeys.all,
        predicate: (query) =>
          query.queryKey[1] === 'detail' &&
          (query.queryKey[2] === eventId ||
            (query.state.data as Event | undefined)?.id === eventId),
      });
      void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
      void qc.invalidateQueries({ queryKey: eventStatsKeys.detail(eventId) });
      // can_post on the comments list depends on RSVP existence — refresh it.
      void qc.invalidateQueries({ queryKey: eventCommentKeys.list(eventId) });
      invalidateEventGuests(qc, eventId);
    },
  });
}
