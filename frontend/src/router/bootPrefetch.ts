import { prefetchCalendarEvents } from '@/api/calendarEvents';
import { queryClient } from '@/api/queryClient';
import { calendarRangeFor, parseDate, parseView } from '@/screens/calendar/calendarParams';

export const CALENDAR_PATH = '/calendar';

/** Landing on the calendar: fetch its events alongside /me instead of after boot and the chunk load. */
export function prefetchCalendarOnBoot(token: string | null): void {
  if (window.location.pathname.toLowerCase() !== CALENDAR_PATH) return;
  const params = new URLSearchParams(window.location.search);
  const range = calendarRangeFor(parseView(params.get('view')), parseDate(params.get('date')));
  void prefetchCalendarEvents(queryClient, range, token);
}
