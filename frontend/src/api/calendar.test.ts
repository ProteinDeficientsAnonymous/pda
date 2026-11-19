import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { makeQueryClient, queryWrapper } from '@/test/render';

import { useCalendarToken, useRegenerateCalendarToken } from './calendar';

vi.mock('@/api/client');

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useCalendarToken', () => {
  it('should map feed url and token from wire response', async () => {
    mockedGet.mockResolvedValueOnce({
      data: { token: 'abc', feed_url: 'https://x.example/feed/?token=abc' },
    });
    const qc = makeQueryClient();
    const { result } = renderHook(() => useCalendarToken(), { wrapper: queryWrapper(qc) });
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
    const qc = makeQueryClient();
    const { result } = renderHook(() => useRegenerateCalendarToken(), {
      wrapper: queryWrapper(qc),
    });
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
