import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { Event, EventStats } from '@/models/event';
import {
  AttendanceStatus,
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
  RsvpServerStatus,
} from '@/models/event';

const setAttendanceMutate = vi.fn();

vi.mock('@/api/eventStats', () => ({
  useEventStats: vi.fn(),
  useSetAttendance: () => ({ mutate: setAttendanceMutate, isPending: false }),
}));

import { useEventStats } from '@/api/eventStats';

import { EventAttendancePanel } from './EventAttendancePanel';

const BASE_EVENT: Event = {
  id: 'ev1',
  title: 'Test Event',
  description: '',
  // Anchored well into the future relative to "now" so the check-in window
  // (opens an hour before start) stays closed regardless of when the suite runs.
  // A hardcoded calendar date rots — once it passes, the "hides check-in until
  // an hour before" test starts seeing the buttons.
  startDatetime: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
  endDatetime: null,
  location: '',
  latitude: null,
  longitude: null,
  whatsappLink: '',
  partifulLink: '',
  otherLink: '',
  venmoLink: '',
  cashappLink: '',
  zelleInfo: '',
  price: '',
  rsvpEnabled: true,
  allowPlusOnes: false,
  maxAttendees: null,
  attendingCount: 1,
  waitlistedCount: 0,
  invitedCount: 2,
  datetimeTbd: false,
  hasPoll: false,
  datetimePollSlug: null,
  createdById: 'creator',
  createdByName: 'Creator',
  createdByPhotoUrl: '',
  coHostIds: [],
  coHostNames: [],
  coHostPhotoUrls: [],
  coHostInviteIds: [],
  guests: [
    {
      userId: 'alice',
      name: 'alice',
      status: RsvpServerStatus.Attending,
      phone: null,
      photoUrl: '',
      hasPlusOne: false,
      attendance: AttendanceStatus.Unknown,
    },
  ],
  myRsvp: null,
  surveySlugs: [],
  invitedUserIds: [],
  invitedUserNames: [],
  invitedUserPhotoUrls: [],
  invitePermission: InvitePermission.AllMembers,
  pendingCohostInvites: [],
  myPendingCohostInviteId: null,
  eventType: EventType.Community,
  visibility: EventVisibility.Public,
  photoUrl: '',
  photoUpdatedAt: null,
  tags: [],
  isPast: false,
  status: EventStatus.Active,
};

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
  vi.mocked(useEventStats).mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('EventAttendancePanel', () => {
  it('renders stats chips when loaded', () => {
    mockStats(BASE_STATS);
    renderPanel(BASE_EVENT);

    // Card is collapsed by default; expand it.
    fireEvent.click(screen.getByRole('button', { name: /attendance/i }));

    expect(screen.getByText(/going/)).toBeInTheDocument();
    expect(screen.getByText(/can't go/)).toBeInTheDocument();
    expect(screen.getByText(/no response/)).toBeInTheDocument();
  });

  it('hides check-in buttons until an hour before the event', () => {
    mockStats(BASE_STATS);
    renderPanel(BASE_EVENT);
    fireEvent.click(screen.getByRole('button', { name: /attendance/i }));

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
    fireEvent.click(screen.getByRole('button', { name: /attendance/i }));

    const attendedBtn = screen.getByRole('button', { name: /^attended$/i });
    fireEvent.click(attendedBtn);

    expect(setAttendanceMutate).toHaveBeenCalledWith({
      userId: 'alice',
      attendance: AttendanceStatus.Attended,
    });
  });

  it('shows check-in buttons after the event (window never closes)', () => {
    mockStats(BASE_STATS);
    const pastEvent: Event = { ...BASE_EVENT, isPast: true };
    renderPanel(pastEvent);
    fireEvent.click(screen.getByRole('button', { name: /attendance/i }));

    expect(screen.getByRole('button', { name: /^attended$/i })).toBeInTheDocument();
  });

  it('renders cancellations list before the event opens for check-in', () => {
    mockStats(BASE_STATS);
    renderPanel(BASE_EVENT);
    fireEvent.click(screen.getByRole('button', { name: /attendance/i }));

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
    fireEvent.click(screen.getByRole('button', { name: /attendance/i }));

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
    fireEvent.click(screen.getByRole('button', { name: /attendance/i }));

    expect(screen.getByText(/couldn't load stats/i)).toBeInTheDocument();
  });
});
