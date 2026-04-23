import { describe, it, expect } from 'vitest';
import { formatPhone } from './formatPhone';

describe('formatPhone', () => {
  it('formats US numbers as (xxx) xxx-xxxx with no country code', () => {
    expect(formatPhone('+12125551234')).toBe('(212) 555-1234');
  });

  it('formats UK numbers in international style', () => {
    expect(formatPhone('+442079460958')).toBe('+44 20 7946 0958');
  });

  it('formats Canadian numbers in international style (not confused with US)', () => {
    // +1 416 is Toronto — same country code as US but parser distinguishes.
    expect(formatPhone('+14165550100')).toBe('+1 416 555 0100');
  });

  it('formats German numbers in international style', () => {
    expect(formatPhone('+493012345678')).toBe('+49 30 12345678');
  });

  it('returns the raw input for an unparseable string', () => {
    expect(formatPhone('not-a-number')).toBe('not-a-number');
  });

  it('returns an empty string as-is', () => {
    expect(formatPhone('')).toBe('');
  });

  it('returns the raw input when missing a leading "+" (no country context)', () => {
    // Stored numbers are always E.164 with a "+"; if somehow we get a bare
    // digit string, we pass through rather than guessing the country.
    expect(formatPhone('12125551234')).toBe('12125551234');
  });
});
