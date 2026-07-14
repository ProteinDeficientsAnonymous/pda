# Design question — PR #771 (issue #498): "attended vs rsvp'd" breakdown on join-request rows

## Context
The current PR shows one line per admin join-request row: `rsvp'd to N official events`
(driven by the backend field `attached_user_official_rsvp_count`, which counts a linked
non-member user's RSVPs on official-type events).

Review feedback (leahpeker, JoinRequestsScreen.tsx:290) asks for a richer breakdown:

> this should show attended, not just RSVPd
> so like "Attended n official events", "Attended n club events",
> "RSVPd for upcoming official event", "RSVPd for upcoming club event"

This needs (a) a backend change — the API currently returns only one aggregate count, so
new per-bucket counts must be added and `make frontend-types` regenerated — and (b) a
decision on what "attended" means, because the schema supports two different readings and
they produce different numbers and different queries/tests. I don't want to guess wrong.

Also note the wording implies **club** events as a separate bucket from **official**.
There is a third event type, **community** (`EventType.COMMUNITY`) — see option D.

## The core ambiguity: what does "attended" count?
`EventRSVP` has BOTH a time dimension (event start/end vs now) AND an explicit
`attendance` field (`AttendanceStatus`: unknown / attended / no_show) that a host marks
after check-in closes. The codebase already has `_is_attended` =
`status==ATTENDING AND attendance==ATTENDED` (backend/community/_rsvp_counts.py).

## Options

**A — time-based (recommended).** "attended" = RSVP'd `attending` to an event now in the
PAST; "rsvp'd for upcoming" = RSVP'd `attending` to a FUTURE event. Matches your wording
("upcoming") and yields useful non-zero data for prospective members even when hosts never
marked attendance. Buckets: attended-official, attended-club, upcoming-official,
upcoming-club (show a line only when its count > 0).
Recommended because these are prospective non-members — hosts have almost certainly not
hand-marked `attendance` for them, so option B would read ~0 everywhere.

**B — attendance-field-based.** "attended" = RSVPs with `attendance == ATTENDED` (exact,
matches existing `_is_attended`); "rsvp'd" = the rest / upcoming. Precise and semantically
literal, but likely near-zero for non-members since attendance is a manual host action.

**C — keep as-is / minimal.** Reject the richer breakdown; keep the single
`rsvp'd to N official events` line the PR already ships (issue #498's literal scope was
only this note). Reply on the thread that attended/club splits are follow-up scope.

**D — same as A/B but also include a `community` bucket** (official + club + community),
in case "club" was shorthand for "all non-official." Say so if you want all three types.

## My recommendation
Option **A**, official + club buckets only, statuses limited to `ATTENDING`, one line per
non-zero bucket, all lowercase (e.g. `attended 2 official events`, `rsvp'd for 1 upcoming
club event`). This requires a backend addition (new per-bucket counts on the join-request
list response) plus regenerated types, so it grows the PR beyond frontend-only — confirm
that's acceptable, or pick C to keep the PR as-is and defer.
