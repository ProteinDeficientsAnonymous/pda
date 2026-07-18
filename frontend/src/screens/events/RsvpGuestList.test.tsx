import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

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

import { RsvpGuestList } from './RsvpGuestList';

function makeGuest(overrides: Partial<EventGuest>): EventGuest {
  return {
    userId: 'user-1',
    name: 'Alex',
    status: RsvpServerStatus.Attending,
    phone: null,
    photoUrl: '',
    hasPlusOne: false,
    attendance: AttendanceStatus.Unknown,
    isMember: true,
    ...overrides,
  };
}

function makeEvent(guests: EventGuest[]): Event {
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
    attendingCount: guests.length,
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
    guests,
    myRsvp: null,
    viewerUserId: null,
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
}

describe('RsvpGuestList', () => {
  it('links member guests to their profile', () => {
    const event = makeEvent([makeGuest({ userId: 'user-1', name: 'Alex', isMember: true })]);
    render(
      <MemoryRouter>
        <RsvpGuestList event={event} canSeeInvited={false} />
      </MemoryRouter>,
    );
    const link = screen.getByRole('link', { name: /alex/i });
    expect(link).toHaveAttribute('href', '/members/user-1');
  });

  it('renders non-member guests without a profile link', () => {
    const event = makeEvent([
      makeGuest({ userId: 'guest-1', name: 'Sam', isMember: false, hasPlusOne: true }),
    ]);
    render(
      <MemoryRouter>
        <RsvpGuestList event={event} canSeeInvited={false} />
      </MemoryRouter>,
    );
    expect(screen.queryByRole('link', { name: /sam/i })).not.toBeInTheDocument();
    expect(screen.getByText('Sam')).toBeInTheDocument();
  });
});
