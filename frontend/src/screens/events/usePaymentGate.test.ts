import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RsvpStatus } from '@/models/event';
import { makePaidEvent } from '@/test/fixtures';

import { usePaymentGate } from './usePaymentGate';

describe('usePaymentGate', () => {
  it('gates attending on a paid event', () => {
    const { result } = renderHook(() => usePaymentGate(makePaidEvent(), false));
    expect(result.current(RsvpStatus.Attending)).toBe(true);
  });

  it('does not gate joining the waitlist', () => {
    const { result } = renderHook(() => usePaymentGate(makePaidEvent(), true));
    expect(result.current(RsvpStatus.Attending)).toBe(false);
  });

  it('does not gate maybe', () => {
    const { result } = renderHook(() => usePaymentGate(makePaidEvent(), false));
    expect(result.current(RsvpStatus.Maybe)).toBe(false);
  });

  it('does not gate cant go', () => {
    const { result } = renderHook(() => usePaymentGate(makePaidEvent(), false));
    expect(result.current(RsvpStatus.CantGo)).toBe(false);
  });

  it('does not gate a free event', () => {
    const { result } = renderHook(() =>
      usePaymentGate(makePaidEvent({ price: '', venmoLink: '' }), false),
    );
    expect(result.current(RsvpStatus.Attending)).toBe(false);
  });

  it('does not gate a viewer who has already confirmed payment', () => {
    const { result } = renderHook(() =>
      usePaymentGate(makePaidEvent({ myPaidConfirmed: true }), false),
    );
    expect(result.current(RsvpStatus.Attending)).toBe(false);
  });
});
