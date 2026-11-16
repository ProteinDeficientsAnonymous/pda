import { describe, expect, it } from 'vitest';

import { explicitTab, resolveTab, tabOptions } from './planningTab';

describe('tabOptions', () => {
  it('gives planners only their own tabs', () => {
    expect(tabOptions(false).map((o) => o.label)).toEqual(['my events', 'my availability']);
    expect(tabOptions(true).map((o) => o.value)).toEqual([
      'schedule',
      'events',
      'availability',
      'slots',
    ]);
  });
});

describe('explicitTab', () => {
  it('maps the old mine tab to events', () => {
    expect(explicitTab('mine', true)).toBe('events');
  });

  it('ignores tabs the viewer cannot open', () => {
    expect(explicitTab('schedule', false)).toBeNull();
    expect(explicitTab('bogus', true)).toBeNull();
  });
});

describe('resolveTab', () => {
  it('lets a valid tab win', () => {
    expect(resolveTab('slots', true, true)).toBe('slots');
  });

  it('defaults a manager to events when something is waiting, else schedule', () => {
    expect(resolveTab(null, true, true)).toBe('events');
    expect(resolveTab(null, false, true)).toBe('schedule');
    expect(resolveTab('bogus', false, true)).toBe('schedule');
  });

  it('defaults a planner to events', () => {
    expect(resolveTab(null, false, false)).toBe('events');
    expect(resolveTab('slots', false, false)).toBe('events');
  });
});
