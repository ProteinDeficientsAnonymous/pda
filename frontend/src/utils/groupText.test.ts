import { afterEach, describe, expect, it } from 'vitest';

import type { TextRecipients } from '@/api/textRecipients';

import { availableGroups, buildSmsUri, collectPhones, RecipientGroup } from './groupText';

function recipients(overrides: Partial<TextRecipients> = {}): TextRecipients {
  return {
    attending: [],
    maybe: [],
    cantGo: [],
    waitlisted: [],
    invited: [],
    ...overrides,
  };
}

describe('availableGroups', () => {
  it('offers only groups with at least one number', () => {
    const r = recipients({ attending: ['+15551112222'], invited: ['+15559990000'] });
    expect(availableGroups(r).map((o) => o.value)).toEqual([
      RecipientGroup.Going,
      RecipientGroup.Invited,
    ]);
  });

  it('includes the count per group', () => {
    const r = recipients({ attending: ['+1', '+2'], maybe: ['+3'] });
    const byValue = Object.fromEntries(availableGroups(r).map((o) => [o.value, o.count]));
    expect(byValue[RecipientGroup.Going]).toBe(2);
    expect(byValue[RecipientGroup.Maybe]).toBe(1);
  });
});

describe('collectPhones', () => {
  const FULL = recipients({
    attending: ['+15551112222'],
    maybe: ['+15553334444'],
    cantGo: ['+15555556666'],
    waitlisted: ['+15557778888'],
  });

  it('only collects phones for the selected groups', () => {
    expect(collectPhones(FULL, [RecipientGroup.Going, RecipientGroup.Maybe])).toEqual([
      '+15551112222',
      '+15553334444',
    ]);
  });

  it('includes every group when all are selected', () => {
    expect(
      collectPhones(FULL, [
        RecipientGroup.Going,
        RecipientGroup.Maybe,
        RecipientGroup.CantGo,
        RecipientGroup.Waitlisted,
      ]),
    ).toEqual(['+15551112222', '+15553334444', '+15555556666', '+15557778888']);
  });

  it('dedupes a number that appears in more than one selected group', () => {
    const r = recipients({ attending: ['+15551112222'], invited: ['+15551112222'] });
    expect(collectPhones(r, [RecipientGroup.Going, RecipientGroup.Invited])).toEqual([
      '+15551112222',
    ]);
  });

  it('returns an empty array when no groups are selected', () => {
    expect(collectPhones(FULL, [])).toEqual([]);
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
