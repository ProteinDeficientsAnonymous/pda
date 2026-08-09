import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useEventStats } from '@/api/eventStats';
import type { Event, EventStats } from '@/models/event';
import { AttendanceStatus, RsvpServerStatus } from '@/models/event';
import { makeEvent, makeGuest } from '@/test/fixtures';

import { EventAttendancePanel } from './EventAttendancePanel';

const setAttendanceMutate = vi.hoisted(() => vi.fn());
const toastError = vi.hoisted(() => vi.fn());

vi.mock('sonner', () => ({
  toast: {
    error: (m: string) => {
      toastError(m);
    },
  },
}));

vi.mock('@/api/eventStats', () => ({
  useEventStats: vi.fn(),
  useSetAttendance: () => ({ mutate: setAttendanceMutate, isPending: false }),
}));

const BASE_EVENT = makeEvent({
  invitedCount: 2,
  guests: [makeGuest({ userId: 'alice', name: 'alice' })],
});

const BASE_STATS: EventStats = {
  goingCount: 1,
  maybeCount: 0,
  cantGoCount: 1,
  noResponseCount: 1,
  waitlistedCount: 0,
  attendedCount: 0,
  noShowCount: 0,
  notMarkedCount: 1,
  cancellations: [
    {
      userId: 'bob',
      name: 'bob',
      cancelledAt: new Date('2026-05-29T12:00:00Z'),
      daysBeforeEvent: 3,
    },
  ],
};

const MIXED_RSVP_EVENT = makeEvent({
  isPast: true,
  guests: [
    makeGuest({ userId: 'alice', name: 'alice', status: RsvpServerStatus.Attending }),
    makeGuest({ userId: 'mabel', name: 'mabel', status: RsvpServerStatus.Maybe }),
    makeGuest({ userId: 'cassie', name: 'cassie', status: RsvpServerStatus.CantGo }),
  ],
});

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderPanel(event: Event) {
  return render(
    <QueryClientProvider client={makeQc()}>
      <EventAttendancePanel event={event} />
    </QueryClientProvider>,
  );
}

function mockStats(stats: EventStats | null, state: 'loading' | 'error' | 'success' = 'success') {
  vi.mocked(useEventStats).mockReturnValue({
    data: state === 'success' ? stats : undefined,
    isLoading: state === 'loading',
    isError: state === 'error',
  } as unknown as ReturnType<typeof useEventStats>);
}

// Freeze "now" a week before BASE_EVENT so the check-in window (open 1h before start,
// vs real Date.now()) is deterministic instead of rotting with wall-clock time (Issue 516).
const FROZEN_NOW = new Date('2026-05-25T12:00:00Z');

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(FROZEN_NOW);
  setAttendanceMutate.mockClear();
  toastError.mockClear();
  vi.mocked(useEventStats).mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('EventAttendancePanel', () => {
  it('renders stats chips when loaded', () => {
    mockStats(BASE_STATS);
    renderPanel(BASE_EVENT);

    expect(screen.getByText(/going/)).toBeInTheDocument();
    expect(screen.getByText(/can't go/)).toBeInTheDocument();
    expect(screen.getByText(/no response/)).toBeInTheDocument();
  });

  it('hides check-in buttons until an hour before the event', () => {
    mockStats(BASE_STATS);
    renderPanel(BASE_EVENT);
    expect(screen.queryByRole('button', { name: /^attended$/i })).not.toBeInTheDocument();
    expect(screen.getByText(/check-in opens an hour before the event/i)).toBeInTheDocument();
  });

  it('shows check-in buttons once the window opens and fires setAttendance on click', () => {
    mockStats(BASE_STATS);
    // Event starts in 30 min → within the 1-hour check-in window.
    const soonEvent: Event = {
      ...BASE_EVENT,
      startDatetime: new Date(Date.now() + 30 * 60 * 1000),
    };
    renderPanel(soonEvent);
    const attendedBtn = screen.getByRole('button', { name: /^attended$/i });
    fireEvent.click(attendedBtn);

    expect(setAttendanceMutate).toHaveBeenCalledWith(
      { userId: 'alice', attendance: AttendanceStatus.Attended, forPlusOne: false },
      expect.objectContaining({ onError: expect.any(Function) }),
    );
  });

  it('fires setAttendance with forPlusOne when the guest has a +1', () => {
    mockStats(BASE_STATS);
    const soonEvent: Event = {
      ...BASE_EVENT,
      guests: [
        makeGuest({ userId: 'alice', name: 'alice', hasPlusOne: true }),
      ],
      startDatetime: new Date(Date.now() + 30 * 60 * 1000),
    };
    renderPanel(soonEvent);

    expect(screen.getByText(/alice.?s \+1/i)).toBeInTheDocument();
    const attendedButtons = screen.getAllByRole('button', { name: /^attended$/i });
    fireEvent.click(attendedButtons[1]!);

    expect(setAttendanceMutate).toHaveBeenCalledWith(
      { userId: 'alice', attendance: AttendanceStatus.Attended, forPlusOne: true },
      expect.objectContaining({ onError: expect.any(Function) }),
    );
  });

  it('toasts an error when a check-in fails (issue #634)', () => {
    mockStats(BASE_STATS);
    setAttendanceMutate.mockImplementation(
      (_args: unknown, opts?: { onError?: (err: unknown) => void }) => {
        opts?.onError?.(new Error('boom'));
      },
    );
    const soonEvent: Event = {
      ...BASE_EVENT,
      startDatetime: new Date(Date.now() + 30 * 60 * 1000),
    };
    renderPanel(soonEvent);

    fireEvent.click(screen.getByRole('button', { name: /^attended$/i }));

    expect(toastError).toHaveBeenCalledWith(expect.stringMatching(/couldn't save check-in/i));
  });

  it('shows check-in buttons after the event (window never closes)', () => {
    mockStats(BASE_STATS);
    const pastEvent: Event = { ...BASE_EVENT, isPast: true };
    renderPanel(pastEvent);
    expect(screen.getByRole('button', { name: /^attended$/i })).toBeInTheDocument();
  });

  it('lists guests of every rsvp status by default', () => {
    mockStats(BASE_STATS);
    renderPanel(MIXED_RSVP_EVENT);

    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('mabel')).toBeInTheDocument();
    expect(screen.getByText('cassie')).toBeInTheDocument();
  });

  it('narrows the list to one rsvp status when a filter chip is picked', () => {
    mockStats(BASE_STATS);
    renderPanel(MIXED_RSVP_EVENT);

    fireEvent.click(screen.getByRole('button', { name: /^maybe$/i }));

    expect(screen.getByText('mabel')).toBeInTheDocument();
    expect(screen.queryByText('alice')).not.toBeInTheDocument();
    expect(screen.queryByText('cassie')).not.toBeInTheDocument();
  });

  it('restores the full list when the "all" chip is picked again', () => {
    mockStats(BASE_STATS);
    renderPanel(MIXED_RSVP_EVENT);

    fireEvent.click(screen.getByRole('button', { name: /^maybe$/i }));
    fireEvent.click(screen.getByRole('button', { name: /^all$/i }));

    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('mabel')).toBeInTheDocument();
    expect(screen.getByText('cassie')).toBeInTheDocument();
  });

  it('renders cancellations list before the event opens for check-in', () => {
    mockStats(BASE_STATS);
    renderPanel(BASE_EVENT);
    expect(screen.getByText(/cancelled 3 days before/i)).toBeInTheDocument();
  });

  it('filters cancellations by "within N days" when host enters a value', () => {
    const stats: EventStats = {
      ...BASE_STATS,
      cancellations: [
        {
          userId: 'early',
          name: 'early bird',
          cancelledAt: new Date('2026-05-20T00:00:00Z'),
          daysBeforeEvent: 12,
        },
        {
          userId: 'late',
          name: 'late one',
          cancelledAt: new Date('2026-05-31T00:00:00Z'),
          daysBeforeEvent: 1,
        },
      ],
    };
    mockStats(stats);
    renderPanel(BASE_EVENT);
    expect(screen.getByText('early bird')).toBeInTheDocument();
    expect(screen.getByText('late one')).toBeInTheDocument();

    // Bump filter from "all" → 1 → 2 days.
    const plus = screen.getByRole('button', { name: /more days/i });
    fireEvent.click(plus);
    fireEvent.click(plus);

    expect(screen.queryByText('early bird')).not.toBeInTheDocument();
    expect(screen.getByText('late one')).toBeInTheDocument();

    // Walk it back down to "all" — both visible again.
    const minus = screen.getByRole('button', { name: /fewer days/i });
    fireEvent.click(minus);
    fireEvent.click(minus);

    expect(screen.getByText('early bird')).toBeInTheDocument();
    expect(screen.getByText('late one')).toBeInTheDocument();
  });

  it('shows error state when stats fail to load', () => {
    mockStats(null, 'error');
    renderPanel(BASE_EVENT);
    expect(screen.getByText(/couldn't load stats/i)).toBeInTheDocument();
  });
});
