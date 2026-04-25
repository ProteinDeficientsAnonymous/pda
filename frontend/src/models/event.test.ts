import { describe, it, expect } from 'vitest';
import { eventClass, EventStatus, EventType, EventVisibility, type Event } from './event';

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 'test-id',
    title: 'Test Event',
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

describe('eventClass', () => {
  it('returns cancelled class for cancelled events (highest precedence)', () => {
    const event = makeEvent({
      status: EventStatus.Cancelled,
      eventType: EventType.Official,
      visibility: EventVisibility.InviteOnly,
    });
    expect(eventClass(event)).toBe('pda-evt pda-evt-cancelled');
  });

  it('returns official class for official events', () => {
    const event = makeEvent({ eventType: EventType.Official });
    expect(eventClass(event)).toBe('pda-evt pda-evt-official');
  });

  it('returns invite class for invite-only community events', () => {
    const event = makeEvent({
      eventType: EventType.Community,
      visibility: EventVisibility.InviteOnly,
    });
    expect(eventClass(event)).toBe('pda-evt pda-evt-invite');
  });

  it('returns members class for members-only community events', () => {
    const event = makeEvent({
      eventType: EventType.Community,
      visibility: EventVisibility.MembersOnly,
    });
    expect(eventClass(event)).toBe('pda-evt pda-evt-members');
  });

  it('returns community class for public community events', () => {
    const event = makeEvent({
      eventType: EventType.Community,
      visibility: EventVisibility.Public,
    });
    expect(eventClass(event)).toBe('pda-evt pda-evt-community');
  });

  it('official takes precedence over invite-only', () => {
    const event = makeEvent({
      eventType: EventType.Official,
      visibility: EventVisibility.InviteOnly,
    });
    expect(eventClass(event)).toBe('pda-evt pda-evt-official');
  });

  it('invite-only takes precedence over members-only', () => {
    const event = makeEvent({
      eventType: EventType.Community,
      visibility: EventVisibility.InviteOnly,
    });
    expect(eventClass(event)).not.toBe('pda-evt pda-evt-members');
    expect(eventClass(event)).toBe('pda-evt pda-evt-invite');
  });
});
