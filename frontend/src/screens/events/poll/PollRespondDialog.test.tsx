import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { mapEventPoll, type WireEventPoll } from '@/api/eventPollMapper';
import { eventPollKeys } from '@/api/eventPolls';
import { VoteChoice } from '@/models/eventPoll';

import { PollRespondDialog } from './PollRespondDialog';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/auth/store', () => {
  const state = { status: 'authed', user: { id: 'u-me', profilePhotoUrl: null } };
  const useAuthStore = vi.fn((selector?: (s: typeof state) => unknown) =>
    selector ? selector(state) : state,
  ) as unknown as {
    (selector: (s: typeof state) => unknown): unknown;
    getState: () => typeof state;
  };
  useAuthStore.getState = () => state;
  return { useAuthStore };
});

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
        yes_count: 1,
        maybe_count: 0,
        no_count: 0,
        yes_voters: [{ user_id: 'u-me', name: 'Me', photo_url: '' }],
        maybe_voters: [],
        no_voters: [],
      },
    ],
    winning_option_id: null,
    winning_datetime: null,
    finalized_by_id: null,
    finalized_at: null,
    my_votes: { 'opt-a': VoteChoice.Yes },
    ...overrides,
  };
}

function renderDialog(poll = mapEventPoll(wirePoll())) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(eventPollKeys.detail('evt-1', true), poll);
  const Wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
  render(<PollRespondDialog open onClose={vi.fn()} poll={poll} />, { wrapper: Wrapper });
  return { qc };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('PollRespondDialog retract vote', () => {
  it('tapping the active choice again sends a payload without that option', async () => {
    mockedGet.mockResolvedValue({ data: wirePoll() });
    mockedPost.mockResolvedValueOnce({
      data: wirePoll({
        my_votes: {},
        options: [{ ...wirePoll().options[0]!, yes_count: 0, yes_voters: [] }],
      }),
    });
    renderDialog();

    const yesButton = screen.getByRole('button', { name: /✓ yes/i });
    await userEvent.click(yesButton);

    await waitFor(() => expect(mockedPost).toHaveBeenCalledTimes(1));
    const [, body] = mockedPost.mock.calls[0]!;
    expect(body).toEqual({ votes: {} });
  });

  it('refetches the poll before submitting so a stale snapshot cannot clobber a concurrent vote', async () => {
    // Simulate another tab having voted on opt-b in the meantime — the fresh
    // fetch sees it, the stale `poll` prop does not.
    mockedGet.mockResolvedValue({
      data: wirePoll({ my_votes: { 'opt-a': VoteChoice.Yes, 'opt-b': VoteChoice.No } }),
    });
    mockedPost.mockResolvedValueOnce({ data: wirePoll() });

    const stalePoll = mapEventPoll(wirePoll());
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(eventPollKeys.detail('evt-1', true), stalePoll);
    const Wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children);
    render(<PollRespondDialog open onClose={vi.fn()} poll={stalePoll} />, { wrapper: Wrapper });

    const maybeButton = screen.getAllByRole('button', { name: /maybe/i })[0]!;
    await userEvent.click(maybeButton);

    await waitFor(() => expect(mockedPost).toHaveBeenCalledTimes(1));
    const [, body] = mockedPost.mock.calls[0]!;
    expect(body).toEqual({
      votes: { 'opt-a': VoteChoice.Maybe, 'opt-b': VoteChoice.No },
    });
  });
});
