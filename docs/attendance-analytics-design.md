# Attendance Analytics — Design

Date: 2026-07-21
Status: approved (brainstorm complete)

## Overview

Three features on top of the existing attendance-marking system:

1. **Host attendance report** — mobile-first per-event breakdown (attended /
   no-show / canceled with cancel times) reachable from the event kebab menu
   after an event ends, with configurable CSV download.
2. **Admin attendance analytics** — per-member participation view on the
   existing `/admin/attendance` screen, a 2-in-trailing-12 compliance badge,
   pause candidates, and automated reminder emails at 10 / 11 / 11.5 / 12
   months since last qualifying attendance. Also surfaces attended events on
   each join request for vetting.
3. **Host check-in nudge** — at start time for club/official events, notify
   hosts (email + in-app) to go check people in.

Both features are gated behind feature flags (system designed separately):
`host_attendance_report` and `admin_attendance_analytics`. All flag checks go
through a single `is_feature_enabled(key)` helper (env-var backed stub until
the real flag system lands).

## Existing infrastructure (reused, not rebuilt)

- `EventRSVP.attendance` (`unknown` / `attended` / `no_show`), `checked_in_at`,
  `cancelled_at` (stamped on transition to `cant_go`, cleared on re-RSVP) —
  `backend/community/models/event.py`
- Event kebab menu: `frontend/src/screens/events/EventDetailKebabMenu.tsx`
  (host gating via `canManageEvent`)
- Admin report screen: `frontend/src/screens/admin/AttendanceReportScreen.tsx`
  at `/admin/attendance`, gated `MANAGE_EVENTS`; backend
  `backend/community/_attendance_report.py`
- `User.is_paused` + `UserManager.active_members()`
- Email: synchronous Resend via `backend/notifications/email_sender.py`,
  HTML+txt template pairs in `backend/templates/emails/`, helpers in
  `_email_helpers.py`
- Scheduled work pattern: management command + Railway cron
  (`hard_delete_old_events.py` is the reference)

Net-new patterns: CSV download endpoint, reminder-send log model, feature-flag
helper stub.

## Data layer decision

**Compute on read.** All analytics derive from `EventRSVP` aggregate queries at
request time. No materialized summary table, no RSVP status-history table —
`cancelled_at` already captures the one transition that matters, and data
volume (community scale) makes query cost a non-issue. The only new table is
the reminder-send log (below).

## Qualifying attendance

- **Qualifying** for the in-person requirement: `attendance = attended` on an
  event with `event_type` in (`club`, `official`).
- **Community** events: participation is shown in analytics but never counts
  toward the requirement or the reminder clock.
- Attendance date = the event's `start_datetime` (not `checked_in_at`).

## Feature 1: Host attendance report

### Entry point

`EventDetailKebabMenu` gets a "check-in" group with two items:
- **check-in** — the existing marking screen at `/events/:id/attendance`,
  relabeled from "attendance" to "check-in" (route/screen unchanged).
- **check-in report** (new) — shown when `canManageEvent(event, user)`
  (creator / co-host / `MANAGE_EVENTS`), the event has ended
  (`end_datetime < now`), and `host_attendance_report` flag is on.

### Screen — `/events/:id/report` (mobile-first), titled "check-in report"

- Summary pills: attended / no-show / canceled / unmarked counts.
- Per-person sections beneath: attended (with check-in time), no-shows,
  canceled — each canceled row shows `cancelled_at` formatted lowercase
  ("canceled jul 14, 3:22pm") — and unmarked.
- Non-member RSVPs included, tagged "guest".
- CSV: a column-picker bottom sheet (checkboxes: name, phone, rsvp status,
  attendance, checked-in time, canceled time, plus-one) → download button.

### Backend

- `GET /events/{event_id}/report/` — JSON breakdown for the screen. Gated by
  `_can_edit_event` + event ended + flag.
- `GET /events/{event_id}/report.csv?columns=name,attendance,...` — plain
  `HttpResponse(content_type="text/csv")` with `Content-Disposition:
  attachment` (same response shape as the `.ics` endpoints in `_calendar.py`).
  Same gating. Unknown column names → 422.

## Feature 2: Admin attendance analytics

### Placement

Extend `/admin/attendance` (`AttendanceReportScreen.tsx`) with two tabs:

- **events** — the current cross-event report, plus tap-through to the
  Feature 1 per-event breakdown screen.
- **members** — new per-member analytics table (flag-gated).

### Members tab — per member

- last qualifying attendance date (club/official only)
- qualifying attendance count, trailing 12 months
- **compliance badge**: ≥2 qualifying attendances in trailing 12 months
  (hybrid rule — this is display/triage only; emails use the last-attended
  clock)
- community-event attendance count (informational)
- no-show count, cancel count
- reminders sent (which milestones)
- months-since-last-attended bucket; sortable/filterable by at-risk
- **Pause candidates** (clock anchor > 12 months ago) surface at top. Pause
  button sets `is_paused = True`; visible only with `MANAGE_USERS`. Pausing is
  always a human action — the system never auto-pauses.

### Permissions

- Viewing (both tabs): `MANAGE_EVENTS` (matches existing report).
- Pause action: `MANAGE_USERS`.
- No new permission keys.

### Backend

- `GET /events/attendance-analytics/members/` — per-member aggregates as
  above. Gated `MANAGE_EVENTS` + flag. Members only (`is_member=True`),
  active + paused shown (paused labeled), archived excluded.

### Join request attendance

Each join request in the admin vetting view shows which events the person has
attended so far (all event types, since this is engagement signal, tagged
club / official / community).

- Resolve the person: `JoinRequest.user` FK when set; otherwise a unique
  `phone_number` match against guest `User` rows (covers public RSVPs made
  before/after the join request without linkage).
- Data: list of `attendance = attended` RSVPs → event title, date, type.
- Delivered in the existing join-request list/detail payload (no new
  endpoint), rendered as a compact list on the request card/detail.
- Gated by the `admin_attendance_analytics` flag; no permission change (join
  request viewing keeps its existing gate).

## Reminder emails

### Clock

`anchor = max(last qualifying attended event date, ATTENDANCE_CLOCK_FLOOR,
date_joined)`

- `ATTENDANCE_CLOCK_FLOOR = 2026-08-01`, a settings constant — movable until
  the announcement date is final.
- Attending a qualifying event advances the anchor, which naturally resets the
  milestone sequence.

### Milestones

Months after anchor: **10, 11, 11.5, 12.** Tone escalates but stays welcoming:

- 10mo — "we miss you" + reminder of the 2-events-a-year commitment and that
  community is about consistency.
- 11mo — firmer nudge, upcoming qualifying events linked if easy.
- 11.5mo — short "two weeks left" note.
- 12mo — final notice: membership will be paused by an admin; how to get back
  in touch. (No auto-pause — admin reviews via the members tab.)

Copy follows the lowercase house style. HTML+txt template pairs
(`attendance_reminder_10mo` etc.) in `backend/templates/emails/`, sent via the
existing `EmailSender` / `_email_helpers.py` pattern.

### Idempotency model

```
AttendanceReminder
  user        FK User
  milestone   choice: m10 / m11 / m11_5 / m12
  anchor_date date      # the anchor this reminder was computed against
  sent_at     datetime
  unique (user, milestone, anchor_date)
```

A milestone is due when `today >= anchor + milestone` and no row exists for
`(user, milestone, anchor_date)`. New anchor → old rows are inert history.

### Delivery

Management command `send_attendance_reminders`:

- Run daily via Railway cron (dashboard-configured, like
  `hard_delete_old_events`).
- Recipients: `User.objects.active_members()` only (excludes paused, archived,
  non-members, inactive).
- Skips entirely when the `admin_attendance_analytics` flag is off.
- Idempotent — safe to re-run any number of times per day.
- Sends at most the single latest due milestone per user per run (a user who
  crosses 10mo and 11mo while the cron was broken gets one email, not two).

## Feature 3: Host check-in nudge

- **Trigger**: event `start_datetime` reached, `event_type` in (`club`,
  `official`), `status = active`, `rsvp_enabled`. Fires once per event.
- **Recipients**: `created_by` + `co_hosts` — the same set `_can_edit_event`
  authorizes (`_event_host_actions.py`).
- **Channels**: in-app notification via the existing `_notify_users` /
  `notify_*` pattern (`backend/notifications/service.py`), plus an email
  using the standard `EmailSender` + template-pair pattern
  (`attendance_checkin_reminder`). Both link straight to
  `/events/:id/attendance` (the check-in screen).
- **Copy**: short, lowercase, e.g. "< event title > just started — head to
  check-in to check people in."
- **Idempotency**: reuses the `AttendanceReminder`-style log shape — a
  `HostCheckinNudge(event, sent_at)` row (unique on `event`), or simply a
  `checkin_nudge_sent_at` field on `Event`; either works since it's a
  one-shot per event, not a recurring milestone. Picked: a
  `checkin_nudge_sent_at` nullable field on `Event` — simpler than a new
  table for a single boolean-ish fact.
- **Delivery**: same daily-cron shape doesn't fit (needs to fire near start
  time, not once a day) — runs as a short-interval management command
  (`send_checkin_nudges`, e.g. every 15 min via Railway cron), selecting
  events where `start_datetime <= now` and `checkin_nudge_sent_at is null`
  and `start_datetime >= now - 1h` (skip nudging for long-past events, e.g.
  after downtime).
- Gated by `host_attendance_report` flag (same flag as the rest of the host
  check-in flow).

## Feature flag integration points

| Flag | Gates |
|---|---|
| `host_attendance_report` | kebab item, `/events/:id/report` route, report + CSV endpoints, `send_checkin_nudges` command |
| `admin_attendance_analytics` | members tab, analytics endpoint, join-request attended-events list, `send_attendance_reminders` command |

All checks call `is_feature_enabled(key)`; the stub reads env vars
(`FEATURE_HOST_ATTENDANCE_REPORT=1`) until the real flag system replaces its
internals. Frontend gets flag state via an existing bootstrap/config response
(exact wiring decided when the flag system design lands).

## Testing

- **Phase 1**: report endpoint gating (non-host 403, event-not-ended 403/409,
  flag off 404), guest tagging, `cancelled_at` in payload, CSV column
  selection + unknown-column 422, CSV content assertions.
- **Phase 2**: compliance math (2-in-trailing-12 boundary cases), qualifying
  vs community separation, pause action perm gating, paused/archived
  filtering, join-request attended-events (FK link, phone fallback, no match →
  empty list).
- **Phase 3**: anchor math (floor, date_joined, attendance advances it),
  milestone due/idempotency (re-run sends nothing), single-latest-milestone
  rule, active_members recipient filtering, flag-off short-circuit.
- **Phase 4**: checkin-nudge event selection (event_type filter, start-time
  window, already-sent skip, non-club/official excluded), recipient set
  matches `created_by` + `co_hosts`, flag-off short-circuit.

## Phasing (one PR each)

1. **Host report** — screen, kebab item, report JSON + CSV endpoints, flag
   stub helper.
2. **Admin analytics** — members tab, analytics endpoint, pause action,
   compliance badge, join-request attended-events list.
3. **Reminders** — `AttendanceReminder` model + migration, templates,
   management command, Railway cron doc note.
4. **Host check-in nudge** — `checkin_nudge_sent_at` field + migration,
   notification + email templates, `send_checkin_nudges` command, Railway
   cron doc note (shorter interval than the daily reminder cron).

## Out of scope

- Feature flag system itself (separate design in progress).
- Auto-pausing members.
- RSVP status-change history/audit table.
- Async email queueing.
