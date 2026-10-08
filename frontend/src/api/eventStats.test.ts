import { describe, expect, it } from 'vitest';

import { RsvpServerStatus } from '@/models/event';
import { makeEvent, makeGuest } from '@/test/fixtures';

import { withWaitlistOrder } from './eventStats';

describe('withWaitlistOrder', () => {
  it('reorders only the waitlisted guests, leaving others in place', () => {
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'w1', status: RsvpServerStatus.Waitlisted }),
        makeGuest({ userId: 'a1', status: RsvpServerStatus.Attending }),
        makeGuest({ userId: 'w2', status: RsvpServerStatus.Waitlisted }),
        makeGuest({ userId: 'w3', status: RsvpServerStatus.Waitlisted }),
      ],
    });
    const ids = withWaitlistOrder(event, ['w3', 'w1', 'w2']).guests.map((g) => g.userId);
    expect(ids).toEqual(['w3', 'a1', 'w1', 'w2']);
  });

  it('keeps unknown waitlisted guests at the end', () => {
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'w1', status: RsvpServerStatus.Waitlisted }),
        makeGuest({ userId: 'w2', status: RsvpServerStatus.Waitlisted }),
      ],
    });
    const ids = withWaitlistOrder(event, ['w2']).guests.map((g) => g.userId);
    expect(ids).toEqual(['w2', 'w1']);
  });
});
