import { afterEach, describe, expect, it, vi } from 'vitest';
import type { EventGuest } from '@/models/event';
import { AttendanceStatus, RsvpServerStatus } from '@/models/event';
import { makeEvent } from '@/test/fixtures';
import { buildSmsUri, collectRecipients, RecipientGroup } from './groupText';

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

const FOUR_STATUS_EVENT = makeEvent({
  guests: [
    guest({ userId: 'a', phone: '+15551112222', status: RsvpServerStatus.Attending }),
    guest({ userId: 'b', phone: '+15553334444', status: RsvpServerStatus.Maybe }),
    guest({ userId: 'c', phone: '+15555556666', status: RsvpServerStatus.CantGo }),
    guest({ userId: 'd', phone: '+15557778888', status: RsvpServerStatus.Waitlisted }),
  ],
});

describe('collectRecipients', () => {
  it('only collects phones for the selected groups', () => {
    const result = collectRecipients(FOUR_STATUS_EVENT, [
      RecipientGroup.Going,
      RecipientGroup.Maybe,
    ]);
    expect(result.phones).toEqual(['+15551112222', '+15553334444']);
  });

  it('includes every group when all are selected', () => {
    const result = collectRecipients(FOUR_STATUS_EVENT, [
      RecipientGroup.Going,
      RecipientGroup.Maybe,
      RecipientGroup.CantGo,
      RecipientGroup.Waitlisted,
    ]);
    expect(result.phones).toEqual(['+15551112222', '+15553334444', '+15555556666', '+15557778888']);
  });

  it('includes invited members when the invited group is selected', () => {
    const event = makeEvent({
      guests: [guest({ userId: 'a', phone: '+15551112222' })],
      invitedUserPhones: ['+15559990000', null],
    });
    const result = collectRecipients(event, [RecipientGroup.Going, RecipientGroup.Invited]);
    expect(result.phones).toEqual(['+15551112222', '+15559990000']);
    // The null invited phone (hidden from this viewer) counts as skipped.
    expect(result.skippedCount).toBe(1);
  });

  it('excludes guests with no phone and counts them', () => {
    const event = makeEvent({
      guests: [
        guest({ userId: 'a', phone: '+15551112222' }),
        guest({ userId: 'b', phone: null }),
        guest({ userId: 'c', phone: '   ' }),
      ],
    });
    const result = collectRecipients(event, [RecipientGroup.Going]);
    expect(result.phones).toEqual(['+15551112222']);
    expect(result.skippedCount).toBe(2);
  });

  it('dedupes repeated numbers without counting them as skipped', () => {
    const event = makeEvent({
      guests: [
        guest({ userId: 'a', phone: '+15551112222' }),
        guest({ userId: 'b', phone: '+15551112222' }),
      ],
    });
    const result = collectRecipients(event, [RecipientGroup.Going]);
    expect(result.phones).toEqual(['+15551112222']);
    expect(result.skippedCount).toBe(0);
  });

  it('returns an empty result when no groups are selected', () => {
    expect(collectRecipients(FOUR_STATUS_EVENT, [])).toEqual({ phones: [], skippedCount: 0 });
  });
});

describe('buildSmsUri', () => {
  const original = navigator.userAgent;

  function setUserAgent(value: string) {
    Object.defineProperty(navigator, 'userAgent', { value, configurable: true });
  }

  afterEach(() => {
    Object.defineProperty(navigator, 'userAgent', { value: original, configurable: true });
  });

  it('uses the /open?addresses= form on Apple platforms (multi-recipient works there)', () => {
    setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)');
    expect(buildSmsUri(['+15551112222', '+15553334444'])).toBe(
      'sms:/open?addresses=+15551112222,+15553334444',
    );
  });

  it('uses the /open?addresses= form on iOS', () => {
    setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)');
    expect(buildSmsUri(['+15551112222'])).toBe('sms:/open?addresses=+15551112222');
  });

  it('uses the plain comma form on non-Apple platforms (Android)', () => {
    setUserAgent('Mozilla/5.0 (Linux; Android 14)');
    expect(buildSmsUri(['+15551112222', '+15553334444'])).toBe('sms:+15551112222,+15553334444');
  });

  it('returns null when there are no numbers', () => {
    expect(buildSmsUri([])).toBeNull();
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});
