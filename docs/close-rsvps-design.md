# Close RSVPs

## Why

Hosts need to stop sign-ups when an event is full for reasons outside the cap. Example: the movie club's tickets sold out, or an event without a cap grew past what the host wants. Today's workarounds (set a cap, set the deadline to now) leak: when a guest switches to can't go, the next waitlisted guest is auto-promoted, so the spot reopens. Closed has to mean closed: cancellations free nothing.

## Goals

- A host can close RSVPs on an event and reopen them later.
- While closed: no new RSVPs, no joining the waitlist, no adding a +1, and no waitlist promotion.
- Going guests can still step down (can't go, drop a +1), and waitlisted guests can still leave.

## Non-goals

- Auto-closing on a schedule (that's the deadline).
- Notifying guests when RSVPs close or reopen.
- Changing how the deadline or cap behave.

## Approaches

- **A: separate "rsvps closed" switch (picked).** A new event field, independent of the deadline and cap. It reuses the passed-deadline gate and also stops waitlist promotion.
- **B: "close now" sets the deadline to now, and a passed deadline stops the waitlist.** No new field, but it overwrites a deadline the host set on purpose, and it changes behavior for every existing deadline event, whose waitlists would freeze.

## Design

**Backend**
- `Event.rsvps_closed_at` (nullable datetime; null means open). `EventOut` exposes `rsvps_closed: bool`.
- Hosts toggle it through the existing event `PATCH` with `rsvps_closed: true|false`. Editing permission applies, so hosts and event managers can do it.
- RSVP gate: generalize `enforce_rsvp_deadline` (`community/rsvps/_deadline.py`) so closed RSVPs block everything except stepping down, just like a passed deadline. Hosts are exempt. Add a new error code, `event.rsvps_closed_by_host`, so the message doesn't mention a deadline. Every RSVP write path must hit the gate: member create/update, public create/manage, and waitlist join.
- Waitlist: `_waitlist_closed` (`community/rsvps/waitlist.py`) also returns true while closed, so no promotion on cancellations, cap changes or host reorders. Reopening goes through the event update, which already calls `promote_from_waitlist`, so the line moves if there's room.
- Audit-log close and reopen.

**Frontend**
- Event detail kebab (`EventDetailKebabMenu.tsx`): a "close rsvps" / "reopen rsvps" item. Visible only to people who can manage RSVPs, and only when RSVPs are enabled and the event isn't a draft, cancelled or past.
- Closing opens a short confirm dialog: "no one new can rsvp or join the waitlist, and cancellations won't open spots." Reopening needs no confirm.
- Guest side: the existing deadline-closed RSVP state shows "rsvps are closed" when `rsvps_closed` is set. Step-down actions stay available.

## Left to the builder

- Exact copy for the closed state and the confirm dialog (lowercase).
- Whether to rename `enforce_rsvp_deadline` now that it covers two cases.
- Split into stacked PRs to stay under the PR size gate: backend first, then frontend.
