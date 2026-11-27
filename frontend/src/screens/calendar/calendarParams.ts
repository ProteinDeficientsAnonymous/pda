import type { View } from 'react-big-calendar';

import { type CalendarRange, monthRange, upcomingRange } from '@/api/calendarEvents';
import { parseEventDay, startOfEventDay } from '@/utils/datetime';

const VIEWS: View[] = ['month', 'week', 'day', 'agenda'];

export function parseView(raw: string | null): View {
  return VIEWS.find((v) => v === raw) ?? 'month';
}

export function parseDate(raw: string | null): Date {
  return (raw ? parseEventDay(raw) : null) ?? startOfEventDay(new Date());
}

// The list view shows everything upcoming; the grid views show the month around `date`.
export function calendarRangeFor(view: View, date: Date): CalendarRange {
  return view === 'agenda' ? upcomingRange() : monthRange(date);
}
