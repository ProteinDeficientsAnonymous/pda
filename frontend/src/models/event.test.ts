import { describe, expect, it } from 'vitest';

import {
  type Event,
  eventClass,
  EventStatus,
  EventType,
  EventVisibility,
  myRsvpLabel,
  RsvpServerStatus,
  spotsLeft,
} from './event';

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
    photoUpdatedAt: null,
    tags: [],
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

  it('returns club class for club events', () => {
    const event = makeEvent({ eventType: EventType.Club });
    expect(eventClass(event)).toBe('pda-evt pda-evt-club');
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

describe('spotsLeft', () => {
  it('returns null for unlimited-capacity events', () => {
    expect(spotsLeft(makeEvent({ maxAttendees: null, attendingCount: 5 }))).toBeNull();
  });

  it('returns remaining spots for capacity-limited events', () => {
    expect(spotsLeft(makeEvent({ maxAttendees: 10, attendingCount: 3 }))).toBe(7);
  });

  it('returns 0 when full', () => {
    expect(spotsLeft(makeEvent({ maxAttendees: 10, attendingCount: 10 }))).toBe(0);
  });

  it('clamps to 0 when over capacity (waitlist overflow)', () => {
    expect(spotsLeft(makeEvent({ maxAttendees: 10, attendingCount: 13 }))).toBe(0);
  });
});

describe('myRsvpLabel', () => {
  it('returns null when the viewer has not responded', () => {
    expect(myRsvpLabel(makeEvent({ myRsvp: null }))).toBeNull();
  });

  it('maps each rsvp status to a lowercase label', () => {
    expect(myRsvpLabel(makeEvent({ myRsvp: RsvpServerStatus.Attending }))).toBe('going');
    expect(myRsvpLabel(makeEvent({ myRsvp: RsvpServerStatus.Maybe }))).toBe('maybe');
    expect(myRsvpLabel(makeEvent({ myRsvp: RsvpServerStatus.CantGo }))).toBe("can't go");
    expect(myRsvpLabel(makeEvent({ myRsvp: RsvpServerStatus.Waitlisted }))).toBe('waitlisted');
  });

  it('returns null for an unrecognized status', () => {
    expect(myRsvpLabel(makeEvent({ myRsvp: 'bogus' }))).toBeNull();
  });
});
