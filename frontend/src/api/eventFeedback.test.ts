import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authClient } from '@/api/client';

import { useEventFeedback, useSubmitEventFeedback } from './eventFeedback';

vi.mock('@/api/client', () => ({
  authClient: { get: vi.fn(), post: vi.fn() },
}));

const mockedGet = vi.mocked(authClient.get);
const mockedPost = vi.mocked(authClient.post);

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useEventFeedback', () => {
  it('sends the token as a header and maps the response', async () => {
    mockedGet.mockResolvedValueOnce({
      data: {
        survey: null,
        event_id: 'evt-1',
        event_title: 'potluck',
        event_start: '2026-10-12T18:00:00Z',
        already_responded: false,
        is_open: true,
      },
    });

    const { result } = renderHook(() => useEventFeedback('tok-1'), { wrapper: wrapper() });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockedGet).toHaveBeenCalledWith('/api/community/event-feedback/', {
      headers: { 'X-Feedback-Token': 'tok-1' },
    });
    expect(result.current.data).toMatchObject({
      survey: null,
      eventId: 'evt-1',
      eventTitle: 'potluck',
      alreadyResponded: false,
      isOpen: true,
    });
    expect(result.current.data?.eventStart).toEqual(new Date('2026-10-12T18:00:00Z'));
  });

  it('does not fetch without a token', () => {
    renderHook(() => useEventFeedback(''), { wrapper: wrapper() });
    expect(mockedGet).not.toHaveBeenCalled();
  });
});

describe('useSubmitEventFeedback', () => {
  it('posts answers with the token header and returns the confirmation', async () => {
    mockedPost.mockResolvedValueOnce({ data: { confirmation_message: 'thanks' } });
    const { result } = renderHook(() => useSubmitEventFeedback('tok-1'), { wrapper: wrapper() });

    const out = await result.current.mutateAsync({ q1: 'great' });

    expect(out).toEqual({ confirmationMessage: 'thanks' });
    expect(mockedPost).toHaveBeenCalledWith(
      '/api/community/event-feedback/respond/',
      { answers: { q1: 'great' } },
      { headers: { 'X-Feedback-Token': 'tok-1' } },
    );
  });
});
