import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RsvpStatus } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

import { usePaymentGate } from './usePaymentGate';

const mockUseFlag = vi.hoisted(() => vi.fn());
vi.mock('@/api/featureFlags', () => ({ useFlag: mockUseFlag }));

function makePaidEvent(overrides: Parameters<typeof makeEvent>[0] = {}) {
  return makeEvent({
    price: '$10',
    venmoLink: 'https://venmo.com/u/host',
    cashappLink: '',
    zelleInfo: '',
    myPaidConfirmed: false,
    ...overrides,
  });
}

describe('usePaymentGate', () => {
  beforeEach(() => {
    mockUseFlag.mockReset();
  });

  it('gates attending on a paid event when the flag is on', () => {
    mockUseFlag.mockReturnValue(true);
    const { result } = renderHook(() => usePaymentGate(makePaidEvent()));
    expect(result.current(RsvpStatus.Attending)).toBe(true);
  });

  it('does not gate when the flag is off', () => {
    mockUseFlag.mockReturnValue(false);
    const { result } = renderHook(() => usePaymentGate(makePaidEvent()));
    expect(result.current(RsvpStatus.Attending)).toBe(false);
  });

  it('does not gate maybe', () => {
    mockUseFlag.mockReturnValue(true);
    const { result } = renderHook(() => usePaymentGate(makePaidEvent()));
    expect(result.current(RsvpStatus.Maybe)).toBe(false);
  });

  it('does not gate cant go', () => {
    mockUseFlag.mockReturnValue(true);
    const { result } = renderHook(() => usePaymentGate(makePaidEvent()));
    expect(result.current(RsvpStatus.CantGo)).toBe(false);
  });

  it('does not gate a free event', () => {
    mockUseFlag.mockReturnValue(true);
    const { result } = renderHook(() =>
      usePaymentGate(makePaidEvent({ price: '', venmoLink: '' })),
    );
    expect(result.current(RsvpStatus.Attending)).toBe(false);
  });

  it('does not gate a viewer who has already confirmed payment', () => {
    mockUseFlag.mockReturnValue(true);
    const { result } = renderHook(() => usePaymentGate(makePaidEvent({ myPaidConfirmed: true })));
    expect(result.current(RsvpStatus.Attending)).toBe(false);
  });
});
