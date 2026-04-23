// Host-only event stats + attendance mutations.
//
// The GET /stats/ endpoint returns 403 for non-hosts, so components must gate
// the `enabled` flag on host status themselves to avoid noisy error toasts.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import { eventKeys } from './events';
import { mapEvent, type WireEvent } from './eventMapper';
import type { AttendanceStatusValue, EventCancellation, EventStats } from '@/models/event';

interface WireCancellation {
  user_id: string;
  name: string;
  cancelled_at: string;
  days_before_event: number;
}

interface WireStats {
  going_count: number;
  maybe_count: number;
  cant_go_count: number;
  no_response_count: number;
  waitlisted_count: number;
  attended_count: number;
  no_show_count: number;
  not_marked_count: number;
  cancellations: WireCancellation[];
}

function mapCancellation(w: WireCancellation): EventCancellation {
  return {
    userId: w.user_id,
    name: w.name,
    cancelledAt: new Date(w.cancelled_at),
    daysBeforeEvent: w.days_before_event,
  };
}

function mapStats(w: WireStats): EventStats {
  return {
    goingCount: w.going_count,
    maybeCount: w.maybe_count,
    cantGoCount: w.cant_go_count,
    noResponseCount: w.no_response_count,
    waitlistedCount: w.waitlisted_count,
    attendedCount: w.attended_count,
    noShowCount: w.no_show_count,
    notMarkedCount: w.not_marked_count,
    cancellations: w.cancellations.map(mapCancellation),
  };
}

export const eventStatsKeys = {
  detail: (eventId: string) => ['event-stats', eventId] as const,
};

export function useEventStats(eventId: string | undefined, enabled: boolean) {
  const id = eventId ?? '';
  return useQuery({
    queryKey: eventStatsKeys.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.get<WireStats>(`/api/community/events/${id}/stats/`);
      return mapStats(data);
    },
    enabled: Boolean(eventId) && enabled,
  });
}

export function useSetAttendance(eventId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { userId: string; attendance: AttendanceStatusValue }) => {
      const { data } = await apiClient.post<WireEvent>(
        `/api/community/events/${eventId}/rsvps/${args.userId}/attendance/`,
        { attendance: args.attendance },
      );
      return mapEvent(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: eventKeys.detail(eventId, true) });
      void qc.invalidateQueries({ queryKey: eventStatsKeys.detail(eventId) });
    },
  });
}
