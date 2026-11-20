# Close RSVPs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hosts can close and reopen RSVPs on an event from the event detail kebab. While closed, nothing new gets in and cancellations don't promote the waitlist.

**Architecture:** A nullable `Event.rsvps_closed_at`, toggled through the existing event PATCH (`rsvps_closed: bool`). The existing deadline gate becomes one shared "rsvps open" gate covering both reasons. `_waitlist_closed` freezes promotion. The frontend gets one shared `areRsvpsClosed(event)` helper that replaces the deadline checks in the guest gates.

**Tech Stack:** Django + Ninja, pytest; React + TanStack Query, Vitest.

**Spec:** `docs/close-rsvps-design.md`

## Global Constraints

- No duplicated logic: deadline and host-close share one gate (backend) and one helper (frontend).
- Frontend copy is lowercase only.
- Ships as two stacked PRs, each under 250 changed lines: PR 1 backend (Tasks 1–2), PR 2 frontend (Tasks 3–4).
- Run scoped tests only, not the full suite.

## Review Focus

- A waitlisted guest on a closed event cancels → no one is promoted (covered in Task 2).
- A host closes, then raises `max_attendees` → still no promotion (Task 2: `_waitlist_closed` covers every caller).
- Reopening with room under the cap promotes the line (Task 1).
- Closing twice keeps the original `rsvps_closed_at` (Task 1).
- Hosts can still add or move guests while closed (Task 2: the host exemption is unchanged).

---

### Task 1: Field, schema, PATCH toggle (backend)

**Files:**
- Modify: `backend/community/models/event.py` (field + `rsvps_closed` property), new migration `0156_event_rsvps_closed_at.py`
- Modify: `backend/community/events/schemas.py` (`EventOut.rsvps_closed: bool = False`, `EventPatchIn.rsvps_closed: bool | None = None`)
- Modify: `backend/community/events/helpers.py` (`event_out` passes `rsvps_closed=event.rsvps_closed`)
- Modify: `backend/community/events/_update.py` (`_resolve_rsvps_closed`, row lock, reopen promotion)
- Test: `backend/tests/test_event_rsvps_closed.py`

**Interfaces:**
- Produces: `Event.rsvps_closed_at: datetime | None`, `Event.rsvps_closed -> bool` (property), and PATCH `rsvps_closed`.

- [ ] Tests: `test_close_sets_timestamp_and_out_flag`, `test_close_twice_keeps_first_timestamp`, `test_reopen_clears_and_promotes_waitlist` (cap 1, attendee switches to can't go while closed so the waitlister stays put; reopen → waitlister becomes attending), and `test_non_host_cannot_close` (403).
- [ ] Run them and confirm they fail.
- [ ] Implement `_resolve_rsvps_closed(event, updates)`: pop `rsvps_closed`. True and currently open → `updates["rsvps_closed_at"] = timezone.now()`. True and already closed → drop the key. False → `None`. Lock the row when `rsvps_closed_at` changes, as `max_attendees` does. Rename `promote_if_capacity_increased` → `promote_if_spots_opened` and also promote when the update reopened RSVPs (`"rsvps_closed_at" in updates and event.rsvps_closed_at is None`).
- [ ] Run the tests and confirm they pass, then commit.

### Task 2: Shared gate + waitlist freeze (backend)

**Files:**
- Modify: `backend/community/rsvps/_deadline.py`: rename `enforce_rsvp_deadline` → `enforce_rsvps_open` (3 call sites in `member.py` and `public_manage.py`). The code is picked by `_closed_code(event)`: `RSVPS_CLOSED_BY_HOST` if `event.rsvps_closed`, else `RSVPS_CLOSED_DEADLINE` if the deadline passed, else open.
- Modify: `backend/community/validation.py` + `validation_codes.json` (via `dump_validation_codes`): `RSVPS_CLOSED_BY_HOST = "event.rsvps_closed_by_host"`
- Modify: `backend/community/rsvps/waitlist.py`: `_waitlist_closed` also returns true when `event.rsvps_closed`.
- Test: `backend/tests/test_event_rsvps_closed.py`

- [ ] Tests: new member RSVP → 400 `event.rsvps_closed_by_host`. Going → can't go is allowed. Going adding a +1 → 400. Public submit → 400. A waitlisted guest can leave. Going → can't go doesn't promote. Raising the cap doesn't promote. A host can still RSVP a guest.
- [ ] Run them and confirm they fail.
- [ ] Implement, then `make generate-codes`.
- [ ] Run the new tests plus the existing deadline and waitlist tests, then commit. **Open PR 1.**

### Task 3: Model + shared closed helper + guest closed state (frontend)

**Files:**
- Regenerate: `frontend/src/api/types.gen.ts` (`make frontend-types`)
- Modify: `frontend/src/api/eventMapper.ts` and `frontend/src/models/event.ts` (`rsvpsClosed: boolean`, `areRsvpsClosed(event) = event.rsvpsClosed || isRsvpDeadlinePassed(event)`)
- Modify: `eventMemberFlags.ts` and `PublicRsvpSection.tsx`, which gate on `areRsvpsClosed`
- Modify: `RsvpDeadline.tsx`: when `event.rsvpsClosed`, the closed note reads `rsvps are closed — {closedDetail}` (it also renders without a deadline)
- Modify: `frontend/src/api/validationCodes.ts`: `RsvpsClosedByHost` → `"rsvps are closed — going guests can only switch to can't go or drop their +1"`
- Test: the existing `eventMemberFlags.test.ts`, `PublicRsvpSection.test.tsx`, `validationCodes.test.ts`

- [ ] Tests: the flags report closed when `rsvpsClosed` is set and no deadline exists. The public section shows the "rsvps are closed" note and no form. The new code's message.
- [ ] Implement, run the scoped vitest, then commit.

### Task 4: Kebab toggle (frontend)

**Files:**
- Modify: `EventDetailKebabMenu.tsx`: a `close rsvps` / `reopen rsvps` `MenuButton`, shown when `canManageRsvps && event.rsvpEnabled && event.status === Active && !event.isPast`. Close opens a `Dialog` titled `close rsvps` with the body `no one new can rsvp or join the waitlist, and cancellations won't open spots. you can reopen anytime.` Reopen calls the mutation directly.
- Modify: `frontend/src/api/eventWrites.ts`: `useUpdateEvent` accepts `rsvpsClosed?: boolean`, passed through as `rsvps_closed`, the same way as `force`.
- Test: `EventDetailKebabMenu.test.tsx` (or the kebab cases in `EventDetailScreen.test.tsx`)

- [ ] Tests: hidden for non-hosts. Shows "close rsvps" when open, and confirming PATCHes `{rsvps_closed: true}`. Shows "reopen rsvps" when closed, and clicking PATCHes `{rsvps_closed: false}`.
- [ ] Implement, run the scoped vitest plus frontend lint and typecheck, then commit. **Open PR 2**, stacked on PR 1.
