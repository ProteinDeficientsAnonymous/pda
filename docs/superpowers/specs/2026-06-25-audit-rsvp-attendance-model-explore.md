# Explore: audit RSVP/attendance model and API completeness (#547) — Findings

**Date:** 2026-06-25
**Issue:** https://github.com/ProteinDeficientsAnonymous/pda/issues/547
**Branch / PR:** `auto-547-explore-rsvp-model` (draft PR linked on the issue)
**Epic:** #545 — events UI improvements + attendance + RSVP cleanup

## The ask

Before implementing the remaining attendance features in epic #545, audit what
is **already built** so the feature issue can be scoped precisely. Specifically:

- Document the current Event / RSVP / attendance model and the Django Ninja API.
- List gaps and missing pieces (check-in confirmation, attendee list, capacity).
- Identify any schema changes that would require migrations.
- Post findings to inform the feature implementation issue.

## What we found

**Headline: the in-app RSVP + attendance + waitlist system is already
substantially built and tested.** This is a far more complete feature than the
issue's framing ("before implementing remaining attendance features") implies.
A member can RSVP (going / maybe / can't go), bring a single +1, get
auto-waitlisted when an event is at capacity and auto-promoted when a spot frees,
and a host can check guests in (attended / no-show) once a check-in window opens.
The frontend mirrors all of this: an RSVP control, an inline tabbed guest roster,
and a host-only attendance/stats panel.

The genuinely unbuilt work is **public (non-member) RSVP**, which is specced and
landing in slices across separate issue branches — only the data-model
groundwork is merged on this branch (see below). A handful of smaller polish
gaps and one acknowledged schema shortcut round out the list.

### Data layer

There is **one** model, `EventRSVP`
(`backend/community/models/event.py:130`), that carries both RSVP *intent* and
*attendance*. It is not a UUID-PK model (implicit `BigAutoField`).

- `status` — `RSVPStatus` (`backend/community/models/choices.py:72`):
  `attending` / `maybe` / `cant_go` / `waitlisted`. No default (must be set).
  `waitlisted` is **system-assigned only** — members cannot self-select it.
- `attendance` — `AttendanceStatus` (`choices.py:79`): `unknown` (default) /
  `attended` / `no_show`. This is the check-in concept, distinct from intent.
- `has_plus_one` — a **boolean**, not a count (one +1 max, design shifted from a
  count in migrations `0035` → `0036`).
- `created_at` / `updated_at` — `created_at` drives FIFO waitlist promotion;
  `updated_at` is reused as a lossy cancellation-time proxy.
- Unique constraint `unique_event_rsvp` on `(event, user)`
  (`event.py:147`). No indexes beyond that constraint + implicit FK indexes.

Capacity lives on `Event.max_attendees` (`event.py:47`, `PositiveIntegerField`,
null = unlimited). Capacity and waitlist are enforced **in app logic, not DB
constraints** — all RSVP writes run under `transaction.atomic()` +
`select_for_update()` on the event row to make the headcount check race-safe.

Count/aggregation logic is **module-level helpers** in
`backend/community/_event_helpers.py` (e.g. `_attending_headcount` `:63`,
`_attending_headcount_db` `:72`, `promote_from_waitlist` `:156`), not model
managers or `Event` methods.

### API layer (Django Ninja)

The RSVP/attendance endpoints live in `backend/community/_event_rsvps.py`. All
use `gated_jwt` auth (logged-in, non-blocked member):

| Method | Path | Function | file:line | Gating |
|---|---|---|---|---|
| POST | `/events/{id}/rsvp/` | `upsert_rsvp` | `_event_rsvps.py:148` | any member who passes read-visibility + `rsvp_enabled`; rate-limited 30/m |
| DELETE | `/events/{id}/rsvp/` | `delete_rsvp` | `_event_rsvps.py:262` | the RSVP owner withdraws their own |
| GET | `/events/{id}/stats/` | `get_event_stats` | `_event_rsvps.py:191` | **host-only** (`_can_edit_event`) |
| POST | `/events/{id}/rsvps/{user_id}/attendance/` | `set_attendance` | `_event_rsvps.py:219` | **host-only**; this is the check-in endpoint; rate-limited 60/m |

Create and update are unified in `upsert_rsvp` (`update_or_create`); a member
changes their RSVP by re-POSTing a new status. The attendee **roster** is not a
dedicated endpoint — it ships as `EventOut.guests` (`list[RSVPGuestOut]`) from
GET `/events/{id}/` (`backend/community/_events.py`), gated to authed users, with
guest phones further gated to host/co-host via `_can_see_phones`
(`_event_helpers.py:28`). Public callers see `attending_count` /
`waitlisted_count` but an empty roster.

Schemas (`backend/community/_event_schemas.py`): `RSVPIn` (`status: str`,
`has_plus_one`), `AttendanceIn` (`attendance: str`, field-validated),
`RSVPGuestOut` (includes `attendance`, `has_plus_one`, gated `phone`),
`EventStatsOut` (full per-status counts + `cancellations`), `CancellationOut`.
Note the input schemas type `status`/`attendance` as **raw `str`** and validate
manually rather than using the `TextChoices` enums — a cleanup candidate given
the repo's "prefer types over strings" rule.

Check-in window: `_check_in_open` (`_event_rsvps.py:40`) opens check-in
`CHECK_IN_OPENS_BEFORE_START = 1 hour` before `start_datetime` (`:37`) and
**never closes**. Only `attending` RSVPs can be marked attended.

### Frontend (React + TanStack Query)

The frontend has a near-complete RSVP/attendance surface:

- **RSVP control** — `frontend/src/screens/events/RsvpSection.tsx`: going /
  maybe / can't-go pills, optional +1 toggle (gated on `allowPlusOnes`), waitlist
  "leave waitlist" view, an at-capacity "event is full" warning, and a
  `{n}/{max} going · {n} waitlisted` summary. Rendered via
  `EventMemberSection.tsx` (authed users only).
- **Guest roster** — `RsvpGuestList.tsx`: inline tabbed roster (going / maybe /
  can't / waitlist / invited) with +1 badges and profile links.
- **Host attendance panel** — `EventAttendancePanel.tsx`: per-status stat chips,
  a check-in list (attended / no-show) that opens 1h before start, and a
  cancellations list with a lead-time filter. Host/co-host only.
- **Hooks** — `frontend/src/api/rsvp.ts` (`useSetRsvp` patches caches directly +
  invalidates stats/comments; `useRemoveRsvp` invalidates) and
  `frontend/src/api/eventStats.ts` (`useEventStats`, `useSetAttendance`).
- **Types** — `frontend/src/models/event.ts` mirrors all server enums
  (`RsvpStatus`, `RsvpServerStatus`, `AttendanceStatus`, `EventGuest`,
  `EventStats`, `Event.myRsvp`), mapped in `frontend/src/api/eventMapper.ts`.

### Test coverage

Backend coverage is strong: `backend/tests/test_rsvp.py` (upsert per status,
disabled/not-found/auth, phone visibility, draft/deleted gating, withdrawal edge
cases), `test_event_capacity.py` (auto-waitlist, +1 capacity, FIFO promotion,
`max_attendees` validation), `test_event_stats.py` (stats perms, attendance
helpers, `set_attendance` window/perm/value cases). Frontend:
`RsvpSection.test.tsx`, `EventAttendancePanel.test.tsx`, plus
`EventMemberSection` / `EventDetailScreen` / `eventMapper` tests.

### Public-RSVP epic state (the genuinely unbuilt work)

Public (non-member) RSVP is **specced and approved** in
`docs/superpowers/specs/2026-05-15-public-rsvp-official-events-design.md` and is
landing in slices. **Only the first slice is merged on this branch** (commit
`5dd6fab`, Issue 491): `User.is_member` flag + `User.objects.members()` manager +
partial-unique email index. Confirmed *not* present here:

- `NonMemberRsvpToken` model (Issue 492, branch `492-nonmember-rsvp-token`).
- `active_members()` manager (Issue 526, branch `auto-526-active-members-manager`).
- The public RSVP endpoints (`POST /api/public/events/{id}/rsvp/`, `/my-rsvps`)
  and the emailed magic-link flow — **do not exist anywhere yet**.

## Relevant code

| Area | Location | Role |
|---|---|---|
| RSVP/attendance model | `backend/community/models/event.py:130` | `EventRSVP`: status, attendance, has_plus_one, unique(event,user) |
| Enums | `backend/community/models/choices.py:72`, `:79` | `RSVPStatus`, `AttendanceStatus` |
| Capacity field | `backend/community/models/event.py:47` | `Event.max_attendees` (null = unlimited) |
| RSVP upsert | `backend/community/_event_rsvps.py:148` | create/update RSVP; capacity + waitlist resolution |
| RSVP delete | `backend/community/_event_rsvps.py:262` | owner withdraws; frees spot, promotes waitlist |
| Stats endpoint | `backend/community/_event_rsvps.py:191` | host-only per-status counts + cancellations |
| Check-in endpoint | `backend/community/_event_rsvps.py:219` | host marks attended/no_show; window opens 1h pre-start |
| Capacity/waitlist logic | `backend/community/_event_helpers.py:63`, `:156` | headcount + FIFO promotion helpers |
| Schemas | `backend/community/_event_schemas.py` | `RSVPIn`, `AttendanceIn`, `RSVPGuestOut`, `EventStatsOut` |
| RSVP control | `frontend/src/screens/events/RsvpSection.tsx` | member RSVP pills, +1, waitlist, summary |
| Guest roster | `frontend/src/screens/events/RsvpGuestList.tsx` | inline tabbed attendee list |
| Attendance panel | `frontend/src/screens/events/EventAttendancePanel.tsx` | host check-in + stats + cancellations |
| RSVP hooks | `frontend/src/api/rsvp.ts`, `frontend/src/api/eventStats.ts` | mutations + stats query |
| FE types | `frontend/src/models/event.ts`, `frontend/src/api/eventMapper.ts` | RSVP/attendance domain types |
| Public-RSVP design | `docs/superpowers/specs/2026-05-15-public-rsvp-official-events-design.md` | approved, partially landed |
| Attendance design | `docs/event-attendance-stats-plan.md` | Issue 299 plan (landed) |

## Gaps and missing pieces

**Schema gaps (require migrations):**

1. **No cancellation/RSVP history table.** `_cancellations`
   (`_event_helpers.py`) infers cancellation lead-time from `EventRSVP.updated_at`,
   which is **lossy** — a member who flip-flops (going → can't → going) is
   mis-tracked. The attendance plan explicitly defers an `EventRSVPHistory`
   table; `test_event_stats.py:143` documents the limitation. *If accurate
   cancellation analytics matter, this needs a new table + migration.*
2. **No check-in timestamp.** `attendance` is an enum only — there is no
   `checked_in_at`, so "when was this guest checked in" is unanswerable. *Adding
   it is a column + migration.*
3. **Plus-ones have no identity.** `has_plus_one` is a boolean on the host's RSVP
   — a +1 has no name, no row, no independent attendance state. *Tracking named
   +1s would be a schema change (a count field, or a separate guest row).*
4. **No `EventRSVP` indexes** beyond `unique(event, user)`. Roster/stats queries
   rely on the unique + implicit FK indexes; if attendance reporting grows, a
   composite index (e.g. `(event, status)`) may help.

**Non-schema gaps (code/UX only):**

5. **`RSVPIn`/`AttendanceIn` use raw `str`** with manual validation instead of
   the `TextChoices` enums — violates the "prefer types over strings" rule.
6. **No "X spots left" countdown** in the UI — only a binary "event is full"
   warning + `{n}/{max} going` summary (`RsvpSection.tsx`).
7. **No RSVP status / attendee count on calendar cards or `MyEventsScreen`
   rows** — RSVP state appears only on the event-detail screen.
8. **Seed data creates no RSVP/attendance rows** —
   `backend/community/management/commands/seed.py` inserts events only (grep for
   `EventRSVP` → 0 hits). There is no way to see a populated roster / attendance
   panel / waitlist from `make seed`. This blocks manual QA of the very features
   the epic is polishing.
9. **No bulk check-in endpoint** — `set_attendance` marks one `user_id` at a
   time; a roster with many guests means many calls.
10. **Public (non-member) RSVP is unbuilt** on this branch (token model,
    endpoints, emails, frontend) — see the epic-state section.

**Testing gaps:** no concurrency test on the `upsert_rsvp` capacity race; no test
that re-marking attendance flips attended→no_show→unknown; no endpoint-level
assertion of `attended_count`/`no_show_count` in the stats response (only the
helper functions are unit-tested).

## Recommendation

**Investigation only — no application code recommended in this issue.** The
in-app RSVP/attendance/waitlist/check-in system is built and well-tested; the
issue's premise that these are largely unbuilt is outdated. The follow-up feature
issue(s) should be scoped to **specific gaps**, not a from-scratch build.

Suggested prioritization for the feature issue(s):

1. **Seed RSVP/attendance data** (gap #8) — small, unblocks QA of everything
   else; do this first.
2. **`EventRSVPHistory` table + `checked_in_at`** (gaps #1, #2) — the only real
   schema work; bundle them since both are migration-backed accuracy fixes. Gate
   on whether cancellation/check-in analytics are actually a product requirement.
3. **Enum-typed RSVP/attendance schemas** (gap #5) — mechanical cleanup aligning
   with repo rules.
4. **UI polish** (gaps #6, #7) — "spots left" + RSVP state on cards/rows.
5. **Public RSVP** (gap #10) — already its own tracked epic slice; not part of
   this audit's follow-up.

Bulk check-in (#9) and an `EventRSVP` composite index (#4) are speculative —
defer until a concrete need (large rosters) appears.

## Open questions

1. **Is accurate cancellation / check-in-time analytics a real product
   requirement?** The lossy `updated_at` inference and missing `checked_in_at`
   only matter if hosts rely on these numbers. If they're cosmetic, the
   `EventRSVPHistory` table (the only substantial schema work here) can be
   dropped from scope.
2. **Should +1s be named/tracked individually**, or is the boolean "+1" headcount
   sufficient for this community? This determines whether a +1 schema change is
   needed at all.
3. **Which gaps belong to #547's follow-up vs. the public-RSVP epic slices
   already in flight** (Issues 492, 526)? Public RSVP should stay in its own
   epic; this audit's follow-up should focus on the in-app gaps above.
4. **Does the check-in window never closing** (opens 1h pre-start, no close) match
   the desired product behavior, or should late check-in be bounded?
