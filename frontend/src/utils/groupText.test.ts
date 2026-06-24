import { afterEach, describe, expect, it, vi } from 'vitest';
import type { EventGuest } from '@/models/event';
import { AttendanceStatus, RsvpServerStatus } from '@/models/event';
import { buildSmsUri, collectRecipients, isSmsSupported } from './groupText';

function guest(overrides: Partial<EventGuest>): EventGuest {
  return {
    userId: 'u',
    name: 'someone',
    status: RsvpServerStatus.Attending,
    phone: null,
    photoUrl: '',
    hasPlusOne: false,
    attendance: AttendanceStatus.Unknown,
    ...overrides,
  };
}

describe('collectRecipients', () => {
  it("collects phones across all rsvp statuses, including can't go", () => {
    const guests = [
      guest({ userId: 'a', phone: '+15551112222', status: RsvpServerStatus.Attending }),
      guest({ userId: 'b', phone: '+15553334444', status: RsvpServerStatus.Maybe }),
      guest({ userId: 'c', phone: '+15555556666', status: RsvpServerStatus.CantGo }),
      guest({ userId: 'd', phone: '+15557778888', status: RsvpServerStatus.Waitlisted }),
    ];
    expect(collectRecipients(guests).phones).toEqual([
      '+15551112222',
      '+15553334444',
      '+15555556666',
      '+15557778888',
    ]);
  });

  it('excludes guests with no phone and counts them', () => {
    const guests = [
      guest({ userId: 'a', phone: '+15551112222' }),
      guest({ userId: 'b', phone: null }),
      guest({ userId: 'c', phone: '   ' }),
    ];
    const result = collectRecipients(guests);
    expect(result.phones).toEqual(['+15551112222']);
    expect(result.skippedCount).toBe(2);
  });

  it('dedupes repeated numbers without counting them as skipped', () => {
    const guests = [
      guest({ userId: 'a', phone: '+15551112222' }),
      guest({ userId: 'b', phone: '+15551112222' }),
    ];
    const result = collectRecipients(guests);
    expect(result.phones).toEqual(['+15551112222']);
    expect(result.skippedCount).toBe(0);
  });

  it('returns an empty result for an empty guest list', () => {
    expect(collectRecipients([])).toEqual({ phones: [], skippedCount: 0 });
  });
});

describe('buildSmsUri', () => {
  it('comma-joins numbers into an sms: uri', () => {
    expect(buildSmsUri(['+15551112222', '+15553334444'])).toBe('sms:+15551112222,+15553334444');
  });

  it('returns null when there are no numbers', () => {
    expect(buildSmsUri([])).toBeNull();
  });
});

describe('isSmsSupported', () => {
  const original = navigator.userAgent;

  afterEach(() => {
    Object.defineProperty(navigator, 'userAgent', { value: original, configurable: true });
  });

  it('is true on a mobile user agent', () => {
    Object.defineProperty(navigator, 'userAgent', {
      value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)',
      configurable: true,
    });
    expect(isSmsSupported()).toBe(true);
  });

  it('is false on a desktop user agent', () => {
    Object.defineProperty(navigator, 'userAgent', {
      value: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
      configurable: true,
    });
    expect(isSmsSupported()).toBe(false);
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});
