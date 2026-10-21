import { afterEach, describe, expect, it, vi } from 'vitest';

import type * as CalendarEventsModule from '@/api/calendarEvents';
import { monthRange, prefetchCalendarEvents, upcomingRange } from '@/api/calendarEvents';
import { queryClient } from '@/api/queryClient';

import { prefetchCalendarOnBoot, preloadCalendarChunk } from './bootPrefetch';

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

  it('treats a trailing slash as the calendar', () => {
    window.history.pushState({}, '', '/calendar/');

    prefetchCalendarOnBoot(null);

    expect(prefetchCalendarEvents).toHaveBeenCalledOnce();
  });

  it('skips every other landing page', () => {
    window.history.pushState({}, '', '/events/potluck');

    prefetchCalendarOnBoot('tok-1');

    expect(prefetchCalendarEvents).not.toHaveBeenCalled();
  });
});

describe('preloadCalendarChunk', () => {
  it('starts the chunk download when landing on the calendar', () => {
    window.history.pushState({}, '', '/Calendar/?view=month');
    const factory = vi.fn(() => Promise.resolve({}));

    preloadCalendarChunk(factory);

    expect(factory).toHaveBeenCalledOnce();
  });

  it('does nothing on other paths', () => {
    window.history.pushState({}, '', '/events/abc');
    const factory = vi.fn(() => Promise.resolve({}));

    preloadCalendarChunk(factory);

    expect(factory).not.toHaveBeenCalled();
  });

  it('swallows a failed preload so the route can retry on render', async () => {
    window.history.pushState({}, '', '/calendar');
    const factory = vi.fn(() => Promise.reject(new Error('failed to fetch')));

    // Vitest fails the run on an unhandled rejection.
    preloadCalendarChunk(factory);
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(factory).toHaveBeenCalledOnce();
  });
});
