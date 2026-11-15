import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useRerenderAt } from './useRerenderAt';

const NOW = new Date(2026, 10, 13, 12, 0);
const DAY = 24 * 60 * 60 * 1000;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(NOW);
});

afterEach(() => {
  vi.useRealTimers();
});

function advance(ms: number) {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

function renderCounted(at: Date | null) {
  let renders = 0;
  const hook = renderHook(
    ({ when }: { when: Date | null }) => {
      renders += 1;
      useRerenderAt(when);
    },
    { initialProps: { when: at } },
  );
  return { ...hook, renders: () => renders };
}

describe('useRerenderAt', () => {
  it('re-renders once the time passes', () => {
    const { renders } = renderCounted(new Date(NOW.getTime() + 60_000));

    advance(60_000);
    expect(renders()).toBe(1);
    advance(1);
    expect(renders()).toBe(2);
  });

  it('does nothing for a past or missing time', () => {
    const past = renderCounted(new Date(NOW.getTime() - 1));
    const none = renderCounted(null);

    advance(DAY);
    expect(past.renders()).toBe(1);
    expect(none.renders()).toBe(1);
  });

  it('waits out times past the max timeout', () => {
    const { renders } = renderCounted(new Date(NOW.getTime() + 30 * DAY));

    advance(29 * DAY);
    const before = renders();
    advance(DAY + 1);
    expect(renders()).toBe(before + 1);
  });

  it('clears the timer on unmount', () => {
    const { unmount } = renderCounted(new Date(NOW.getTime() + 60_000));
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});
