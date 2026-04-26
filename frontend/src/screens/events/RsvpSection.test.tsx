import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '@/auth/store';
import {
  AttendanceStatus,
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
  RsvpServerStatus,
  type Event,
  type EventGuest,
} from '@/models/event';
import type { User } from '@/models/user';

const setRsvpMutate = vi.fn();
vi.mock('@/api/rsvp', () => ({
  useSetRsvp: () => ({ mutateAsync: setRsvpMutate, isPending: false }),
  useRemoveRsvp: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('./RsvpGuestList', () => ({
  RsvpGuestList: () => <div data-testid="guest-list" />,
}));

import { RsvpSection } from './RsvpSection';

const ME: User = {
  id: 'user-me',
  phoneNumber: '+12125550001',
  displayName: 'Me',
  email: '',
  bio: '',
  isSuperuser: false,
  isStaff: false,
  needsOnboarding: false,
  showPhone: false,
  showEmail: false,
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
    guests: [],
    myRsvp: RsvpServerStatus.Attending,
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
  useAuthStore.setState({ status: 'authed', user: ME, accessToken: 'tok' });
});

describe('RsvpSection — +1 toggle', () => {
  it('shows "remove +1" when MY guest record has a +1, even if other attendees do not', () => {
    // Issue #368 regression: previously the lookup matched by status, so
    // the toggle reflected some other attendee's hasPlusOne value.
    renderSection(
      makeEvent({
        guests: [
          makeGuest({ userId: 'user-other', hasPlusOne: false }),
          makeGuest({ userId: 'user-me', name: 'Me', hasPlusOne: true }),
        ],
      }),
    );

    expect(screen.getByRole('button', { name: 'remove +1' })).toBeInTheDocument();
  });

  it('shows "bring a +1" when MY guest record has no +1, even if another attendee does', () => {
    renderSection(
      makeEvent({
        guests: [
          makeGuest({ userId: 'user-other', hasPlusOne: true }),
          makeGuest({ userId: 'user-me', name: 'Me', hasPlusOne: false }),
        ],
      }),
    );

    expect(screen.getByRole('button', { name: 'bring a +1' })).toBeInTheDocument();
  });

  it('toggling off sends hasPlusOne: false', async () => {
    renderSection(
      makeEvent({
        guests: [makeGuest({ userId: 'user-me', name: 'Me', hasPlusOne: true })],
      }),
    );

    fireEvent.click(screen.getByRole('button', { name: 'remove +1' }));

    expect(setRsvpMutate).toHaveBeenCalledWith({
      eventId: 'ev1',
      status: RsvpServerStatus.Attending,
      hasPlusOne: false,
    });
  });

  it('toggling on sends hasPlusOne: true', async () => {
    renderSection(
      makeEvent({
        guests: [makeGuest({ userId: 'user-me', name: 'Me', hasPlusOne: false })],
      }),
    );

    fireEvent.click(screen.getByRole('button', { name: 'bring a +1' }));

    expect(setRsvpMutate).toHaveBeenCalledWith({
      eventId: 'ev1',
      status: RsvpServerStatus.Attending,
      hasPlusOne: true,
    });
  });

  it('hides the +1 button when allowPlusOnes is false', () => {
    renderSection(
      makeEvent({
        allowPlusOnes: false,
        guests: [makeGuest({ userId: 'user-me', name: 'Me' })],
      }),
    );

    expect(screen.queryByRole('button', { name: /\+1/ })).not.toBeInTheDocument();
  });

  it('hides the +1 button on the waitlist', () => {
    renderSection(
      makeEvent({
        myRsvp: RsvpServerStatus.Waitlisted,
        guests: [makeGuest({ userId: 'user-me', name: 'Me', status: RsvpServerStatus.Waitlisted })],
      }),
    );

    expect(screen.queryByRole('button', { name: /\+1/ })).not.toBeInTheDocument();
  });
});
