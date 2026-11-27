import { describe, expect, it } from 'vitest';

import { formatAgendaTime, formatEventTimeRange } from './calendarFormats';

describe('calendar time formats', () => {
  it('formats agenda times in et', () => {
    expect(formatAgendaTime(new Date('2026-08-12T19:00:00Z'))).toBe('3:00pm et');
  });

  it('formats event time ranges in et', () => {
    expect(
      formatEventTimeRange({
        start: new Date('2026-08-12T19:00:00Z'),
        end: new Date('2026-08-13T00:00:00Z'),
      }),
    ).toBe('3:00pm – 8:00pm et');
  });
});
