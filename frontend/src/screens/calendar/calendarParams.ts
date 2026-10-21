import { isValid, parseISO } from 'date-fns';
import type { View } from 'react-big-calendar';

import { type CalendarRange, monthRange, upcomingRange } from '@/api/calendarEvents';

const VIEWS: View[] = ['month', 'week', 'day', 'agenda'];

export function parseView(raw: string | null): View {
  return VIEWS.find((v) => v === raw) ?? 'month';
}

export function parseDate(raw: string | null): Date {
  if (!raw) return new Date();
  const parsed = parseISO(raw);
  return isValid(parsed) ? parsed : new Date();
}

// The list view shows everything upcoming; the grid views show the month around `date`.
export function calendarRangeFor(view: View, date: Date): CalendarRange {
  return view === 'agenda' ? upcomingRange() : monthRange(date);
}
