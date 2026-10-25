# Host digest email

Issue: #1603. Status: approved design, not yet built.

## Goal

Once a day, email each event host a short summary of what changed on their events since their last digest: who joined, who dropped, how many new comments, and whether the event is full.

## Example

```
south mountain nj hike — sat oct 18, 10am
12/12 going · full · 3 waitlisted
going: sam, alex
waitlisted: jo
can't go: chris
3 new comments
view event → https://…/events/south-mountain-nj-hike-2
```

Empty lines are omitted. Comment text is never included, only the count; event location is never included (#1598).

## Which events

An event is eligible when all of these hold:

- `status = ACTIVE`, not deleted, `rsvp_enabled = True`, any `event_type` (official, club, community).
- TBD (`datetime_tbd = True` or `start_datetime` is null), or `coalesce(end_datetime, start_datetime + DEFAULT_EVENT_DURATION) >= run_started_at - 24h`. That covers upcoming, in-progress and just-ended events, so post-event comments still show up. A TBD event with a stale `start_datetime` still counts as TBD.

An eligible event appears in a host's email only if it had RSVP activity or new comments in that host's window.

## Who gets it

- Recipients are each eligible event's `co_hosts` (the source of truth for hosts; the creator is added on create).
- Only hosts who are in `User.objects.active_members()`, have a non-blank email, and have `host_digest_opt_out = False`.
- One email per host, covering all of their events with activity. No activity on any event → no email.

## The window

- Each host's window is `(host_digest_last_sent_at, run_started_at]`. When `host_digest_last_sent_at` is null, the window starts at `run_started_at - 24h`.
- `run_started_at` is captured once at the start of the run, so activity during the run lands in the next window.
- After a successful send, or when the host had nothing to report, set `host_digest_last_sent_at = run_started_at`.
- On a send failure, leave it unchanged so the next run retries the same window (at-least-once).

## What counts as activity

**RSVPs:** RSVPs on the event whose `status_changed_at` falls in the window, excluding RSVPs by any co-host of that event. Each person is listed under their current status:

| status | label |
|---|---|
| ATTENDING | going |
| MAYBE | maybe |
| WAITLISTED | waitlisted |
| CANT_GO | can't go |
| REMOVED | removed |

**Comments:** `EventComment` on the event with `created_at` in the window, `deleted_at` null, author not a co-host of that event. Replies count too.

**Capacity line:** always shown for an included event.

- With `max_attendees`: `{headcount}/{max} going`, plus `· full` when `headcount >= max`, plus `· {n} waitlisted` when n > 0.
- Without a cap: `{headcount} going`, plus `· {n} waitlisted` when n > 0.
- Headcount uses the existing helpers in `community/_rsvp_counts.py` (attending plus plus-ones).

Names use the same display-name helper as the host's guest list, with the host as viewer.

## New fields

- `EventRSVP.status_changed_at`: `DateTimeField(null=True, db_index=True)`.
  - Set in `EventRSVP.save()` when the row is created or its status differs from the value loaded from the DB. When `save(update_fields=...)` includes `status`, add `status_changed_at` too.
  - `_event_nonmember_removal.py` bulk `.update(status=REMOVED)` also sets `status_changed_at=now`. Any other bulk status write found during build gets the same treatment.
  - No backfill: existing rows stay null, so the first digests only cover changes after deploy.
- `User.host_digest_last_sent_at`: `DateTimeField(null=True, blank=True)`.
- `User.host_digest_opt_out`: `BooleanField(default=False)`. Exposed like `weekly_digest_opt_out`: model, user schemas, the PATCH passthrough in `users/_auth.py`, and a toggle in `frontend/src/screens/settings/EmailPreferences.tsx` ("updates about events i host"). Run `make frontend-types`.

## Sending

- New management command `send_host_digests`, added to `scripts/cron_daily.sh` with `timeout 300` like the others (~7–8am ET).
- `--dry-run` logs what each host would get and sends nothing and writes nothing.
- Sent on `EmailStream.BULK`, like the weekly digest.
- Subject: `what's new on your events`.
- Templates `backend/templates/emails/host_digest.{html,txt}`, all lowercase, ending with the "update your preferences" settings link and `_no_reply_footer`. Times use `format_eastern_datetime`.

## Code layout

- `backend/community/_host_digest.py`: pure collection logic. Given `run_started_at`, return per-host digest data. No sending.
- `backend/notifications/_host_digest_email.py`: render and send one host's email. Keeps `_email_helpers.py` from growing.
- `backend/community/management/commands/send_host_digests.py`: loop over hosts, send, update `host_digest_last_sent_at`.

## Tests

- `status_changed_at`: set on create and on status change; not touched by payment, check-in, plus-one or waitlist-order saves; set by the bulk non-member removal.
- Collection:
  - joins and drop-outs grouped by current status;
  - a host's own RSVPs and comments are excluded;
  - deleted comments are excluded and replies are included;
  - window boundaries, including the null-watermark fallback;
  - event eligibility: inactive, RSVP disabled, ended over 24h ago, ended under 24h ago, TBD;
  - capacity line and full marker, with and without a cap;
  - no activity means no digest;
  - recipient filters: no email, opted out, paused, archived.
- Command:
  - one email per host across several events;
  - the watermark advances after a send and not after a failed send;
  - a second run straight after sends nothing;
  - `--dry-run` sends and writes nothing.
- Frontend: the `EmailPreferences` toggle reads and patches `hostDigestOptOut`.

## Out of scope

- Naming people whose RSVP was deleted. The capacity line still reflects the drop.
- A "just filled up" callout. The full marker covers it.
- Comment text in the email.
- Sending more than once a day, per-user timezones, an in-app activity view.

## Merge conflicts to watch

- **PR #1480** also adds a users migration, an `EmailPreferences.tsx` toggle, a `cron_daily.sh` line.
- **PR #1604** touches `users/models.py` and the weekly digest command.
- **PR #1507** touches `_event_rsvps.py` and `_email_helpers.py`.

Renumber migrations when rebasing.
