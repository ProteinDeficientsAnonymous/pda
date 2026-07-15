import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  type Event,
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
} from '@/models/event';

import { EventBadge } from './EventBadge';

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 'ev1',
    title: 'potluck',
    description: '',
    startDatetime: new Date('2026-04-15T18:00:00Z'),
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
    rsvpEnabled: false,
    allowPlusOnes: false,
    maxAttendees: null,
    attendingCount: 0,
    waitlistedCount: 0,
    invitedCount: 0,
    datetimeTbd: false,
    hasPoll: false,
    datetimePollSlug: null,
    createdById: 'u1',
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
    invitePermission: InvitePermission.CoHostsOnly,
    pendingCohostInvites: [],
    myPendingCohostInviteId: null,
    eventType: EventType.Community,
    visibility: EventVisibility.Public,
    photoUrl: '',
    photoUpdatedAt: null,
    isPast: false,
    status: EventStatus.Active,
    tags: [],
    ...overrides,
  };
}

describe('EventBadge', () => {
  it('renders an official badge', () => {
    render(<EventBadge event={makeEvent({ eventType: EventType.Official })} />);
    expect(screen.getByText('official')).toBeInTheDocument();
  });

  it('renders a club badge', () => {
    render(<EventBadge event={makeEvent({ eventType: EventType.Club })} />);
    expect(screen.getByText('pda club')).toBeInTheDocument();
  });
});
