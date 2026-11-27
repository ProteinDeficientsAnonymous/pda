import { describe, expect, it } from 'vitest';

import { formatPollOption } from './pollOption';

describe('formatPollOption', () => {
  it('formats iso datetimes in et', () => {
    expect(formatPollOption('2026-11-07T16:00:00.000Z')).toBe('nov 7, 2026 11:00 am et');
  });

  it('leaves non-datetime values alone', () => {
    expect(formatPollOption('2024')).toBe('2024');
    expect(formatPollOption('vanilla')).toBe('vanilla');
  });
});
