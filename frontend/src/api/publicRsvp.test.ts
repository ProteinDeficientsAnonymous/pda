import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { createElement, type ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from './client';
import { useSubmitPublicRsvp } from './publicRsvp';

vi.mock('./client', () => ({ apiClient: { post: vi.fn() } }));

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return createElement(QueryClientProvider, { client: qc }, children);
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
