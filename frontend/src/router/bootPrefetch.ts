import { prefetchCalendarEvents } from '@/api/calendarEvents';
import { queryClient } from '@/api/queryClient';
import { calendarRangeFor, parseDate, parseView } from '@/screens/calendar/calendarParams';

const CALENDAR_PATH = '/calendar';

function isCalendarLanding(): boolean {
  return window.location.pathname.toLowerCase().replace(/\/+$/, '') === CALENDAR_PATH;
}

// Overlaps the chunk download with AuthBoot's session restore.
export function preloadCalendarChunk(factory: () => Promise<unknown>): void {
  if (!isCalendarLanding()) return;
  // A failed preload is fine: lazyWithRetry retries when the route renders.
  factory().catch(() => undefined);
}

/** Landing on the calendar: fetch its events alongside /me instead of after boot and the chunk load. */
export function prefetchCalendarOnBoot(token: string | null): void {
  if (!isCalendarLanding()) return;
  const params = new URLSearchParams(window.location.search);
  const range = calendarRangeFor(parseView(params.get('view')), parseDate(params.get('date')));
  void prefetchCalendarEvents(queryClient, range, token);
}
