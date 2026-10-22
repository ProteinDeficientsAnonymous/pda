# attendance pause design

## goal

Members are expected to attend 2 official/club events per rolling 12 months. With tentative approval rolling out, we're starting to pause members who haven't. This adds a second kind of pause for that case, with automatic restore once they're back in compliance.

There are two kinds of pause:

| | guidelines violation pause | attendance pause |
|---|---|---|
| why | stewards involved: interpersonal conflict or broken guidelines | under 2 qualifying events in the last 12 months |
| field | `User.is_paused` (exists) | `User.attendance_paused_at` (new) |
| access | none: login and every endpoint blocked | same as a tentative member: log in, RSVP to official/club events only |
| ends | admin unpauses | automatically on reaching 2 qualifying events in the last 12 months, or admin unpauses |

The single-check-in promotion stays the bar for **first entry** (tentative → member). Once someone is a member they have to keep up 2/yr, so a restore needs 2 qualifying events in the last 12 months, not 1.

## data

New fields on `User` (one migration, no backfill; everyone paused today stays a guidelines pause):

- `attendance_paused_at: DateTimeField(null=True)`: set while attendance-paused.
- `restored_at: DateTimeField(null=True)`: last automatic restore. Drives the restored list.
- `attendance_grace_notified_at: DateTimeField(null=True)`: dedupe marker for the grace email (auto-pause only, see below).

"Qualifying event" means the existing rule in `community/_attendance_analytics.py`: attended (host-marked) on an `OFFICIAL` or `CLUB` event, counted over the trailing 12 months (`qualifying_count_12mo`).

## guidelines violation pause

No backend change. The frontend label for `is_paused` becomes "guidelines violation pause". If a user is under both kinds, the guidelines pause wins because `GatedJWTAuth` and login block them outright.

## who counts as a tentative member

The code has two layers, and an attendance-paused member has to land on the tentative side of both:

- **Access:** `community/_tentative_member_access.py` treats any signed-in user with `not user.is_member` as tentative (`is_tentative_member`, `event_viewer_for`, `enforce_tentative_member_write_access`). Setting `is_member=False` covers this layer with no change. Login only blocks `is_paused` and `archived_at`, so they can still sign in.
- **Tentative vs public RSVPer:** several places tell a tentative member apart from a public (token) RSVPer by a `TENTATIVE` join request. An attendance-paused member has an `APPROVED` join request, or none for older accounts, so today these would treat them as a public RSVPer:
  - `ineligible_non_member_rsvps` and `email_removed_non_members` (`community/_event_nonmember_removal.py`)
  - `_tentative_q` / `_gets_member_emails` (`community/_rsvp_status_emails.py`)
  - `check_phone` (`community/_join_request_submit.py`)
  - `User.objects.active_tentative_members()` (`users/models.py`), used by the weekly digest and login reminders

These switch to one shared definition of a signed-in non-member: `is_member=False` and either a `TENTATIVE` join request or `attendance_paused_at` set. Tracked in #1686.

## attendance pause

### shared step: `community/_attendance_pause.py`

Manual and auto pause both go through these two functions.

**`attendance_pause_impact(user) -> PauseImpact`**: read-only, with no side effects and no emails. It looks at upcoming events (`upcoming_events_q` in `users/_archive.py`: status `DRAFT` or `ACTIVE` and not past) where the user holds an RSVP (`ATTENDING`, `MAYBE` or `WAITLISTED`) or is in `co_hosts`, and sorts each into a bucket:

| role | official or club event | any other event |
|---|---|---|
| RSVP'd | `kept_rsvps` | `removed_rsvps` |
| co-host, with other co-hosts | `kept_hosting` | `removed_hosting` |
| only co-host | `kept_hosting` | `drafted_events` |

`co_hosts` is the only source of truth for who hosts an event. `created_by` is an audit field and isn't touched.

**`apply_attendance_pause(user, actor) -> PauseImpact`**: one transaction. `users/_archive.py` (self-delete) already releases a user's upcoming RSVPs and steps them down as co-host; factor its helpers to take an event filter and reuse them here rather than writing a second copy.

1. Compute the impact.
2. For each of `removed_rsvps`: same as `_release_upcoming_rsvps`. Set the RSVP to `CANT_GO` with `cancelled_at`, run `promote_from_waitlist(event)` and `broadcast_capacity_change` if they were attending, and email promoted users after commit.
3. For each of `removed_hosting`: same as `_step_down_as_cohost`. Remove the user from `co_hosts`, set their accepted `EventCoHostInvite` to `REMOVED`, and `broadcast_cohost_change`.
4. Rescind any `PENDING` co-host invites to them on events that aren't official/club.
5. For each of `drafted_events`:
   - remove the user from `co_hosts` and set their accepted invite to `REMOVED`
   - set `status=DRAFT`
   - collect the guests (RSVP'd users other than the paused member), then delete all RSVPs
6. On the user: strip non-member roles (`_strip_non_member_roles`), remove the member role, then set `attendance_paused_at=now`, `is_member=False` and `has_joined_whatsapp=False`.
7. Audit log `user_attendance_paused` with removed role ids, removed RSVP event ids, removed hosting event ids, drafted event ids.
8. After commit, notify the guests of each drafted event: an in-app notification (new `NotificationType.EVENT_UNPUBLISHED`) plus an email that the event was unpublished. A failed send doesn't undo the pause.

The same guards as the guidelines pause apply (`_validate_pause_change` in `users/_management.py`): you can't pause yourself or an admin.

`has_joined_whatsapp=False` because paused members are removed from the WhatsApp community. That way the restored list (below) keeps them until an admin re-adds them.

The ACTIVE → DRAFT move is done directly by this service. It isn't added as a user-facing transition in `_event_transitions.py`.

### manual pause (admin)

1. On the member edit form, the admin turns on "event rqmt pause".
2. The frontend calls `GET /users/{id}/attendance-pause-preview/`. It's gated the same as the user PATCH, and it returns the `PauseImpact` buckets with event title and date.
3. If any of the removed or drafted buckets are non-empty, or the user is hosting or RSVP'd to anything kept, a confirm dialog lists them. For example:
   - "hosting: book club 10/12, will be moved to draft"
   - "rsvp'd: potluck 10/20, will be removed"
   - "rsvp'd: official meetup 10/15, kept"
4. Confirming saves the PATCH with `attendance_paused: true`, and the backend runs `apply_attendance_pause`. If nothing is affected, there's no dialog.

### manual unpause (admin)

PATCH with `attendance_paused: false`:
- clears `attendance_paused_at`
- sets `is_member=True` and saves, then calls `_grant_membership` (the `reject_role_for_non_member` signal rejects a role on a non-member, so the order matters)
- audit log `user_attendance_unpaused`

It's silent: no email, no notification, `restored_at` isn't set, and they don't appear in the restored list. Drafted events stay drafts, and removed RSVPs or host spots aren't put back.

### auto pause (later, separate issue)

The runner finds members with `qualifying_count_12mo < 2` who aren't already paused, and for each one:

- **Grace:** if `attendance_pause_impact` shows a kept RSVP or kept hosting on an official/club event in the next 30 days, skip them for this run. Email them once that they're in a grace period because of that event (name the event(s)) and that they need to attend to stay a member. `attendance_grace_notified_at` makes sure they get the email once per grace period. It's cleared when they're paused or become compliant.
- **Otherwise:** call `apply_attendance_pause(user, actor=None)`.
- **After the run:** send admins with `approve_join_requests` the list of people paused in this run, so they can remove them from WhatsApp.

The attendance report's `is_pause_candidate` (`community/_attendance_analytics.py`) is `qualifying_count_12mo == 0` today. It moves to `< 2` with this work.

## check-in: promote or restore

Today `_apply_attendance_mark` (`community/_event_host_actions.py`) returns early for a non-`ATTENDED` mark or a +1, then returns `_maybe_promote_tentative(user, event, actor) -> bool`, and the caller sends `send_join_approval` when it's true. That call becomes a single entry point:

**`_maybe_promote_non_member(user, event, actor) -> NonMemberOutcome | None`** (`community/_join_request_approval.py`):

1. Shared check: the event is `OFFICIAL` or `CLUB` (`is_official_or_club`). The caller has already filtered to an `ATTENDED` mark for the member, not their +1. (#1609 locks +1s off official/club events, so a +1 mark on a qualifying event shouldn't happen anyway.)
2. Route:
   - if `user.attendance_paused_at` is set → `_restore_attendance_paused(user, actor, event)`. It restores only if `qualifying_count_12mo >= 2`, counting this check-in, and otherwise returns `None`.
   - else, if the user has a `TENTATIVE` join request → today's `_maybe_promote_tentative` body (`_promote_tentative_member`, then stamp the join request `APPROVED`).
3. Return `PROMOTED`, `RESTORED` or `None`.

Checking attendance-paused first means a paused member can never take the one-check-in path.

`_restore_attendance_paused`, in the attendance-mark transaction:
- clears `attendance_paused_at`, sets `restored_at=now` and `is_member=True`, clears `attendance_grace_notified_at`, and saves
- then `_grant_membership` gives back the member role and revokes any scoped RSVP tokens; other roles aren't restored
- audit log `user_attendance_restored`, with actor and event id

The caller acts on the outcome after commit:
- `PROMOTED` → `send_join_approval` (unchanged).
- `RESTORED` →
  - `send_member_restored` email, using the new editable `MemberRestoredEmailTemplate`. It's a singleton in `community/models/content.py` like `MemberPromotionEmailTemplate` and supports `{FIRST_NAME}` and `{WHATSAPP_LINK}`, with a default along the lines of "your membership has been restored".
  - `create_member_restored_notifications(user)` to everyone with `APPROVE_JOIN_REQUESTS` (new `NotificationType.MEMBER_RESTORED`): "{name} was restored to membership".

A failed send doesn't undo the restore.

## join requests list

The list (`community/_join_requests.py`) drops `APPROVED` and `TENTATIVE` rows once the user is past 7 days from `onboarded_at` **and** `has_joined_whatsapp` is true (#1511). Because the pause sets `has_joined_whatsapp=False`, a paused member's old approved row would come back on the approved tab. Exclude users with `attendance_paused_at` or `restored_at` set from those rows; the restored tab covers them.

## restored list

`GET /users/restored/` is gated by `APPROVE_JOIN_REQUESTS`. It returns users with `restored_at` set, newest first, minus anyone who meets the #1511 rule measured from restore: it's been at least 7 days since `restored_at` **and** `has_joined_whatsapp` is true.

Each row has: id, name, `restored_at`, `has_joined_whatsapp`, and the last 2 qualifying events (title and date).

## frontend

- **Member edit form** (`screens/admin/MemberDetailScreen.tsx`): the "pause account" toggle becomes two toggles, "guidelines violation pause" (`is_paused`) and "event rqmt pause". Both are disabled for admins, as today.
  - Turning on event rqmt pause fetches the preview and shows the confirm dialog when anything is affected.
- **Member row and detail badges** (`MemberRow.tsx`, `MemberDetailScreen.tsx`): "paused · guidelines" or "paused · event rqmt".
- **Join requests page** (`JoinRequestsScreen.tsx`): a "restored" tab after rejected. Each row shows name, restored date, the last 2 events, and the existing `JoinRequestWhatsappToggle`.
  - The hint reads: "restored members stay here until it's been 7 days since they were restored and they're marked as joined the whatsapp".
- **Message editors** (`JoinRequestMessageEditors.tsx`): add a restored email editor dialog like `MemberPromotionEmailEditorDialog.tsx`, and the grace email template once auto-pause lands.
- **Notifications:** add `member_restored` and `event_unpublished` to `models/notification.ts`.
- All text is lowercase.

## API changes

- `UserPatchIn`: `attendance_paused: bool | None`.
- `UserOut` / member schemas: `attendance_paused_at`, `restored_at`.
- `GET /users/{id}/attendance-pause-preview/`
- `GET /users/restored/`
- GET/PATCH for the restored email template, the same shape as the member promotion email endpoints.
- New `NotificationType` values need a migration altering the choices (like `notifications/migrations/0018`) and creators in `notifications/service.py`.
- Run `make frontend-types` after.

## testing

- **Impact sorting:** for each row of the bucket table, cover official/club vs other events, RSVP vs co-host vs only co-host, and past events excluded.
- **Apply:**
  - removed RSVPs become `CANT_GO` and run waitlist promotion when they were attending
  - pending co-host invites on other events are rescinded
  - an only-hosted event becomes a draft with no RSVPs and its guests are notified
  - an official/club RSVP or hosting role is untouched
  - user fields, roles and `has_joined_whatsapp` are set
  - audit log written
  - a failed notification doesn't undo the pause
- **Access:** an attendance-paused user can log in and RSVP to official/club events and is blocked elsewhere. A guidelines-paused user is still fully blocked.
- **Tentative definition:** an attendance-paused user without a `TENTATIVE` join request keeps official/club RSVPs when an event loses public-RSVP eligibility, gets member RSVP emails, is a member to `check_phone`, and is in the digest and login reminders.
- **Check-in:**
  - attendance-paused with 1 qualifying event: no restore
  - attendance-paused reaching 2: restored, email sent, approvers notified, `restored_at` set
  - +1 mark: no restore
  - non-qualifying event: no restore
  - tentative applicant: still promoted after 1 check-in
  - attendance-paused user who also has a stale tentative join request: not promoted on 1
- **Manual unpause:** silent restore; not in the restored list.
- **Join requests list:** a paused or restored member's approved row doesn't come back on the approved tab.
- **Restored list:** sort order, the 7-day + WhatsApp clearing rule, the last 2 events, and the permission gate.
- **Frontend:** toggles, preview dialog (shown and skipped), badges, restored tab.

## out of scope

- Restoring removed RSVPs or host roles, or republishing drafted events, on unpause or restore.
- Restoring non-member roles on restore.
- Changing what the guidelines pause does.
