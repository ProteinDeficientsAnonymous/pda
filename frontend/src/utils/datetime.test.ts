import { describe, expect, it } from 'vitest';

import { formatBirthday, formatDayHeader, formatEventDateTime, parseIsoDate } from './datetime';

describe('parseIsoDate', () => {
  it('parses ISO 8601 string', () => {
    const result = parseIsoDate('2026-04-15T18:00:00Z');
    expect(result.getFullYear()).toBe(2026);
    expect(result.getMonth()).toBe(3);
    expect(result.getDate()).toBe(15);
  });
});

describe('formatBirthday', () => {
  it('formats a plain date as lowercase month day, year', () => {
    expect(formatBirthday('1990-06-15')).toBe('june 15, 1990');
  });

  it('does not shift the day across timezones', () => {
    // A UTC-parsed '2000-01-01' would render as dec 31, 1999 in negative offsets.
    expect(formatBirthday('2000-01-01')).toBe('january 1, 2000');
  });

  it('returns empty string for a malformed date', () => {
    expect(formatBirthday('not-a-date')).toBe('');
  });
});

describe('formatEventDateTime', () => {
  it('returns "date & time tbd" when datetimeTbd is true', () => {
    const start = new Date('2026-04-15T18:00:00');
    expect(formatEventDateTime(start, null, true)).toBe('date & time tbd');
  });

  it('returns start string only when end is null', () => {
    const start = new Date('2026-04-15T18:00:00');
    const result = formatEventDateTime(start, null);
    expect(result).toMatch(/apr 15/);
    expect(result).not.toContain('→');
    expect(result).not.toContain('–');
  });

  it('uses en-dash and end time only for same-day events', () => {
    const start = new Date('2026-04-15T18:00:00');
    const end = new Date('2026-04-15T21:00:00');
    const result = formatEventDateTime(start, end);
    expect(result).toContain('–');
    expect(result).not.toContain('→');
    // End portion is just time, not a full date
    const parts = result.split('–');
    expect(parts[1]!.trim()).toMatch(/^\d+:\d{2} [ap]m$/);
  });

  it('uses arrow and full date for multi-day events', () => {
    const start = new Date('2026-04-15T18:00:00');
    const end = new Date('2026-04-16T12:00:00');
    const result = formatEventDateTime(start, end);
    expect(result).toContain('→');
    expect(result).not.toContain('–');
    const parts = result.split('→');
    expect(parts[0]).toMatch(/apr 15/);
    expect(parts[1]).toMatch(/apr 16/);
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
