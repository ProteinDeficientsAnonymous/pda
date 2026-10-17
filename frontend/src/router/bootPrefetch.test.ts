import { afterEach, describe, expect, it, vi } from 'vitest';

import type * as CalendarEventsModule from '@/api/calendarEvents';
import { monthRange, prefetchCalendarEvents, upcomingRange } from '@/api/calendarEvents';
import { queryClient } from '@/api/queryClient';

import { prefetchCalendarOnBoot } from './bootPrefetch';

vi.mock('@/api/calendarEvents', async (importOriginal) => ({
  ...(await importOriginal<typeof CalendarEventsModule>()),
  prefetchCalendarEvents: vi.fn(() => Promise.resolve()),
}));

afterEach(() => {
  vi.clearAllMocks();
  window.history.pushState({}, '', '/');
});

describe('prefetchCalendarOnBoot', () => {
  it('prefetches the month in the url with the session token', () => {
    window.history.pushState({}, '', '/calendar?view=month&date=2026-03-10');

    prefetchCalendarOnBoot('tok-1');

    expect(prefetchCalendarEvents).toHaveBeenCalledWith(
      queryClient,
      monthRange(new Date(2026, 2, 10)),
      'tok-1',
    );
  });

  it('prefetches upcoming events anonymously for the list view', () => {
    window.history.pushState({}, '', '/calendar?view=agenda');

    prefetchCalendarOnBoot(null);

    expect(prefetchCalendarEvents).toHaveBeenCalledWith(queryClient, upcomingRange(), null);
  });

  it('skips every other landing page', () => {
    window.history.pushState({}, '', '/events/potluck');

    prefetchCalendarOnBoot('tok-1');

    expect(prefetchCalendarEvents).not.toHaveBeenCalled();
  });
});
