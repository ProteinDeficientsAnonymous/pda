import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useEventPoll } from '@/api/eventPolls';
import { useAuthStore } from '@/auth/store';
import type { EventPoll, EventPollOption } from '@/models/eventPoll';
import { Permission } from '@/models/permissions';
import { makeEvent, makeUser } from '@/test/fixtures';

import { EventPollCard } from './EventPollCard';

vi.mock('@/api/eventPolls', () => ({
  useEventPoll: vi.fn(),
  useFinalizePoll: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  useVotePoll: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  eventPollKeys: {
    all: ['event-poll'],
    detail: () => ['event-poll', 'ev1'],
  },
}));

vi.mock('./PollRespondDialog', () => ({
  PollRespondDialog: () => null,
}));

vi.mock('./PollFinalizeDialog', () => ({
  PollFinalizeDialog: () => null,
}));

vi.mock('./PollManageDialog', () => ({
  PollManageDialog: () => null,
}));

function makePollOption(overrides: Partial<EventPollOption> = {}): EventPollOption {
  return {
    id: 'opt1',
    datetime: new Date('2026-09-15T19:00:00Z'),
    displayOrder: 0,
    yesCount: 2,
    maybeCount: 1,
    noCount: 0,
    yesVoters: [],
    maybeVoters: [],
    noVoters: [],
    ...overrides,
  };
}

function makePoll(overrides: Partial<EventPoll> = {}): EventPoll {
  return {
    id: 'poll1',
    eventId: 'ev1',
    isActive: true,
    options: [makePollOption()],
    winningOptionId: null,
    winningDatetime: null,
    finalizedById: null,
    finalizedAt: null,
    myVotes: {},
    ...overrides,
  };
}

function renderCard(event = makeEvent({ hasPoll: true })) {
  return render(
    <MemoryRouter>
      <EventPollCard event={event} />
    </MemoryRouter>,
  );
}

function mockPollResponse(data: EventPoll | undefined, isPending: boolean, isError: boolean) {
  const useEventPollMock = vi.mocked(useEventPoll);
  useEventPollMock.mockReturnValue({
    data,
    isPending,
    isError,
  } as ReturnType<typeof useEventPoll>);
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
});

describe('EventPollCard', () => {
  it('returns null when event has no poll', () => {
    mockPollResponse(undefined, false, false);

    const { container } = renderCard(makeEvent({ hasPoll: false }));
    expect(container.firstChild).toBeNull();
  });

  it('shows loading message while poll is pending', () => {
    mockPollResponse(undefined, true, false);

    renderCard();
    expect(screen.getByText('loading poll…')).toBeInTheDocument();
  });

  it('shows error message when poll fails to load', () => {
    mockPollResponse(undefined, false, true);

    renderCard();
    expect(screen.getByText("couldn't load the poll — try refreshing")).toBeInTheDocument();
  });

  it('renders poll options when poll loads', () => {
    const poll = makePoll({
      options: [
        makePollOption({ id: 'opt1', datetime: new Date('2026-09-15T19:00:00Z') }),
        makePollOption({ id: 'opt2', datetime: new Date('2026-09-16T19:00:00Z') }),
      ],
    });
    mockPollResponse(poll, false, false);

    renderCard();
    expect(screen.getByText('find a time')).toBeInTheDocument();
    expect(screen.getByText('2 options')).toBeInTheDocument();
  });

  it('shows sign in to vote link for unauthenticated users when poll not finalized', () => {
    mockPollResponse(makePoll(), false, false);

    renderCard();
    expect(screen.getByText('sign in to vote')).toBeInTheDocument();
  });

  it('shows respond to poll button for authenticated users when poll not finalized', () => {
    useAuthStore.setState({
      status: 'authed',
      user: makeUser({ id: 'user1' }),
      accessToken: 'tok',
    });
    mockPollResponse(makePoll(), false, false);

    renderCard();
    expect(screen.getByText('respond to poll')).toBeInTheDocument();
  });

  it('shows finalize and edit buttons for poll managers when poll not finalized', () => {
    useAuthStore.setState({
      status: 'authed',
      user: makeUser({
        id: 'user1',
        roles: [
          { id: 'r1', name: 'manager', isDefault: false, permissions: [Permission.ManageEvents] },
        ],
      }),
      accessToken: 'tok',
    });
    mockPollResponse(makePoll(), false, false);

    renderCard();
    expect(screen.getByText('finalize')).toBeInTheDocument();
    expect(screen.getByText('edit options')).toBeInTheDocument();
  });

  it('hides action buttons when poll is finalized', () => {
    useAuthStore.setState({
      status: 'authed',
      user: makeUser({
        id: 'user1',
        roles: [
          { id: 'r1', name: 'manager', isDefault: false, permissions: [Permission.ManageEvents] },
        ],
      }),
      accessToken: 'tok',
    });
    const winningDatetimeValue = new Date('2026-09-15T19:00:00Z');
    mockPollResponse(
      makePoll({
        winningDatetime: winningDatetimeValue,
        winningOptionId: 'opt1',
        finalizedAt: new Date('2026-09-01T10:00:00Z'),
      }),
      false,
      false,
    );

    renderCard();
    expect(screen.queryByText('respond to poll')).not.toBeInTheDocument();
    expect(screen.queryByText('finalize')).not.toBeInTheDocument();
    expect(screen.queryByText('edit options')).not.toBeInTheDocument();
  });

  it('displays finalized date when poll.finalizedAt is set', () => {
    const finalizedAt = new Date('2026-09-01T10:00:00Z');
    mockPollResponse(
      makePoll({
        winningDatetime: new Date('2026-09-15T19:00:00Z'),
        winningOptionId: 'opt1',
        finalizedAt,
      }),
      false,
      false,
    );

    renderCard();
    expect(screen.getByText(/finalized sep 1/)).toBeInTheDocument();
  });

  it('does not display finalized date when poll.finalizedAt is null', () => {
    mockPollResponse(makePoll({ finalizedAt: null }), false, false);

    renderCard();
    expect(screen.queryByText(/finalized/)).not.toBeInTheDocument();
  });

  it('shows poll card for co-hosts with finalize button when poll not finalized', () => {
    useAuthStore.setState({
      status: 'authed',
      user: makeUser({ id: 'creator' }),
      accessToken: 'tok',
    });
    mockPollResponse(makePoll(), false, false);

    renderCard(makeEvent({ hasPoll: true, coHostIds: ['creator'] }));
    expect(screen.getByText('finalize')).toBeInTheDocument();
  });

  it('does not show finalize button for non-managers', () => {
    useAuthStore.setState({
      status: 'authed',
      user: makeUser({ id: 'user1' }),
      accessToken: 'tok',
    });
    mockPollResponse(makePoll(), false, false);

    renderCard(makeEvent({ hasPoll: true, coHostIds: ['other'] }));
    expect(screen.queryByText('finalize')).not.toBeInTheDocument();
  });

  it('renders poll card (not null) when finalized instead of disappearing', () => {
    const poll = makePoll({
      options: [makePollOption({ id: 'opt1' })],
      winningDatetime: new Date('2026-09-15T19:00:00Z'),
      winningOptionId: 'opt1',
      finalizedAt: new Date('2026-09-01T10:00:00Z'),
    });
    mockPollResponse(poll, false, false);

    const { container } = renderCard();
    expect(container.querySelector('[class*="border-border"]')).toBeInTheDocument();
    expect(screen.getByText('find a time')).toBeInTheDocument();
  });
});
