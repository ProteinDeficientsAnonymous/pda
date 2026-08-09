import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { eventKeys } from '@/api/events';
import { RsvpStatus } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

import { useRemoveRsvp, useSetRsvp } from './rsvp';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/auth/store', () => {
  const state = { status: 'authed', user: { id: 'u-me' } };
  const useAuthStore = vi.fn((selector?: (s: typeof state) => unknown) =>
    selector ? selector(state) : state,
  );
  return { useAuthStore };
});

const EVENT_ID = '11111111-1111-1111-1111-111111111111';
const EVENT_SLUG = 'summer-potluck';

function buildWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const Wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
  return { qc, Wrapper };
}

describe('useSetRsvp', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should post questionnaire_responses with the RSVP body', async () => {
    const { Wrapper } = buildWrapper();
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { id: EVENT_ID, title: 'potluck', my_rsvp: RsvpStatus.Attending },
    });
    const { result } = renderHook(() => useSetRsvp(), { wrapper: Wrapper });
    result.current.mutate({
      eventId: EVENT_ID,
      status: RsvpStatus.Attending,
      questionnaireResponses: { q1: 'vegan' },
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith(
      `/api/community/events/${EVENT_ID}/rsvp/`,
      expect.objectContaining({
        status: RsvpStatus.Attending,
        questionnaire_responses: { q1: 'vegan' },
      }),
    );
  });
});

describe('useSetRsvp cache patching (issue 1242)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('patches a detail query cached under the event slug, not just the uuid', async () => {
    const { qc, Wrapper } = buildWrapper();
    // Simulate EventDetailScreen having loaded via the slug URL — the query
    // cache entry backing the visible screen is keyed by slug, not uuid.
    qc.setQueryData(
      eventKeys.detail(EVENT_SLUG, true),
      makeEvent({ id: EVENT_ID, slug: EVENT_SLUG, myRsvp: null }),
    );
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { id: EVENT_ID, slug: EVENT_SLUG, title: 'potluck', my_rsvp: RsvpStatus.Attending },
    });

    const { result } = renderHook(() => useSetRsvp(), { wrapper: Wrapper });
    result.current.mutate({ eventId: EVENT_ID, status: RsvpStatus.Attending });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(qc.getQueryData(eventKeys.detail(EVENT_SLUG, true))).toMatchObject({
      myRsvp: RsvpStatus.Attending,
    });
  });
});

describe('useRemoveRsvp cache invalidation (issue 1242)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('invalidates a detail query cached under the event slug, not just the uuid', async () => {
    const { qc, Wrapper } = buildWrapper();
    qc.setQueryData(
      eventKeys.detail(EVENT_SLUG, true),
      makeEvent({ id: EVENT_ID, slug: EVENT_SLUG, myRsvp: RsvpStatus.Attending }),
    );
    vi.mocked(apiClient.delete).mockResolvedValue({ data: undefined });
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');

    const { result } = renderHook(() => useRemoveRsvp(), { wrapper: Wrapper });
    result.current.mutate(EVENT_ID);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(qc.getQueryState(eventKeys.detail(EVENT_SLUG, true))?.isInvalidated).toBe(true);
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: eventKeys.list(true) });
  });
});
