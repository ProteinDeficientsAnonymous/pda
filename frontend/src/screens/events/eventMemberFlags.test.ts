import { describe, expect, it } from 'vitest';

import { EventStatus, RsvpStatus } from '@/models/event';
import { MembershipStatus } from '@/models/user';
import { makeEvent, makeUser } from '@/test/fixtures';

import { eventMemberSectionFlags } from './eventMemberFlags';

describe('eventMemberSectionFlags rsvpLocked', () => {
  const draft = makeEvent({ status: EventStatus.Draft, createdById: 'user1', coHostIds: [] });

  it('locks rsvps on a draft for its hostless creator', () => {
    expect(eventMemberSectionFlags(draft, makeUser()).rsvpLocked).toBe(true);
  });

  it('keeps rsvps open on a draft for a co-host', () => {
    const hosted = { ...draft, coHostIds: ['user1'] };
    expect(eventMemberSectionFlags(hosted, makeUser()).rsvpLocked).toBe(false);
  });
});

describe('eventMemberSectionFlags rsvpsClosed', () => {
  const pastDeadline = makeEvent({
    rsvpDeadline: new Date(Date.now() - 60 * 60 * 1000),
    coHostIds: ['host'],
  });

  it('closes rsvps for a guest once the deadline passes', () => {
    expect(eventMemberSectionFlags(pastDeadline, makeUser()).rsvpsClosed).toBe(true);
  });

  it('keeps rsvps open for a co-host past the deadline', () => {
    const host = makeUser({ id: 'host' });
    expect(eventMemberSectionFlags(pastDeadline, host).rsvpsClosed).toBe(false);
  });

  it('closes rsvps for a guest when a host closed them, with no deadline', () => {
    const closed = makeEvent({ rsvpsClosed: true, coHostIds: ['host'] });
    expect(eventMemberSectionFlags(closed, makeUser()).rsvpsClosed).toBe(true);
    expect(eventMemberSectionFlags(closed, makeUser({ id: 'host' })).rsvpsClosed).toBe(false);
  });
});

describe('eventMemberSectionFlags canInvite', () => {
  const rsvpd = makeEvent({ rsvpEnabled: true, myRsvp: RsvpStatus.Attending });

  it('lets a member who rsvpd invite', () => {
    expect(eventMemberSectionFlags(rsvpd, makeUser()).canInvite).toBe(true);
  });

  it.each([MembershipStatus.Tentative, MembershipStatus.AttendancePaused])(
    'hides the invite button from a %s user',
    (membershipStatus) => {
      const user = makeUser({ membershipStatus });
      expect(eventMemberSectionFlags(rsvpd, user).canInvite).toBe(false);
    },
  );
});
