import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

import { apiClient } from '@/api/client';
import { useCalendarToken, useRegenerateCalendarToken } from './calendar';

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function makeWrapper(qc: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useCalendarToken', () => {
  it('should map feed url and token from wire response', async () => {
    mockedGet.mockResolvedValueOnce({
      data: { token: 'abc', feed_url: 'https://x.example/feed/?token=abc' },
    });
    const qc = makeQc();
    const { result } = renderHook(() => useCalendarToken(), { wrapper: makeWrapper(qc) });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedGet).toHaveBeenCalledWith('/api/community/calendar/token/');
    expect(result.current.data).toEqual({
      token: 'abc',
      feedUrl: 'https://x.example/feed/?token=abc',
    });
  });
});

describe('useRegenerateCalendarToken', () => {
  it('should post and return new token payload', async () => {
    mockedPost.mockResolvedValueOnce({
      data: { token: 'newtok', feed_url: 'https://x.example/feed/?token=newtok' },
    });
    const qc = makeQc();
    const { result } = renderHook(() => useRegenerateCalendarToken(), { wrapper: makeWrapper(qc) });
    await result.current.mutateAsync();
    expect(mockedPost).toHaveBeenCalledWith('/api/community/calendar/token/');
    await waitFor(() =>
      expect(qc.getQueryData(['calendar', 'token'])).toEqual({
        token: 'newtok',
        feedUrl: 'https://x.example/feed/?token=newtok',
      }),
    );
  });
});
