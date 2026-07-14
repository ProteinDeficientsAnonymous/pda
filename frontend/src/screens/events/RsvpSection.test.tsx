import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
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
import type { User } from '@/models/user';

const setRsvpMutate = vi.fn();
const removeRsvpMutate = vi.fn();
vi.mock('@/api/rsvp', () => ({
  useSetRsvp: () => ({ mutateAsync: setRsvpMutate, isPending: false }),
  useRemoveRsvp: () => ({ mutateAsync: removeRsvpMutate, isPending: false }),
}));

vi.mock('./RsvpGuestList', () => ({
  RsvpGuestList: () => <div data-testid="guest-list" />,
}));

// Covered by RsvpNoteField.test.tsx — stubbed here so the RsvpBox's textarea
// isn't a factor in assertions that only care about the dialog/pills.
vi.mock('./RsvpNoteField', () => ({
  RsvpNoteField: () => <div data-testid="rsvp-note-field" />,
}));

import { RsvpSection } from './RsvpSection';

const ME: User = {
  id: 'user-me',
  phoneNumber: '+12125550001',
  firstName: 'Me',
  lastName: '',
  fullName: 'Me',
  nickname: '',
  email: '',
  bio: '',
  pronouns: '',
  birthday: null,
  isSuperuser: false,
  isStaff: false,
  needsOnboarding: false,
  needsPasswordReset: false,
  needsGuidelinesConsent: false,
  needsSmsConsent: false,
  showPhone: false,
  showEmail: false,
  hideLastName: false,
  weekStart: 'sunday',
  calendarFeedScope: 'all',
  profilePhotoUrl: '',
  photoUpdatedAt: null,
  roles: [],
};

function makeGuest(overrides: Partial<EventGuest>): EventGuest {
  return {
    userId: 'user-other',
    name: 'Other',
    status: RsvpServerStatus.Attending,
    phone: null,
    photoUrl: '',
    hasPlusOne: false,
    attendance: AttendanceStatus.Unknown,
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
    guests: [],
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
    ...overrides,
  };
}

function renderSection(event: Event) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <RsvpSection event={event} canSeeInvited={false} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  setRsvpMutate.mockReset();
  setRsvpMutate.mockResolvedValue(undefined);
  removeRsvpMutate.mockReset();
  removeRsvpMutate.mockResolvedValue(undefined);
  useAuthStore.setState({ status: 'authed', user: ME, accessToken: 'tok' });
});

describe('RsvpSection — before RSVPing', () => {
  it('opens the RSVP box when a pill is tapped (not yet RSVP’d)', () => {
    renderSection(makeEvent({ myRsvp: null }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: "i'm going" }));

    expect(screen.getByRole('dialog', { name: /RSVP/i })).toBeInTheDocument();
  });

  it('shows all three pills and no status line when I have not RSVP’d', () => {
    renderSection(makeEvent({ myRsvp: null }));

    expect(screen.getByRole('button', { name: "i'm going" })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'maybe' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: "can't go" })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit RSVP/i })).not.toBeInTheDocument();
  });

  it('shows "join the waitlist" instead of "i\'m going" when the event is full', () => {
    renderSection(makeEvent({ maxAttendees: 2, attendingCount: 2, myRsvp: null }));

    expect(screen.getByRole('button', { name: 'join the waitlist' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "i'm going" })).not.toBeInTheDocument();
  });
});

describe('RsvpSection — after RSVPing', () => {
  it('shows an edit RSVP button and no status pills once the member has responded', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Attending }));

    expect(screen.queryByRole('button', { name: "i'm going" })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'maybe' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "can't go" })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /edit RSVP/i })).toBeInTheDocument();
  });

  it('shows a "you\'re going" status line when attending', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Attending }));
    expect(screen.getByText("you're going")).toBeInTheDocument();
  });

  it('shows a "you\'re a maybe" status line when maybe', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Maybe }));
    expect(screen.getByText("you're a maybe")).toBeInTheDocument();
  });

  it('shows a "you can\'t go" status line when cant_go', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.CantGo }));
    expect(screen.getByText("you can't go")).toBeInTheDocument();
  });

  it('opens the RSVP box in edit mode when "edit RSVP" is tapped', () => {
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Attending }));

    fireEvent.click(screen.getByRole('button', { name: /edit RSVP/i }));

    expect(screen.getByRole('dialog', { name: /RSVP/i })).toBeInTheDocument();
  });

  it('shows only "leave waitlist" when on the waitlist (no pills, no status line, no edit button)', () => {
    renderSection(
      makeEvent({
        myRsvp: RsvpServerStatus.Waitlisted,
        guests: [makeGuest({ userId: 'user-me', name: 'Me', status: RsvpServerStatus.Waitlisted })],
      }),
    );

    expect(screen.getByRole('button', { name: 'leave waitlist' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit RSVP/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "i'm going" })).not.toBeInTheDocument();
  });
});

describe('RsvpSection — spots left indicator', () => {
  it('shows spots left when the event has a cap and room remains', () => {
    renderSection(makeEvent({ maxAttendees: 4, attendingCount: 2, myRsvp: null }));
    expect(screen.getByText('2 spots left')).toBeInTheDocument();
  });

  it('hides spots left when uncapped', () => {
    renderSection(makeEvent({ maxAttendees: null, attendingCount: 2, myRsvp: null }));
    expect(screen.queryByText(/spots left/)).not.toBeInTheDocument();
  });

  it('hides spots left at capacity', () => {
    renderSection(makeEvent({ maxAttendees: 2, attendingCount: 2, myRsvp: null }));
    expect(screen.queryByText(/spots left/)).not.toBeInTheDocument();
  });
});

describe('RsvpSection — spots left', () => {
  it('shows "x spots left" for a capacity-limited event with room', () => {
    renderSection(makeEvent({ maxAttendees: 10, attendingCount: 7, myRsvp: null }));
    expect(screen.getByText('3 spots left')).toBeInTheDocument();
  });

  it('singularizes "1 spot left"', () => {
    renderSection(makeEvent({ maxAttendees: 10, attendingCount: 9, myRsvp: null }));
    expect(screen.getByText('1 spot left')).toBeInTheDocument();
  });

  it('shows no spots-left text for unlimited-capacity events', () => {
    renderSection(makeEvent({ maxAttendees: null, attendingCount: 7, myRsvp: null }));
    expect(screen.queryByText(/spots? left/)).not.toBeInTheDocument();
  });

  it('shows no spots-left text at capacity', () => {
    renderSection(makeEvent({ maxAttendees: 10, attendingCount: 10, myRsvp: null }));
    expect(screen.queryByText(/spots? left/)).not.toBeInTheDocument();
  });
});

describe('RsvpSection — leave waitlist error handling (issue #633)', () => {
  it('surfaces an error when leaving the waitlist fails', async () => {
    removeRsvpMutate.mockRejectedValue(new Error('boom'));
    renderSection(makeEvent({ myRsvp: RsvpServerStatus.Waitlisted }));

    fireEvent.click(screen.getByRole('button', { name: 'leave waitlist' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/couldn't update your rsvp/i);
  });
});
