import { describe, expect, it } from 'vitest';

import { toEventWallClock } from '@/utils/datetime';

import { formatAgendaTime, formatEventTimeRange } from './calendarFormats';

describe('calendar time formats', () => {
  it('formats agenda times in et', () => {
    expect(formatAgendaTime(toEventWallClock(new Date('2026-08-12T19:00:00Z')))).toBe('3:00pm et');
  });

  it('formats event time ranges in et', () => {
    expect(
      formatEventTimeRange({
        start: toEventWallClock(new Date('2026-08-12T19:00:00Z')),
        end: toEventWallClock(new Date('2026-08-13T00:00:00Z')),
      }),
    ).toBe('3:00pm – 8:00pm et');
  });
});
