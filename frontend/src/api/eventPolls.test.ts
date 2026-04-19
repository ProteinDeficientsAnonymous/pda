import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AxiosError } from 'axios';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/auth/store', () => {
  const state = {
    status: 'authed',
    user: { id: 'u-me', displayName: 'Me', profilePhotoUrl: null },
  };
  const useAuthStore = vi.fn((selector?: (s: typeof state) => unknown) =>
    selector ? selector(state) : state,
  ) as unknown as { (selector: (s: typeof state) => unknown): unknown; getState: () => typeof state };
  useAuthStore.getState = () => state;
  return { useAuthStore };
});

import { apiClient } from '@/api/client';
import { mapEventPoll, type WireEventPoll } from './eventPollMapper';
import { eventPollKeys, useEventPoll, useVotePoll } from './eventPolls';
import { VoteChoice } from '@/models/eventPoll';

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

function wirePoll(overrides: Partial<WireEventPoll> = {}): WireEventPoll {
  return {
    id: 'poll-1',
    event_id: 'evt-1',
    is_active: true,
    options: [
      {
        id: 'opt-a',
        datetime: '2026-05-01T18:00:00Z',
        display_order: 0,
        yes_count: 2,
        maybe_count: 1,
        no_count: 0,
        yes_voters: [
          { user_id: 'u-1', name: 'Alice', photo_url: 'a.jpg' },
          { user_id: 'u-2', name: 'Bob', photo_url: 'b.jpg' },
        ],
        maybe_voters: [{ user_id: 'u-3', name: 'Cass', photo_url: 'c.jpg' }],
        no_voters: [],
      },
      {
        id: 'opt-b',
        datetime: '2026-05-02T18:00:00Z',
        display_order: 1,
        yes_count: 0,
        maybe_count: 0,
        no_count: 1,
        yes_voters: [],
        maybe_voters: [],
        no_voters: [{ user_id: 'u-1', name: 'Alice', photo_url: 'a.jpg' }],
      },
    ],
    winning_option_id: null,
    winning_datetime: null,
    finalized_by_id: null,
    finalized_at: null,
    my_votes: {},
    ...overrides,
  };
}

function buildWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  return { qc, Wrapper };
}

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// mapper
// ---------------------------------------------------------------------------

describe('mapEventPoll', () => {
  it('converts snake_case + ISO strings to domain types', () => {
    const poll = mapEventPoll(wirePoll());
    expect(poll.id).toBe('poll-1');
    expect(poll.eventId).toBe('evt-1');
    expect(poll.isActive).toBe(true);
    expect(poll.options).toHaveLength(2);
    expect(poll.options[0].datetime).toBeInstanceOf(Date);
    expect(poll.options[0].datetime.toISOString()).toBe('2026-05-01T18:00:00.000Z');
    expect(poll.options[0].yesCount).toBe(2);
    expect(poll.options[0].yesVoters[0]).toEqual({
      userId: 'u-1',
      name: 'Alice',
      photoUrl: 'a.jpg',
    });
  });

  it('maps finalized fields', () => {
    const poll = mapEventPoll(
      wirePoll({
        winning_option_id: 'opt-a',
        winning_datetime: '2026-05-01T18:00:00Z',
        finalized_by_id: 'u-me',
        finalized_at: '2026-04-20T10:00:00Z',
      }),
    );
    expect(poll.winningOptionId).toBe('opt-a');
    expect(poll.winningDatetime).toBeInstanceOf(Date);
    expect(poll.finalizedAt).toBeInstanceOf(Date);
  });

  it('leaves winningDatetime + finalizedAt null when absent', () => {
    const poll = mapEventPoll(wirePoll());
    expect(poll.winningDatetime).toBeNull();
    expect(poll.finalizedAt).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// useEventPoll — tolerates 404 (no poll yet)
// ---------------------------------------------------------------------------

describe('useEventPoll', () => {
  it('returns mapped poll when the API returns 200', async () => {
    mockedGet.mockResolvedValueOnce({ data: wirePoll() });
    const { Wrapper } = buildWrapper();

    const { result } = renderHook(() => useEventPoll('evt-1', true), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe('poll-1');
    expect(mockedGet).toHaveBeenCalledWith('/api/community/events/evt-1/poll/');
  });

  it('returns null when the API returns 404', async () => {
    const err = Object.assign(new Error('not found'), {
      isAxiosError: true,
      response: { status: 404, data: {} },
    }) as AxiosError;
    mockedGet.mockRejectedValueOnce(err);
    const { Wrapper } = buildWrapper();

    const { result } = renderHook(() => useEventPoll('evt-1', true), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });

  it('is disabled when hasPoll is false', () => {
    const { Wrapper } = buildWrapper();
    const { result } = renderHook(() => useEventPoll('evt-1', false), { wrapper: Wrapper });
    expect(result.current.fetchStatus).toBe('idle');
    expect(mockedGet).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// useVotePoll — optimistic update + rollback
// ---------------------------------------------------------------------------

describe('useVotePoll', () => {
  it('optimistically shifts counts + voter lists on a new yes vote', async () => {
    const { qc, Wrapper } = buildWrapper();
    const key = eventPollKeys.detail('evt-1', true);
    qc.setQueryData(key, mapEventPoll(wirePoll()));

    // Make the POST hang so we can observe the optimistic state.
    let resolvePost: ((value: { data: WireEventPoll }) => void) | undefined;
    mockedPost.mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePost = resolve;
      }),
    );

    const { result } = renderHook(() => useVotePoll('evt-1'), { wrapper: Wrapper });

    void result.current.mutate({ 'opt-a': VoteChoice.Yes });

    await waitFor(() => {
      const cached = qc.getQueryData(key) as ReturnType<typeof mapEventPoll> | undefined;
      expect(cached?.options[0].yesCount).toBe(3);
      expect(cached?.options[0].yesVoters.some((v) => v.userId === 'u-me')).toBe(true);
      expect(cached?.myVotes['opt-a']).toBe(VoteChoice.Yes);
    });

    resolvePost?.({ data: wirePoll({ my_votes: { 'opt-a': VoteChoice.Yes } }) });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('rolls back to the previous snapshot on error', async () => {
    const { qc, Wrapper } = buildWrapper();
    const key = eventPollKeys.detail('evt-1', true);
    const initial = mapEventPoll(wirePoll());
    qc.setQueryData(key, initial);

    mockedPost.mockRejectedValueOnce(new Error('network fail'));

    const { result } = renderHook(() => useVotePoll('evt-1'), { wrapper: Wrapper });

    await expect(
      result.current.mutateAsync({ 'opt-a': VoteChoice.Yes }),
    ).rejects.toThrow('network fail');

    const rolledBack = qc.getQueryData(key) as ReturnType<typeof mapEventPoll>;
    expect(rolledBack.options[0].yesCount).toBe(2);
    expect(rolledBack.options[0].yesVoters.some((v) => v.userId === 'u-me')).toBe(false);
    expect(rolledBack.myVotes).toEqual({});
  });

  it('shifts a voter from one bucket to another when their choice changes', async () => {
    const { qc, Wrapper } = buildWrapper();
    const key = eventPollKeys.detail('evt-1', true);
    // Seed with my-user already voting "maybe" on opt-a.
    qc.setQueryData(
      key,
      mapEventPoll(
        wirePoll({
          options: [
            {
              id: 'opt-a',
              datetime: '2026-05-01T18:00:00Z',
              display_order: 0,
              yes_count: 0,
              maybe_count: 1,
              no_count: 0,
              yes_voters: [],
              maybe_voters: [{ user_id: 'u-me', name: 'Me', photo_url: '' }],
              no_voters: [],
            },
          ],
          my_votes: { 'opt-a': VoteChoice.Maybe },
        }),
      ),
    );

    let resolvePost: ((value: { data: WireEventPoll }) => void) | undefined;
    mockedPost.mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePost = resolve;
      }),
    );

    const { result } = renderHook(() => useVotePoll('evt-1'), { wrapper: Wrapper });

    void result.current.mutate({ 'opt-a': VoteChoice.Yes });

    await waitFor(() => {
      const cached = qc.getQueryData(key) as ReturnType<typeof mapEventPoll> | undefined;
      expect(cached?.options[0].yesCount).toBe(1);
      expect(cached?.options[0].maybeCount).toBe(0);
      expect(cached?.options[0].maybeVoters).toHaveLength(0);
      expect(cached?.options[0].yesVoters[0].userId).toBe('u-me');
    });

    resolvePost?.({ data: wirePoll() });
  });
});
