import { format } from 'date-fns';
import { describe, expect, it } from 'vitest';

import { formatPollOption } from './pollOption';

describe('formatPollOption', () => {
  it('formats iso datetimes as lowercase local times', () => {
    const iso = '2026-11-07T16:00:00.000Z';
    expect(formatPollOption(iso)).toBe(format(new Date(iso), 'MMM d, yyyy h:mm a').toLowerCase());
  });

  it('leaves non-datetime values alone', () => {
    expect(formatPollOption('2024')).toBe('2024');
    expect(formatPollOption('vanilla')).toBe('vanilla');
  });
});
