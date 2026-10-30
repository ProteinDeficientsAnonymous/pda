import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { makeEvent } from '@/test/fixtures';
import { makeQueryClient, queryWrapper } from '@/test/render';

import { apiClient } from './client';
import { eventCommentKeys } from './eventComments';
import { eventKeys } from './events';
import { useCancelPublicMyRsvp, useSubmitPublicRsvp, useUpdatePublicMyRsvp } from './publicRsvp';

vi.mock('./client', () => ({
  apiClient: { post: vi.fn(), get: vi.fn(), delete: vi.fn() },
  setAuthBridge: vi.fn(),
}));

describe('useSubmitPublicRsvp', () => {
  beforeEach(() => vi.mocked(apiClient.post).mockReset());

  it('posts to the public endpoint with the payload and returns data', async () => {
    const out = { event: { id: 'ev1' }, rsvp: { status: 'attending', has_plus_one: false } };
    vi.mocked(apiClient.post).mockResolvedValue({ data: out });
    const { result } = renderHook(() => useSubmitPublicRsvp(), { wrapper: queryWrapper() });

    const payload = {
      first_name: 'Ada',
      last_name: '',
      email: 'ada@example.com',
      phone_number: '+15550001111',
      status: 'attending',
      has_plus_one: false,
      questionnaire_responses: {},
      website: '',
      paid_confirmed: false,
    };
    result.current.mutate({ eventId: 'ev1', payload });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith('/api/community/public/events/ev1/rsvp/', payload);
    expect(result.current.data).toEqual(out);
  });
});

describe('useUpdatePublicMyRsvp', () => {
  beforeEach(() => vi.mocked(apiClient.post).mockReset());

  it('invalidates the slug-keyed event detail after changing to cant go', async () => {
    const token = 'tok123';
    const eventId = '11111111-1111-1111-1111-111111111111';
    const slug = 'pda-hudson-river-walk';
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { event: { id: eventId, slug, title: 'walk', my_rsvp: 'cant_go' } },
    });
    const qc = makeQueryClient();
    const otherId = '22222222-2222-2222-2222-222222222222';
    const otherSlug = 'other-event';
    qc.setQueryData(
      eventKeys.detail(slug, false, token),
      makeEvent({ id: eventId, slug, myRsvp: 'attending' }),
    );
    qc.setQueryData(
      eventKeys.detail(otherSlug, false, token),
      makeEvent({ id: otherId, slug: otherSlug, myRsvp: 'attending' }),
    );
    qc.setQueryData(eventKeys.list(false), [makeEvent({ id: eventId, slug })]);
    const invalidate = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useUpdatePublicMyRsvp(token), {
      wrapper: queryWrapper(qc),
    });

    result.current.mutate({
      eventId,
      status: 'cant_go',
      hasPlusOne: false,
      comment: 'hi',
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenCalledWith(
      `/api/community/public/my-rsvps/${eventId}/`,
      {
        status: 'cant_go',
        has_plus_one: false,
        comment: 'hi',
        paid_confirmed: false,
      },
      { params: { token } },
    );
    expect(
      qc.getQueryData<ReturnType<typeof makeEvent>>(eventKeys.detail(slug, false, token))?.myRsvp,
    ).toBe('cant_go');
    expect(qc.getQueryState(eventKeys.detail(slug, false, token))?.isInvalidated).toBe(true);
    expect(qc.getQueryState(eventKeys.detail(otherSlug, false, token))?.isInvalidated).toBe(false);
    expect(qc.getQueryState(eventKeys.list(false))?.isInvalidated).toBe(true);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: eventCommentKeys.list(eventId) });
  });
});

describe('useCancelPublicMyRsvp', () => {
  beforeEach(() => vi.mocked(apiClient.delete).mockReset());

  it('invalidates the slug-keyed event detail after remove', async () => {
    const token = 'tok123';
    const eventId = '11111111-1111-1111-1111-111111111111';
    const slug = 'pda-hudson-river-walk';
    vi.mocked(apiClient.delete).mockResolvedValue({ data: null });
    const qc = makeQueryClient();
    qc.setQueryData(
      eventKeys.detail(slug, false, token),
      makeEvent({ id: eventId, slug, myRsvp: 'attending' }),
    );
    const { result } = renderHook(() => useCancelPublicMyRsvp(token), {
      wrapper: queryWrapper(qc),
    });

    result.current.mutate(eventId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.delete).toHaveBeenCalledWith(`/api/community/public/my-rsvps/${eventId}/`, {
      params: { token },
    });
    expect(qc.getQueryState(eventKeys.detail(slug, false, token))?.isInvalidated).toBe(true);
  });
});
