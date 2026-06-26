import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  type Event,
  EventStatus,
  EventType,
  EventVisibility,
  RsvpServerStatus,
} from '@/models/event';

import { EventCardBadges } from './EventCardBadges';

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
    createdById: null,
    createdByName: null,
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
    invitePermission: 'all_members',
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

describe('EventCardBadges', () => {
  it('renders nothing when there is no rsvp and capacity is unlimited', () => {
    const { container } = render(<EventCardBadges event={makeEvent()} variant="card" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the viewer rsvp state', () => {
    render(
      <EventCardBadges event={makeEvent({ myRsvp: RsvpServerStatus.Attending })} variant="card" />,
    );
    expect(screen.getByText('going')).toBeInTheDocument();
  });

  it('shows going/{max} headcount for capacity-limited events', () => {
    render(
      <EventCardBadges event={makeEvent({ maxAttendees: 20, attendingCount: 8 })} variant="row" />,
    );
    expect(screen.getByText('8 / 20 going')).toBeInTheDocument();
  });

  it('omits the headcount for unlimited-capacity events', () => {
    render(
      <EventCardBadges
        event={makeEvent({ maxAttendees: null, myRsvp: RsvpServerStatus.Maybe })}
        variant="row"
      />,
    );
    expect(screen.getByText('maybe')).toBeInTheDocument();
    expect(screen.queryByText(/going$/)).not.toBeInTheDocument();
  });
});
