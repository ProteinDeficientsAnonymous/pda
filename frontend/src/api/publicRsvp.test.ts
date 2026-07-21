import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { createElement, type ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from './client';
import { eventCommentKeys } from './eventComments';
import { eventKeys } from './events';
import { useSubmitPublicRsvp, useUpdatePublicMyRsvp } from './publicRsvp';

vi.mock('./client', () => ({
  apiClient: { post: vi.fn(), get: vi.fn(), delete: vi.fn() },
  setAuthBridge: vi.fn(),
}));

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: qc }, children);
  }
  return { qc, wrapper };
}

function wrapper({ children }: { children: ReactNode }) {
  return makeWrapper().wrapper({ children });
}

describe('useSubmitPublicRsvp', () => {
  beforeEach(() => vi.mocked(apiClient.post).mockReset());

  it('posts to the public endpoint with the payload and returns data', async () => {
    const out = { event: { id: 'ev1' }, rsvp: { status: 'attending', has_plus_one: false } };
    vi.mocked(apiClient.post).mockResolvedValue({ data: out });
    const { result } = renderHook(() => useSubmitPublicRsvp(), { wrapper });

    const payload = {
      first_name: 'Ada',
      last_name: '',
      email: 'ada@example.com',
      phone_number: '+15550001111',
      status: 'attending',
      has_plus_one: false,
      website: '',
    };
    result.current.mutate({ eventId: 'ev1', payload });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith('/api/community/public/events/ev1/rsvp/', payload);
    expect(result.current.data).toEqual(out);
  });
});

describe('useUpdatePublicMyRsvp', () => {
  beforeEach(() => vi.mocked(apiClient.post).mockReset());

  it('invalidates the token event-detail and comment-list queries on success', async () => {
    const token = 'tok123';
    vi.mocked(apiClient.post).mockResolvedValue({ data: { event: { id: 'ev1' } } });
    const { qc, wrapper } = makeWrapper();
    const invalidate = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useUpdatePublicMyRsvp(token), { wrapper });

    result.current.mutate({
      eventId: 'ev1',
      status: 'attending',
      hasPlusOne: false,
      comment: 'hi',
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: eventKeys.detail('ev1', false, token) });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: eventCommentKeys.list('ev1') });
  });
});
