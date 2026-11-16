import { describe, expect, it } from 'vitest';

import { resolveTab } from './planningTab';

describe('resolveTab', () => {
  it('lets a valid tab win', () => {
    expect(resolveTab('slots', true)).toBe('slots');
  });

  it('defaults to mine when something is waiting', () => {
    expect(resolveTab(null, true)).toBe('mine');
  });

  it('defaults to schedule otherwise', () => {
    expect(resolveTab(null, false)).toBe('schedule');
    expect(resolveTab('bogus', false)).toBe('schedule');
  });
});
