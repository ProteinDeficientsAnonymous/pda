import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { queryWrapper } from '@/test/render';

import { useSubmitFeedback } from './feedback';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const mockedPost = vi.mocked(apiClient.post);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useSubmitFeedback', () => {
  it('POSTs feedback with snake_case metadata and returns the issue url', async () => {
    mockedPost.mockResolvedValueOnce({
      data: { html_url: 'https://github.com/owner/repo/issues/42' },
    });

    const { result } = renderHook(() => useSubmitFeedback(), { wrapper: queryWrapper() });

    const returned = await result.current.mutateAsync({
      title: 'calendar crash',
      description: 'the month view throws on empty weeks',
      feedbackTypes: ['bug'],
      metadata: {
        route: '/calendar',
        userAgent: 'jsdom',
        appVersion: '',
      },
    });

    expect(returned).toEqual({ html_url: 'https://github.com/owner/repo/issues/42' });
    expect(mockedPost).toHaveBeenCalledWith('/api/community/feedback/', {
      title: 'calendar crash',
      description: 'the month view throws on empty weeks',
      feedback_types: ['bug'],
      metadata: {
        route: '/calendar',
        user_agent: 'jsdom',
        app_version: '',
      },
    });
  });

  it('sends multiple feedback types in the payload', async () => {
    mockedPost.mockResolvedValueOnce({ data: { html_url: 'https://example.com/1' } });

    const { result } = renderHook(() => useSubmitFeedback(), { wrapper: queryWrapper() });
    await result.current.mutateAsync({
      title: 't',
      description: 'd',
      feedbackTypes: ['bug', 'feature request'],
      metadata: {
        route: '/',
        userAgent: '',
        appVersion: '',
      },
    });

    const [, body] = mockedPost.mock.calls[0] ?? [];
    expect((body as { feedback_types: string[] }).feedback_types).toEqual([
      'bug',
      'feature request',
    ]);
  });

  it('propagates API errors to the caller', async () => {
    const apiError = new Error('github app not configured');
    mockedPost.mockRejectedValueOnce(apiError);

    const { result } = renderHook(() => useSubmitFeedback(), { wrapper: queryWrapper() });

    await expect(
      result.current.mutateAsync({
        title: 't',
        description: 'd',
        feedbackTypes: [],
        metadata: {
          route: '/',
          userAgent: '',
          appVersion: '',
        },
      }),
    ).rejects.toBe(apiError);

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(apiError);
  });
});
