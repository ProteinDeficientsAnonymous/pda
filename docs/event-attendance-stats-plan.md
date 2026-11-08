# Host-Only Event Attendance: Stats, Check-In, and Cancellation Lead Time

Issue: [#299](https://github.com/leahpeker/pda/issues/299)

## Context

From the bug bash: hosts want a real picture of "who actually came" after the event, not just "who RSVP'd." That breaks into three related asks, all host-only (creator + co-hosts + `MANAGE_EVENTS` admins — no public toggle, no member-facing view):

1. **Stats block** — going / maybe / can't-go / no-response counts at a glance, plus attended / no-show after the event.
2. **Check-in flow** — after the event, hosts can mark each "going" RSVP as attended or no-show.
3. **Cancellation lead time** — for each person who RSVP'd `CANT_GO` (or removed their RSVP), show how many days before `start_datetime` they did so.

Existing primitives to reuse:

- `_can_edit_event` / `_can_see_invited` (`backend/community/events/helpers.py:121`) — the "host + co-host + admin" gate.
- `_attending_headcount`, `_waitlisted_count` — template for new aggregations.
- `RsvpGuestList` (`frontend/src/screens/events/RsvpGuestList.tsx`) — tab-with-count layout we can mirror, but for a host-only panel.

Not in place today:

- No `attended` / `no_show` concept on `EventRSVP` (`backend/community/models/event.py:119`).
- No RSVP history table — so cancellation-lead-time has to be inferred from `EventRSVP.updated_at` for current `CANT_GO` rows (lossy for people who flip-flopped, but good enough for the common case).

## Scope

- Add `attendance` field on `EventRSVP` (enum: `UNKNOWN` default / `ATTENDED` / `NO_SHOW`).
- Add host-only API: `POST /events/{id}/rsvps/{user_id}/attendance` with `{attendance: "attended" | "no_show" | "unknown"}`.
- Add host-only `EventStatsOut` schema and endpoint `GET /events/{id}/stats` returning:
  - `going_count`, `maybe_count`, `cant_go_count`, `no_response_count`, `waitlisted_count`
  - `attended_count`, `no_show_count`, `not_marked_count` (only meaningful post-event)
  - `cancellations`: list of `{user_id, name, cancelled_at, days_before_event}` for RSVPs currently `CANT_GO` (sorted by `cancelled_at`)
- Add host-only UI section on event detail: "attendance" card, collapsible, shown to hosts/co-hosts/admins. Contains:
  - Stats row (always) — going/maybe/cant/no-response/waitlisted
  - After event: per-going-guest row with `[attended] [no-show]` buttons
  - After event: cancellation list with lead times
- Out of scope: public (non-host) view of any of this; RSVP history audit trail; bulk check-in tools (QR, kiosk); notifications about attendance marks; retroactive edits far after the event (no time limit for now — trust hosts).

## Changes

### Backend

**`backend/community/models/choices.py`**

- Add `AttendanceStatus` TextChoices: `UNKNOWN = "unknown"`, `ATTENDED = "attended"`, `NO_SHOW = "no_show"`.

**`backend/community/models/event.py`**

- `EventRSVP`: add `attendance = models.CharField(max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.UNKNOWN)` after `has_plus_one` (L125).

**`backend/community/migrations/0047_eventrsvp_attendance.py`** (new) — AddField with default.

**`backend/community/events/helpers.py`**

- Add helpers mirroring `_attending_headcount`:
  - `_maybe_count`, `_cant_go_count` (simple prefetch filters).
  - `_no_response_count(event)` — `invited_users` set minus users with any RSVP row. Uses already-prefetched data.
  - `_attended_count`, `_no_show_count` — count RSVPs with matching `attendance`.
  - `_cancellations(event)` — for RSVPs with `status=CANT_GO`, return `[(user, updated_at, (start - updated_at).days)]` sorted by `updated_at` desc. Skip if `event.start_datetime` is null.

**`backend/community/events/schemas.py`**

- New `EventStatsOut` Schema with the fields listed in Scope. Include a `CancellationOut` sub-schema `{user_id, name, cancelled_at, days_before_event}`.
- New `AttendanceIn` Schema: `{attendance: str}` (validated against enum).

**`backend/community/rsvps/member.py`** (current home for RSVP endpoints)

- `GET /events/{id}/stats` — gated by `_can_edit_event`. Returns `EventStatsOut`. Reuses the event's prefetch pattern so we don't re-query.
- `POST /events/{id}/rsvps/{user_id}/attendance` — gated by `_can_edit_event`. Validates the target RSVP exists and is `ATTENDING`. Sets attendance. 404 if no RSVP; 403 if not host.

**Router wiring** — add the two routes to whatever `Router()` `community/rsvps/member.py` exports (match existing pattern).

**Tests** — extend `backend/tests/test_events.py` (or add `test_event_stats.py`):

- `_no_response_count`: 3 invited, 1 responds → 2.
- `_no_response_count`: user both invited and with an RSVP → counted once, as a responder.
- Cancellation lead time: user currently `CANT_GO` with `updated_at` 3 days before `start_datetime` → `days_before_event == 3`.
- Cancellation list excludes users currently `ATTENDING` even if they were `CANT_GO` at some point (acknowledging the lossy inference).
- `GET /stats` forbidden for non-hosts (403); ok for host, co-host, admin.
- `POST attendance` rejects when target isn't `ATTENDING`, rejects for non-hosts, updates correctly for hosts.
- Attendance defaults to `UNKNOWN` for existing rows after migration.

### Frontend

**`frontend/src/models/event.ts`**

- New `AttendanceStatus` const `{ Unknown, Attended, NoShow }`.
- New `EventStats` type matching `EventStatsOut` (include `Cancellation` sub-type).
- Add `attendance: AttendanceStatus` to `EventGuest` (so the check-in UI knows current marks without a separate fetch).

**`frontend/src/api/eventStats.ts`** (new)

- `useEventStats(eventId)` — `useQuery` against `GET /events/{id}/stats`. Host-only; component decides when to call.
- `useSetAttendance()` — `useMutation` against `POST /events/{id}/rsvps/{user_id}/attendance`. On success, invalidate both `['event', id]` (for updated guest `attendance`) and `['event-stats', id]`.

**`frontend/src/screens/events/EventAttendancePanel.tsx`** (new)

- Rendered inside `EventMemberSection` only when `isCoHost || canManageEvents`.
- Collapsible section (use an existing `CollapsibleCard` / `<details>` pattern if one exists — grep first).
- Top row: stats chips — `going · maybe · cant · no response · waitlisted`.
- If `event.isPast`:
  - Check-in list: each "going" guest with two buttons: `attended` / `no-show`. Pressed state = current value. Third state "not marked" if `UNKNOWN`.
  - Cancellation list: `<name> cancelled 3 days before` rows, newest first.
- If not past: show stats only, with a note like "check-in opens after the event".

**`frontend/src/screens/events/EventMemberSection.tsx`**

- Add `const isHost = isCoHost || canManageEvents;` (already have `isCoHost` L28 and `canManageEvents` L29; just name + pass).
- Render `<EventAttendancePanel event={event} />` inside the hosts-only area (near `EventAdminActions`).

**Tests** — `frontend/src/screens/events/EventAttendancePanel.test.tsx`:

- Non-host doesn't see the panel at all (so test via `EventMemberSection`).
- Pre-event: stats render; check-in buttons do not.
- Post-event: check-in buttons render; clicking `attended` calls `setAttendance` with `attended`.
- Cancellation list renders lead time strings.

## Critical files

- `backend/community/models/event.py` — new `attendance` field on `EventRSVP`.
- `backend/community/models/choices.py` — new `AttendanceStatus`.
- `backend/community/events/helpers.py` — new aggregations + cancellation query.
- `backend/community/events/schemas.py` — `EventStatsOut`, `CancellationOut`, `AttendanceIn`.
- `backend/community/rsvps/member.py` — two new endpoints.
- `frontend/src/models/event.ts` — types.
- `frontend/src/api/eventStats.ts` (new) — query + mutation hooks.
- `frontend/src/screens/events/EventAttendancePanel.tsx` (new).
- `frontend/src/screens/events/EventMemberSection.tsx` — mount point.

## Reused utilities / patterns

- `_can_edit_event` / `_can_see_invited` in `community/events/helpers.py` — host gate.
- `_attending_headcount` — aggregation style to mirror.
- `EventAdminActions.tsx:24-27` — `isCreator || isCoHost || canManage` derivation already exists; copy for attendance panel gating.
- `CollapsibleCard` (used in the event form) — for the attendance panel if available; otherwise a simple `<details>`.

## Open questions for later (not blocking)

- Should we add a full `EventRSVPHistory` table for accurate cancellation tracking? Recommend waiting for the feature to prove useful first — `updated_at` inference is fine for v1.
- Should hosts get a notification/reminder to do check-in after the event? Not for v1.
- Any retention/privacy concern around keeping per-person attendance marks? Not addressed here; same sensitivity as existing RSVP data.

## Verification

1. `make agent-ci` passes.
2. `make frontend-types` regenerates OpenAPI types.
3. Manual check (`make dev`):
   - Create event, invite 3 members, one RSVPs `going`, one `cant_go`, one doesn't respond. As host, open event detail → attendance panel shows `1 going · 0 maybe · 1 can't · 1 no response`.
   - Cancellation list shows the `CANT_GO` member with a sensible lead-time string.
   - Fast-forward (or set `start_datetime` in the past) — check-in buttons appear next to the `going` guest. Click `attended` — count updates.
   - Log in as a non-host member — attendance panel is not rendered.

## Effort estimate

~500 lines across 10 files. Biggest pieces: the `EventAttendancePanel` component (~150 lines), the stats endpoint + tests (~150 lines). Everything else is plumbing.
