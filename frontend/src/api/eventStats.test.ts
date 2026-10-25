import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { eventKeys } from '@/api/events';
import type { Event } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';
import { makeEvent, makeGuest } from '@/test/fixtures';

import { useSetGuestPayment, withWaitlistOrder } from './eventStats';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/auth/store', () => {
  const state = { status: 'authed', user: { id: 'u-me' } };
  const useAuthStore = vi.fn((selector?: (s: typeof state) => unknown) =>
    selector ? selector(state) : state,
  );
  return { useAuthStore };
});

describe('withWaitlistOrder', () => {
  it('reorders only the waitlisted guests, leaving others in place', () => {
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'w1', status: RsvpServerStatus.Waitlisted }),
        makeGuest({ userId: 'a1', status: RsvpServerStatus.Attending }),
        makeGuest({ userId: 'w2', status: RsvpServerStatus.Waitlisted }),
        makeGuest({ userId: 'w3', status: RsvpServerStatus.Waitlisted }),
      ],
    });
    const ids = withWaitlistOrder(event, ['w3', 'w1', 'w2']).guests.map((g) => g.userId);
    expect(ids).toEqual(['w3', 'a1', 'w1', 'w2']);
  });

  it('keeps unknown waitlisted guests at the end', () => {
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'w1', status: RsvpServerStatus.Waitlisted }),
        makeGuest({ userId: 'w2', status: RsvpServerStatus.Waitlisted }),
      ],
    });
    const ids = withWaitlistOrder(event, ['w2']).guests.map((g) => g.userId);
    expect(ids).toEqual(['w2', 'w1']);
  });
});

describe('useSetGuestPayment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('patches the verified mark and caches the mapped event', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const Wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children);
    vi.mocked(apiClient.patch).mockResolvedValue({
      data: {
        id: 'ev1',
        slug: 'test-event',
        title: 'Test Event',
        guests: [
          {
            user_id: 'u1',
            name: 'Alex',
            status: 'attending',
            paid_confirmed: true,
            payment_verified: true,
          },
        ],
      },
    });

    const { result } = renderHook(() => useSetGuestPayment('ev1'), { wrapper: Wrapper });
    result.current.mutate({ userId: 'u1', verified: true });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(apiClient.patch).toHaveBeenCalledWith('/api/community/events/ev1/rsvps/u1/payment/', {
      paid_confirmed: true,
    });
    const cached = qc.getQueryData<Event>(eventKeys.detail('test-event', true));
    expect(cached?.guests[0]?.paymentVerified).toBe(true);
    expect(qc.getQueryData<Event>(eventKeys.detail('ev1', true))).toBe(cached);
  });

  it('caches an undone verification as unpaid', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const Wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children);
    vi.mocked(apiClient.patch).mockResolvedValue({
      data: {
        id: 'ev1',
        slug: 'test-event',
        title: 'Test Event',
        guests: [
          {
            user_id: 'u1',
            name: 'Alex',
            status: 'attending',
            paid_confirmed: false,
            payment_verified: false,
          },
        ],
      },
    });

    const { result } = renderHook(() => useSetGuestPayment('ev1'), { wrapper: Wrapper });
    result.current.mutate({ userId: 'u1', verified: false });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(apiClient.patch).toHaveBeenCalledWith('/api/community/events/ev1/rsvps/u1/payment/', {
      paid_confirmed: false,
    });
    const guest = qc.getQueryData<Event>(eventKeys.detail('test-event', true))?.guests[0];
    expect(guest?.paidConfirmed).toBe(false);
    expect(guest?.paymentVerified).toBe(false);
  });
});
