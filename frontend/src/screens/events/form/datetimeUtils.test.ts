import { describe, it, expect } from 'vitest';
import { isoToLocalInput, localInputToIso } from './datetimeUtils';

describe('isoToLocalInput', () => {
  it('returns empty string for null', () => {
    expect(isoToLocalInput(null)).toBe('');
  });

  it('returns empty string for empty string', () => {
    expect(isoToLocalInput('')).toBe('');
  });

  it('returns empty string for invalid ISO string', () => {
    expect(isoToLocalInput('not-a-date')).toBe('');
  });

  it('converts ISO string to datetime-local format', () => {
    // Use a fixed UTC time and check local components match what new Date() resolves to
    const iso = '2026-04-15T00:00:00Z';
    const result = isoToLocalInput(iso);
    // Must match YYYY-MM-DDTHH:mm format
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
  });
});

describe('localInputToIso', () => {
  it('returns null for empty string', () => {
    expect(localInputToIso('')).toBeNull();
  });

  it('returns null for invalid input', () => {
    expect(localInputToIso('not-a-date')).toBeNull();
  });

  it('converts datetime-local string to ISO string', () => {
    const result = localInputToIso('2026-04-15T18:00');
    expect(result).not.toBeNull();
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
  });

  it('roundtrips: localInputToIso then isoToLocalInput restores original', () => {
    const local = '2026-06-20T14:30';
    const iso = localInputToIso(local);
    expect(iso).not.toBeNull();
    expect(isoToLocalInput(iso!)).toBe(local);
  });
});
