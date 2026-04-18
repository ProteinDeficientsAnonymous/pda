import { describe, it, expect } from 'vitest';
import { parseIsoDate, formatEventDateTime, formatDayHeader } from './datetime';

describe('parseIsoDate', () => {
  it('parses ISO 8601 string', () => {
    const result = parseIsoDate('2026-04-15T18:00:00Z');
    expect(result.getFullYear()).toBe(2026);
    expect(result.getMonth()).toBe(3);
    expect(result.getDate()).toBe(15);
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
    expect(result).toMatch(/Apr 15/);
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
    expect(parts[1].trim()).toMatch(/^\d+:\d{2} [AP]M$/);
  });

  it('uses arrow and full date for multi-day events', () => {
    const start = new Date('2026-04-15T18:00:00');
    const end = new Date('2026-04-16T12:00:00');
    const result = formatEventDateTime(start, end);
    expect(result).toContain('→');
    expect(result).not.toContain('–');
    const parts = result.split('→');
    expect(parts[0]).toMatch(/Apr 15/);
    expect(parts[1]).toMatch(/Apr 16/);
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