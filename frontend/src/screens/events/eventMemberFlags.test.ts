import { describe, expect, it } from 'vitest';

import { EventStatus } from '@/models/event';
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
