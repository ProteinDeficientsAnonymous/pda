import { useQuery } from '@tanstack/react-query';
import { addDays, addMonths, format, parseISO, startOfDay, subDays } from 'date-fns';

import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';

import { apiClient } from './client';
import { mapEvent, type WireEvent } from './eventMapper';
import { eventKeys } from './events';
import type { operations } from './types.gen';

type ListEventsQuery = NonNullable<
  operations['community__events_list_events']['parameters']['query']
>;

// Any week or day view sits inside its month padded by a week, so one fetch per
// month serves the month, week and day views.
const MONTH_PAD_DAYS = 7;

export type CalendarRange = { month: string } | { upcomingFrom: string };

export function monthRange(date: Date): CalendarRange {
  return { month: format(date, 'yyyy-MM') };
}

// A day early so an end-less event from late last night, which the list shows as
// running for DEFAULT_EVENT_DURATION_MS, still reaches the list's own upcoming filter.
export function upcomingRange(now: Date = new Date()): CalendarRange {
  return { upcomingFrom: format(subDays(startOfDay(now), 1), 'yyyy-MM-dd') };
}

// The calendar never shows partiful/legacy imports, so it never asks for them.
export function calendarRangeParams(range: CalendarRange): ListEventsQuery {
  if ('upcomingFrom' in range) {
    return { start: parseISO(range.upcomingFrom).toISOString(), include_imported: false };
  }
  const first = parseISO(`${range.month}-01`);
  return {
    start: subDays(first, MONTH_PAD_DAYS).toISOString(),
    end: addDays(addMonths(first, 1), MONTH_PAD_DAYS).toISOString(),
    include_imported: false,
  };
}

// Under eventKeys.list so every list invalidation also refreshes the calendar.
export const calendarEventKeys = (isAuthed: boolean, range: CalendarRange) =>
  [...eventKeys.list(isAuthed), range] as const;

export async function fetchCalendarEvents(range: CalendarRange): Promise<Event[]> {
  const { data } = await apiClient.get<WireEvent[]>('/api/community/events/', {
    params: calendarRangeParams(range),
  });
  return data.map(mapEvent);
}

export function useCalendarEvents(range: CalendarRange) {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useQuery({
    queryKey: calendarEventKeys(isAuthed, range),
    queryFn: () => fetchCalendarEvents(range),
    // Hold the last range on screen while the next loads, but never across a
    // login/logout — member-only fields must not linger for a signed-out viewer.
    placeholderData: (prev, prevQuery) =>
      prevQuery?.queryKey[2].authed === isAuthed ? prev : undefined,
  });
}
