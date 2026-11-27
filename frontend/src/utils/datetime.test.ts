import { describe, expect, it } from 'vitest';

import {
  formatBirthday,
  formatDayHeader,
  formatEventDateTime,
  formatEventTime,
  formatVeganniversary,
  isSameEventDay,
  MONTH_OPTIONS,
  parseIsoDate,
} from './datetime';

describe('parseIsoDate', () => {
  it('parses ISO 8601 string', () => {
    const result = parseIsoDate('2026-04-15T18:00:00Z');
    expect(result.getFullYear()).toBe(2026);
    expect(result.getMonth()).toBe(3);
    expect(result.getDate()).toBe(15);
  });
});

describe('formatBirthday', () => {
  it('formats a birthday with a year as lowercase month day, year', () => {
    expect(formatBirthday({ month: 6, day: 15, year: 1990 })).toBe('june 15, 1990');
  });

  it('formats a birthday without a year as lowercase month day', () => {
    expect(formatBirthday({ month: 1, day: 1, year: null })).toBe('january 1');
  });

  it('formats a leap day without a year', () => {
    expect(formatBirthday({ month: 2, day: 29, year: null })).toBe('february 29');
  });
});

describe('formatVeganniversary', () => {
  it('formats month day, year when a day is set', () => {
    expect(formatVeganniversary({ month: 6, day: 15, year: 2019 })).toBe('june 15, 2019');
  });

  it('formats month year when day is omitted', () => {
    expect(formatVeganniversary({ month: 3, day: null, year: 2020 })).toBe('march 2020');
  });
});

describe('formatEventDateTime', () => {
  it('returns "date & time tbd" when datetimeTbd is true', () => {
    const start = new Date('2026-04-15T22:00:00Z');
    expect(formatEventDateTime(start, null, true)).toBe('date & time tbd');
  });

  it('formats in eastern time regardless of the viewer zone', () => {
    expect(formatEventDateTime(new Date('2026-04-15T19:00:00Z'), null)).toBe(
      'wed apr 15, 3:00 pm et',
    );
  });

  it('uses en-dash and end time only for same-day events', () => {
    const start = new Date('2026-04-15T19:00:00Z');
    const end = new Date('2026-04-16T00:00:00Z');
    expect(formatEventDateTime(start, end)).toBe('wed apr 15, 3:00 pm – 8:00 pm et');
  });

  it('uses arrow and full date for multi-day events', () => {
    const start = new Date('2026-04-15T22:00:00Z');
    const end = new Date('2026-04-16T16:00:00Z');
    expect(formatEventDateTime(start, end)).toBe('wed apr 15, 6:00 pm → thu apr 16, 12:00 pm et');
  });
});

describe('isSameEventDay', () => {
  it('compares calendar days in eastern time', () => {
    // 11pm et and 1am et the next day are the same utc day
    expect(isSameEventDay(new Date('2026-04-16T03:00:00Z'), new Date('2026-04-16T05:00:00Z'))).toBe(
      false,
    );
  });
});

describe('formatEventTime', () => {
  it('lowercases eastern-time output', () => {
    expect(formatEventTime(new Date('2026-07-04T13:05:00Z'), 'EEE h:mmaaa')).toBe('sat 9:05am');
  });
});

describe('formatDayHeader', () => {
  it('formats date as full weekday and month/day', () => {
    const date = new Date('2026-04-15T12:00:00');
    const result = formatDayHeader(date);
    expect(result).toMatch(/Wednesday/);
    expect(result).toMatch(/April/);
    expect(result).toMatch(/15/);
  });
});

describe('MONTH_OPTIONS', () => {
  it('lists the 12 lowercase months keyed 1-12', () => {
    expect(MONTH_OPTIONS).toHaveLength(12);
    expect(MONTH_OPTIONS[0]).toEqual({ value: '1', label: 'january' });
    expect(MONTH_OPTIONS[11]).toEqual({ value: '12', label: 'december' });
  });
});
