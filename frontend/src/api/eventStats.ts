import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type {
  AttendanceStatusValue,
  EventCancellation,
  EventStats,
  RsvpInputStatus,
} from '@/models/event';

import { attendanceReportKey } from './attendanceReport';
import { apiClient } from './client';
import { checkInReportKeys } from './eventCheckInReport';
import { mapEvent, type WireEvent } from './eventMapper';
import { invalidateEventDetail, setEventDetailData } from './events';
import { USERS_KEY } from './users';

interface WireCancellation {
  user_id: string;
  name: string;
  cancelled_at: string;
  days_before_event: number;
  same_day: boolean;
  previous_status: string | null;
}

interface WireStats {
  going_count: number;
  maybe_count: number;
  cant_go_count: number;
  no_response_count: number;
  waitlisted_count: number;
  attended_count: number;
  didnt_go_count: number;
  not_marked_count: number;
  cancellations: WireCancellation[];
}

function mapCancellation(w: WireCancellation): EventCancellation {
  return {
    userId: w.user_id,
    name: w.name,
    cancelledAt: new Date(w.cancelled_at),
    daysBeforeEvent: w.days_before_event,
    sameDay: w.same_day,
    previousStatus: w.previous_status as EventCancellation['previousStatus'],
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
    didntGoCount: w.didnt_go_count,
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
    // GET /stats/ returns 403 for non-hosts; callers must gate this on host status.
    enabled: Boolean(eventId) && enabled,
  });
}

export function useSetAttendance(eventId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: {
      userId: string;
      attendance: AttendanceStatusValue;
      forPlusOne?: boolean;
    }) => {
      const { data } = await apiClient.post<WireEvent>(
        `/api/community/events/${eventId}/rsvps/${args.userId}/attendance/`,
        { attendance: args.attendance, for_plus_one: args.forPlusOne ?? false },
      );
      return mapEvent(data);
    },
    onSuccess: () => {
      invalidateEventDetail(qc, eventId);
      void qc.invalidateQueries({ queryKey: eventStatsKeys.detail(eventId) });
      void qc.invalidateQueries({ queryKey: checkInReportKeys.detail(eventId) });
      // attendance marks feed the admin report + members-list last_attended.
      void qc.invalidateQueries({ queryKey: attendanceReportKey });
      void qc.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
}

export function useSetGuestRsvp(eventId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { userId: string; status: RsvpInputStatus; hasPlusOne?: boolean }) => {
      const { data } = await apiClient.post<WireEvent>(
        `/api/community/events/${eventId}/rsvps/${args.userId}/rsvp/`,
        { status: args.status, has_plus_one: args.hasPlusOne ?? false },
      );
      return mapEvent(data);
    },
    onSuccess: (event) => {
      setEventDetailData(qc, event, true);
      void qc.invalidateQueries({ queryKey: eventStatsKeys.detail(eventId) });
    },
  });
}

export function useSetGuestPayment(eventId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { userId: string; paidConfirmed: boolean }) => {
      const { data } = await apiClient.patch<WireEvent>(
        `/api/community/events/${eventId}/rsvps/${args.userId}/payment/`,
        { paid_confirmed: args.paidConfirmed },
      );
      return mapEvent(data);
    },
    onSuccess: (event) => {
      setEventDetailData(qc, event, true);
    },
  });
}

export function useRemoveGuestRsvp(eventId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { userId: string }) => {
      await apiClient.delete(`/api/community/events/${eventId}/rsvps/${args.userId}/rsvp/`);
    },
    onSuccess: () => {
      invalidateEventDetail(qc, eventId);
      void qc.invalidateQueries({ queryKey: eventStatsKeys.detail(eventId) });
    },
  });
}
