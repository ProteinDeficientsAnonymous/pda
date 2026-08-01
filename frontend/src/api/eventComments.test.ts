import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/auth/store', () => {
  const state = {
    status: 'authed',
    user: { id: 'u-me', profilePhotoUrl: null },
  };
  const useAuthStore = vi.fn((selector?: (s: typeof state) => unknown) =>
    selector ? selector(state) : state,
  ) as unknown as {
    (selector: (s: typeof state) => unknown): unknown;
    getState: () => typeof state;
  };
  useAuthStore.getState = () => state;
  return { useAuthStore };
});

import { apiClient } from '@/api/client';

import { type WireCommentList } from './eventCommentMapper';
import { eventCommentKeys, useEventComments } from './eventComments';

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedDelete = vi.mocked(apiClient.delete);

function wireCommentList(overrides: Partial<WireCommentList> = {}): WireCommentList {
  return {
    items: [],
    can_post: true,
    cannot_post_reason: null,
    ...overrides,
  };
}

function buildWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const Wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
  return { qc, Wrapper };
}

beforeEach(() => {
  vi.clearAllMocks();
});

const EVENT_ID = '11111111-1111-1111-1111-111111111111';

// ---------------------------------------------------------------------------
// eventCommentKeys
// ---------------------------------------------------------------------------

describe('eventCommentKeys', () => {
  it('produces stable list key', () => {
    expect(eventCommentKeys.list(EVENT_ID)).toEqual(['event-comments', EVENT_ID]);
  });
});

// ---------------------------------------------------------------------------
// useEventComments
// ---------------------------------------------------------------------------

describe('useEventComments', () => {
  it('maps the wire payload to the domain shape', async () => {
    mockedGet.mockResolvedValueOnce({ data: wireCommentList() });
    const { Wrapper } = buildWrapper();

    const { result } = renderHook(() => useEventComments(EVENT_ID), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({
      items: [],
      canPost: true,
      cannotPostReason: null,
    });
    expect(mockedGet).toHaveBeenCalledWith(`/api/community/events/${EVENT_ID}/comments/`);
  });

  it('maps cannot_post_reason correctly', async () => {
    mockedGet.mockResolvedValueOnce({
      data: wireCommentList({ can_post: false, cannot_post_reason: 'login_required' }),
    });
    const { Wrapper } = buildWrapper();

    const { result } = renderHook(() => useEventComments(EVENT_ID), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.canPost).toBe(false);
    expect(result.current.data?.cannotPostReason).toBe('login_required');
  });

  it('is disabled when eventId is empty', () => {
    const { Wrapper } = buildWrapper();
    const { result } = renderHook(() => useEventComments(''), { wrapper: Wrapper });
    expect(result.current.fetchStatus).toBe('idle');
    expect(mockedGet).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// useDeleteComment — optimistic update + rollback
// ---------------------------------------------------------------------------

import { mapCommentList } from './eventCommentMapper';
import { useDeleteComment } from './eventComments';

const wireWithComment: WireCommentList = {
  can_post: true,
  cannot_post_reason: null,
  items: [
    {
      id: 'c-1',
      author_id: 'u-me',
      author_display_name: 'Me',
      author_photo_url: '',
      body: 'hello',
      is_deleted: false,
      created_at: '2026-01-01T00:00:00Z',
      reactions: [],
      can_delete: true,
      replies: [],
    },
  ],
};

describe('useDeleteComment', () => {
  it('optimistically marks comment as deleted', async () => {
    const { qc, Wrapper } = buildWrapper();
    const key = eventCommentKeys.list(EVENT_ID);
    qc.setQueryData(key, mapCommentList(wireWithComment));

    let resolveDelete: (() => void) | undefined;
    mockedDelete.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveDelete = () =>
          resolve({
            data: undefined,
            status: 204,
            statusText: 'No Content',
            headers: {},
            config: {} as never,
          });
      }),
    );
    // invalidateQueries triggers a refetch — stub it
    mockedGet.mockResolvedValue({ data: wireWithComment });

    const { result } = renderHook(() => useDeleteComment(EVENT_ID), { wrapper: Wrapper });

    result.current.mutate({ commentId: 'c-1' });

    await waitFor(() => {
      const cached = qc.getQueryData(key) as ReturnType<typeof mapCommentList> | undefined;
      expect(cached?.items[0]?.isDeleted).toBe(true);
      expect(cached?.items[0]?.body).toBe('');
    });

    resolveDelete?.();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('rolls back on error', async () => {
    const { qc, Wrapper } = buildWrapper();
    const key = eventCommentKeys.list(EVENT_ID);
    qc.setQueryData(key, mapCommentList(wireWithComment));

    mockedDelete.mockRejectedValueOnce(new Error('network fail'));
    mockedGet.mockResolvedValue({ data: wireWithComment });

    const { result } = renderHook(() => useDeleteComment(EVENT_ID), { wrapper: Wrapper });

    await expect(result.current.mutateAsync({ commentId: 'c-1' })).rejects.toThrow('network fail');

    const rolledBack = qc.getQueryData<ReturnType<typeof mapCommentList>>(key)!;
    expect(rolledBack.items[0]?.isDeleted).toBe(false);
    expect(rolledBack.items[0]?.body).toBe('hello');
  });
});

// ---------------------------------------------------------------------------
// useToggleReaction — optimistic update + rollback
// ---------------------------------------------------------------------------

import { useToggleReaction } from './eventComments';

const wireWithReaction: WireCommentList = {
  can_post: true,
  cannot_post_reason: null,
  items: [
    {
      id: 'c-1',
      author_id: 'u-other',
      author_display_name: 'Other',
      author_photo_url: '',
      body: 'nice',
      is_deleted: false,
      created_at: '2026-01-01T00:00:00Z',
      reactions: [{ emoji: '👍', count: 1, reacted_by_me: false, reactors: [] }],
      can_delete: false,
      replies: [],
    },
  ],
};

describe('useToggleReaction', () => {
  it('optimistically increments reaction count when adding', async () => {
    const { qc, Wrapper } = buildWrapper();
    const key = eventCommentKeys.list(EVENT_ID);
    qc.setQueryData(key, mapCommentList(wireWithReaction));

    let resolvePost: ((value: { data: unknown }) => void) | undefined;
    mockedPost.mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePost = resolve;
      }),
    );

    const { result } = renderHook(() => useToggleReaction(EVENT_ID), { wrapper: Wrapper });

    result.current.mutate({ commentId: 'c-1', emoji: '👍' });

    await waitFor(() => {
      const cached = qc.getQueryData(key) as ReturnType<typeof mapCommentList> | undefined;
      const reaction = cached?.items[0]?.reactions.find((r) => r.emoji === '👍');
      expect(reaction?.count).toBe(2);
      expect(reaction?.reactedByMe).toBe(true);
    });

    // Resolve with the server response (same as current state)
    resolvePost?.({ data: wireWithReaction.items[0] });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('optimistically decrements when removing own reaction', async () => {
    const wireWithMyReaction: WireCommentList = {
      can_post: true,
      cannot_post_reason: null,
      items: [
        {
          id: 'c-1',
          author_id: 'u-other',
          author_display_name: 'Other',
          author_photo_url: '',
          body: 'nice',
          is_deleted: false,
          created_at: '2026-01-01T00:00:00Z',
          reactions: [{ emoji: '👍', count: 2, reacted_by_me: true, reactors: [] }],
          can_delete: false,
          replies: [],
        },
      ],
    };

    const { qc, Wrapper } = buildWrapper();
    const key = eventCommentKeys.list(EVENT_ID);
    qc.setQueryData(key, mapCommentList(wireWithMyReaction));

    let resolvePost: ((value: { data: unknown }) => void) | undefined;
    mockedPost.mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePost = resolve;
      }),
    );

    const { result } = renderHook(() => useToggleReaction(EVENT_ID), { wrapper: Wrapper });

    result.current.mutate({ commentId: 'c-1', emoji: '👍' });

    await waitFor(() => {
      const cached = qc.getQueryData(key) as ReturnType<typeof mapCommentList> | undefined;
      const reaction = cached?.items[0]?.reactions.find((r) => r.emoji === '👍');
      expect(reaction?.count).toBe(1);
      expect(reaction?.reactedByMe).toBe(false);
    });

    resolvePost?.({ data: wireWithMyReaction.items[0] });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('rolls back on error', async () => {
    const { qc, Wrapper } = buildWrapper();
    const key = eventCommentKeys.list(EVENT_ID);
    qc.setQueryData(key, mapCommentList(wireWithReaction));

    mockedPost.mockRejectedValueOnce(new Error('network fail'));

    const { result } = renderHook(() => useToggleReaction(EVENT_ID), { wrapper: Wrapper });

    await expect(result.current.mutateAsync({ commentId: 'c-1', emoji: '👍' })).rejects.toThrow(
      'network fail',
    );

    const rolledBack = qc.getQueryData<ReturnType<typeof mapCommentList>>(key)!;
    const reaction = rolledBack.items[0]?.reactions.find((r) => r.emoji === '👍');
    expect(reaction?.count).toBe(1);
    expect(reaction?.reactedByMe).toBe(false);
  });
});
