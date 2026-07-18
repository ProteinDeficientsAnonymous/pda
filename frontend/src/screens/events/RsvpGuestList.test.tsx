import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  AttendanceStatus,
  type Event,
  type EventGuest,
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
  RsvpServerStatus,
} from '@/models/event';

const setGuestRsvpMutate = vi.fn();
vi.mock('@/api/eventStats', () => ({
  useSetGuestRsvp: () => ({ mutate: setGuestRsvpMutate, isPending: false }),
}));

import { RsvpGuestList } from './RsvpGuestList';

function makeGuest(overrides: Partial<EventGuest>): EventGuest {
  return {
    userId: 'user-other',
    name: 'Other',
    status: RsvpServerStatus.Attending,
    phone: null,
    photoUrl: '',
    hasPlusOne: false,
    attendance: AttendanceStatus.Unknown,
    isMember: true,
    ...overrides,
  };
}

function makeEvent(overrides: Partial<Event>): Event {
  return {
    id: 'ev1',
    title: 'Potluck',
    description: '',
    startDatetime: new Date('2099-06-01T18:00:00Z'),
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
    allowPlusOnes: true,
    maxAttendees: null,
    attendingCount: 0,
    waitlistedCount: 0,
    invitedCount: 0,
    datetimeTbd: false,
    hasPoll: false,
    datetimePollSlug: null,
    createdById: 'user-host',
    createdByName: 'Host',
    createdByPhotoUrl: '',
    coHostIds: [],
    coHostNames: [],
    coHostPhotoUrls: [],
    coHostInviteIds: [],
    guests: [makeGuest({})],
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
    viewerUserId: null,
    ...overrides,
  };
}

function renderList(event: Event, canManageRsvps = false) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <RsvpGuestList event={event} canSeeInvited={false} canManageRsvps={canManageRsvps} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  setGuestRsvpMutate.mockReset();
});

describe('RsvpGuestList', () => {
  it('links member guests to their profile', () => {
    const event = makeEvent({
      guests: [makeGuest({ userId: 'user-1', name: 'Alex', isMember: true })],
    });
    renderList(event);
    const link = screen.getByRole('link', { name: /alex/i });
    expect(link).toHaveAttribute('href', '/members/user-1');
  });

  it('renders non-member guests without a profile link', () => {
    const event = makeEvent({
      guests: [makeGuest({ userId: 'guest-1', name: 'Sam', isMember: false, hasPlusOne: true })],
    });
    renderList(event);
    expect(screen.queryByRole('link', { name: /sam/i })).not.toBeInTheDocument();
    expect(screen.getByText('Sam')).toBeInTheDocument();
  });
});

describe('RsvpGuestList — host rsvp management (Issue 872)', () => {
  it('does not show an edit control when the viewer cannot manage rsvps', () => {
    renderList(makeEvent({}), false);
    expect(screen.queryByRole('button', { name: /change other's rsvp/i })).not.toBeInTheDocument();
  });

  it('shows an edit control per guest when the viewer can manage rsvps', () => {
    renderList(makeEvent({}), true);
    expect(screen.getByRole('button', { name: /change other's rsvp/i })).toBeInTheDocument();
  });

  it('does not show an edit control for non-member guests', () => {
    renderList(makeEvent({ guests: [makeGuest({ isMember: false })] }), true);
    expect(screen.queryByRole('button', { name: /change other's rsvp/i })).not.toBeInTheDocument();
  });

  it('opens a dialog with status options when edit is tapped', () => {
    renderList(makeEvent({}), true);
    fireEvent.click(screen.getByRole('button', { name: /change other's rsvp/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^maybe$/i })).toBeInTheDocument();
  });

  it('calls the mutation with the selected status', () => {
    renderList(makeEvent({}), true);
    fireEvent.click(screen.getByRole('button', { name: /change other's rsvp/i }));
    fireEvent.click(screen.getByRole('button', { name: /^maybe$/i }));
    expect(setGuestRsvpMutate).toHaveBeenCalledWith(
      { userId: 'user-other', status: 'maybe', hasPlusOne: false },
      expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) }),
    );
  });
});
