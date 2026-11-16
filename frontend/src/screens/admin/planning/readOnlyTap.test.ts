import { describe, expect, it } from 'vitest';

import { readOnlyTapNotice } from './readOnlyTap';

describe('readOnlyTapNotice', () => {
  it('lets you act on your own sent tile', () => {
    expect(readOnlyTapNotice('proposed', true, true, 'june')).toBeNull();
  });

  it.each([
    ['proposed', false, true, 'you can only change your own row', false],
    ['committed', true, true, "you're in for june — back out from my events", false],
    [
      'available',
      true,
      true,
      "you can only put yourself in for months you've been proposed for",
      false,
    ],
    ['declined', true, true, 'you declined june — ask a coordinator to propose you again', false],
    ['blank', true, true, "you said you're not free in june — update your availability", true],
    ['blank', true, false, 'add your availability so you can be proposed months', true],
  ] as const)(
    '%s (self %s, submitted %s) -> %s',
    (state, self, submitted, message, toAvailability) => {
      expect(readOnlyTapNotice(state, self, submitted, 'june')).toEqual({
        message,
        toAvailability,
      });
    },
  );
});
