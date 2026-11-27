# Club Reps: Assignment and Monthly Event Reminders

## Why

Next month's club events get shared in the whatsapp on the 15th and the 1st. Reps are expected to have them posted by the last day of the month at the latest, and today someone has to chase reps who haven't. There's also no record of who reps which club: "club rep" is a plain role with no link to a club, so the app can't tell whose job a missing event is.

This links reps to their clubs, makes that link the single source of truth for who is a rep, and emails reps automatically while their club has nothing posted for next month.

## Goals

- Admins assign one or more reps to each club on `/admin/clubs`. Being assigned to at least one club is what makes someone a club rep; there is no separate role to keep in sync.
- Admins can also list and set club reps through the pda MCP server (`list_club_reps`, `set_club_reps`, same `manage_events` gate, preview + confirm token like `set_member_roles`).
- A rep can post club events for their own clubs, and only those. Admins (anyone with `tag_club_event`) can still post for any club.
- Every rep of a club gets reminder emails on the 10th, 7 days before the last day of the month, and on the last day, as long as their club has no qualifying event next month. Reminders stop once one exists.

## Non-goals

- A summary email to admins listing clubs that are behind.
- Reminders by whatsapp, sms or push. Email only.
- Requiring more than one event per club per month.
- An opt-out. Reminders are part of the rep job; stepping down means being unassigned.
- Migrating the existing "club rep" role holders automatically. A role can't be mapped to a club.

## Anti-goals

- Reminding a rep whose club is covered. Any qualifying event counts, whoever created it (a co-rep, an admin, anyone).
- Double-sending a reminder when the cron reruns or two runs overlap.
- Managing reps in two places.

## Approaches considered

1. **`Club.reps` many-to-many to users (chosen).** Admins add/remove reps on the club, changes go to the audit log like other club edits. Least code, fits how clubs work today.
2. **A dedicated `ClubRep` model with assigned_by / assigned_at.** History lives on the row, but the audit log already records who changed what, so it's extra code for little gain.
3. **Keep the "club rep" role and attach clubs to it.** Recreates the two-places problem. Dropped.

For dedup, the reminder job records each send in a small table, matching the existing reminder jobs (stamp before send, under a lock).

## Design

### Data

- `Club.reps = ManyToManyField("users.User", blank=True, related_name="rep_clubs")`.
- `ClubEventReminder(club FK, month DateField (first of the target month), stage CharField, sent_at DateTimeField)`, unique on `(club, month, stage)`. Stage is one of `early`, `week`, `final`.

### Assigning reps (PR 1)

- `ClubIn` / `ClubOut` gain reps: `ClubOut` returns rep ids and display names; `ClubIn` takes `rep_ids`. Same `manage_events` gate as the rest of club editing.
- Rep changes are audited (`club_reps_updated` with added / removed user ids — actor and targets as ids, not names).
- `/admin/clubs` club form gets a member picker for reps (reuse the existing member search/picker used elsewhere, e.g. co-host invites).
- The public `GET /clubs/` (join form, `auth=None`) must not expose rep identities. Either a separate admin/authenticated shape or omit reps when unauthenticated.
- `GET /me/` (`backend/users/_auth.py`, returns `UserOut`) gains `rep_club_ids` so the frontend can scope the club dropdown. If `UserOut` is reused by other endpoints, add it only to the `/me/` response so it doesn't leak elsewhere.
- Update the `list_roles` MCP tool description, which uses "club rep" as its example role.

### Reps post only for their clubs (PR 2)

Server is the real gate:

- `enforce_type_tag_permission` (`backend/community/events/helpers.py`) takes the club id as a new argument (both callers updated). For `EventType.CLUB` it passes if the user has `tag_club_event` **or** the club is in `user.rep_clubs`.
- Create (`crud.py`) passes `payload.club_id`.
- Update (`_update.py`) today only checks when `event_type` is in the patch. Run the check when either `event_type` or `club_id` is in the patch and the resulting event is a club event, against the resulting club (the patched one, else the existing one). *(My call.)* A rep editing an existing event of a club they don't rep, touching neither field, falls under the normal host/co-host edit rules, unchanged.
- Frontend: the club event type option shows for users with `tag_club_event` or any `rep_club_ids`. In the club dropdown, reps without `tag_club_event` see clubs they don't rep grayed out and unselectable.

### Reminder emails (PR 3)

New management command `send_club_event_reminders`, added to `scripts/cron_daily.sh`.

Dates are in `settings.COMMUNITY_TZ`. Target month = next month. For today's month:

| stage | due from | example (dec events) |
|---|---|---|
| `early` | the 10th | nov 10 |
| `week` | last day − 7 | nov 23 |
| `final` | last day | nov 30 |

Each run finds the latest stage whose date is ≤ today and sends only that one (if the cron missed the 10th, `early` goes out on the 11th; if it missed through the 23rd, only `week` goes out — never two reminders in one day).

A club is **covered** if it has an event with `club = that club`, `event_type = club`, `status = active` (not draft, cancelled or deleted), and `start_datetime` within the target month in community time. An event with no date (tbd) doesn't count. Visibility doesn't matter: club events are always public. Covered clubs get nothing.

Nothing fires between the 1st and the 9th: the 1st share covers the current month, whose deadline has already passed, so there's nothing left to remind about.

For each uncovered club with a due, unsent stage: claim the `(club, month, stage)` row under a lock (pattern in `community/planning/reminders.py`), then email each rep who has an email and can receive mail (active, not paused/archived — reuse the existing "who can get email" filter). A club with no reachable reps is logged and skipped; the stage is still stamped so it doesn't retry daily. *(My call: no admin alert. `/admin/clubs` shows each club's reps, which is where a gap gets noticed.)*

Email content, lowercase: the club name, the target month, the deadline (the last day of this month), whether the 15th share has passed (early stage mentions "shared on the 15th"; week/final say "due by the last day" / "due today"), and a link to the create-event page (club prefill only if the form already supports it; don't add one in this PR). One email per rep per club; a rep of two uncovered clubs gets two.

## Rollout

1. Ship in order: assign reps → reps post only for their clubs → reminder emails. Each stage splits into backend and frontend PRs to stay under the 250-line gate (see `docs/club-rep-reminders-plan.md`).
2. After PR 1 deploys, an admin assigns reps on `/admin/clubs`.
3. Right after the rep-scoped club picker deploys (reps already assigned), an admin deletes the "club rep" role. Until then its `tag_club_event` grant still lets holders post for any club. That's no worse than today, so the window is fine. Deleting it before PR 2 would leave reps unable to post at all.

## Left to the builder

- Exact email copy and template, following the existing `notifications/*_email.py` pattern.
- Which member picker component to reuse and its layout on the club form.
- Whether `GET /clubs/` splits into public vs. admin shapes or conditionally includes reps.
- Whether to also send an in-app notification alongside the email.
