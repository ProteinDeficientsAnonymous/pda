import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type {
  AttendanceStatusValue,
  Event,
  EventCancellation,
  EventStats,
  RsvpInputStatus,
} from '@/models/event';
import { RsvpServerStatus } from '@/models/event';

import { attendanceReportKey } from './attendanceReport';
import { apiClient } from './client';
import { checkInReportKeys } from './eventCheckInReport';
import { mapEvent, type WireEvent } from './eventMapper';
import {
  eventKeys,
  invalidateEventDetail,
  invalidateEventGuests,
  setEventDetailData,
} from './events';
import { USERS_KEY } from './users';

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
      invalidateEventGuests(qc, eventId);
      void qc.invalidateQueries({ queryKey: eventStatsKeys.detail(eventId) });
    },
  });
}

export function withWaitlistOrder(event: Event, userIds: string[]): Event {
  const rank = new Map(userIds.map((id, i) => [id, i]));
  const isWaitlisted = (g: Event['guests'][number]) => g.status === RsvpServerStatus.Waitlisted;
  const waitlisted = event.guests
    .filter(isWaitlisted)
    .sort((a, b) => (rank.get(a.userId) ?? rank.size) - (rank.get(b.userId) ?? rank.size));
  let next = 0;
  return {
    ...event,
    guests: event.guests.map((g) => (isWaitlisted(g) ? (waitlisted[next++] ?? g) : g)),
  };
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

export function useReorderWaitlist(eventId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { userIds: string[] }) => {
      const { data } = await apiClient.put<WireEvent>(
        `/api/community/events/${eventId}/waitlist/order/`,
        { user_ids: args.userIds },
      );
      return mapEvent(data);
    },
    // Optimistic so a dropped row stays put instead of snapping back until the save lands.
    onMutate: async (args: { userIds: string[] }) => {
      const key = eventKeys.detail(eventId, true);
      await qc.cancelQueries({ queryKey: key });
      const previous = qc.getQueryData<Event>(key);
      if (previous) setEventDetailData(qc, withWaitlistOrder(previous, args.userIds), true);
      return { previous };
    },
    onError: (_err, _args, context) => {
      if (context?.previous) setEventDetailData(qc, context.previous, true);
    },
    onSuccess: (event) => {
      setEventDetailData(qc, event, true);
      invalidateEventGuests(qc, eventId);
      void qc.invalidateQueries({ queryKey: eventStatsKeys.detail(eventId) });
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
      invalidateEventGuests(qc, eventId);
      void qc.invalidateQueries({ queryKey: eventStatsKeys.detail(eventId) });
    },
  });
}
