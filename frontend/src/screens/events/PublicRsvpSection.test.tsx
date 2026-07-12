import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import {
  type Event,
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
} from '@/models/event';

vi.mock('@/api/publicRsvp', () => ({
  useSubmitPublicRsvp: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

import { canPublicRsvp, PublicRsvpSection } from './PublicRsvpSection';

function makeEvent(overrides: Partial<Event> = {}): Event {
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
    invitePermission: InvitePermission.AllMembers,
    pendingCohostInvites: [],
    myPendingCohostInviteId: null,
    eventType: EventType.Official,
    visibility: EventVisibility.Public,
    photoUrl: '',
    photoUpdatedAt: null,
    tags: [],
    isPast: false,
    status: EventStatus.Active,
    ...overrides,
  };
}

describe('canPublicRsvp', () => {
  it('is true for official + public + rsvpEnabled + active + not-past', () => {
    expect(canPublicRsvp(makeEvent())).toBe(true);
  });
  it('is false for community events', () => {
    expect(canPublicRsvp(makeEvent({ eventType: EventType.Community }))).toBe(false);
  });
  it('is false for members-only visibility', () => {
    expect(canPublicRsvp(makeEvent({ visibility: EventVisibility.MembersOnly }))).toBe(false);
  });
  it('is false when rsvp disabled', () => {
    expect(canPublicRsvp(makeEvent({ rsvpEnabled: false }))).toBe(false);
  });
  it('is false when cancelled', () => {
    expect(canPublicRsvp(makeEvent({ status: EventStatus.Cancelled }))).toBe(false);
  });
  it('is false when past', () => {
    expect(canPublicRsvp(makeEvent({ isPast: true }))).toBe(false);
  });
});

describe('PublicRsvpSection', () => {
  it('renders the form heading initially', () => {
    render(
      <MemoryRouter>
        <PublicRsvpSection event={makeEvent()} />
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { name: 'rsvp' })).toBeInTheDocument();
  });
});
