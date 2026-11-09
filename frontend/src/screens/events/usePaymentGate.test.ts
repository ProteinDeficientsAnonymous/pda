import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RsvpServerStatus, RsvpStatus } from '@/models/event';
import { makePaidEvent } from '@/test/fixtures';

import { usePaymentGate } from './usePaymentGate';

describe('usePaymentGate', () => {
  it('gates attending on a paid event', () => {
    const { result } = renderHook(() => usePaymentGate(makePaidEvent()));
    expect(result.current(RsvpStatus.Attending, false)).toBe(true);
  });

  it('does not gate joining the waitlist', () => {
    const { result } = renderHook(() =>
      usePaymentGate(makePaidEvent({ maxAttendees: 2, attendingCount: 2 })),
    );
    expect(result.current(RsvpStatus.Attending, false)).toBe(false);
  });

  it('does not gate a +1 party that only fits on the waitlist', () => {
    const { result } = renderHook(() =>
      usePaymentGate(makePaidEvent({ maxAttendees: 2, attendingCount: 1 })),
    );
    expect(result.current(RsvpStatus.Attending, true)).toBe(false);
    expect(result.current(RsvpStatus.Attending, false)).toBe(true);
  });

  it('gates an unpaid attendee who already holds a seat at capacity', () => {
    const { result } = renderHook(() =>
      usePaymentGate(
        makePaidEvent({ maxAttendees: 2, attendingCount: 2, myRsvp: RsvpServerStatus.Attending }),
      ),
    );
    expect(result.current(RsvpStatus.Attending, false)).toBe(true);
  });

  it('does not gate a waitlister keeping their place while spots are open', () => {
    const { result } = renderHook(() =>
      usePaymentGate(
        makePaidEvent({ maxAttendees: 5, attendingCount: 1, myRsvp: RsvpServerStatus.Waitlisted }),
      ),
    );
    expect(result.current(RsvpStatus.Attending, false)).toBe(false);
  });

  it('does not gate maybe', () => {
    const { result } = renderHook(() => usePaymentGate(makePaidEvent()));
    expect(result.current(RsvpStatus.Maybe, false)).toBe(false);
  });

  it('does not gate cant go', () => {
    const { result } = renderHook(() => usePaymentGate(makePaidEvent()));
    expect(result.current(RsvpStatus.CantGo, false)).toBe(false);
  });

  it('does not gate a free event', () => {
    const { result } = renderHook(() =>
      usePaymentGate(makePaidEvent({ price: '', venmoLink: '' })),
    );
    expect(result.current(RsvpStatus.Attending, false)).toBe(false);
  });

  it('does not gate a viewer who has already confirmed payment', () => {
    const { result } = renderHook(() => usePaymentGate(makePaidEvent({ myPaidConfirmed: true })));
    expect(result.current(RsvpStatus.Attending, false)).toBe(false);
  });
});
