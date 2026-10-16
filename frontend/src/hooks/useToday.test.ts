import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useToday } from './useToday';

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(2026, 9, 7, 15, 30));
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useToday', () => {
  it('returns the start of the current day', () => {
    const { result } = renderHook(() => useToday());

    expect(result.current).toEqual(new Date(2026, 9, 7));
  });

  it('keeps the same date across re-renders', () => {
    const { result, rerender } = renderHook(() => useToday());
    const first = result.current;

    vi.setSystemTime(new Date(2026, 9, 8, 9, 0));
    rerender();

    expect(result.current).toBe(first);
  });
});
