# User states

Every path a person can take through the app, from visitor to archived. What each type can do once there: [user-capabilities.md](user-capabilities.md). Update both when a transition or gate changes.

## Vocabulary

| Term | Means | Code |
|------|-------|------|
| member | `membership_status` in `MEMBER_STATUSES`: active, guidelines-paused or attendance-paused | `is_member` property, `User.objects.members()` |
| non-member | `none`, `tentative` or `archived` | `User.objects.members()` excludes them |
| `none` | base status for an account with no membership: a public rsvper, or a rejected or withdrawn applicant. Can't sign in | `MembershipStatus.NONE` |
| public rsvper | RSVP'd without an account; status `none`, unusable password | `PublicRsvpToken` |
| limited | signed in without full access: tentative, or attendance-paused (who still hold membership and the member role) | `limited_q()`, `is_limited()` |
| tentative | limited because of a `TENTATIVE` join request | `JoinRequestStatus.TENTATIVE` |

There is no `rejected` membership status. Rejection lives only on the join request.
There is no `is_paused` column either: a guidelines pause is the `guidelines_paused` status (or `status_before_archive` while archived), read through `User.is_guidelines_paused`. The API exposes it only as `membership_status`; admins set it with the PATCH field `guidelines_paused`.

## Lifecycle

```mermaid
stateDiagram-v2
    state "visitor (no account)" as Visitor
    state "public rsvper (none)" as PublicRsvper
    state "applicant (join request pending)" as Applicant
    state "rejected applicant (none, or no account)" as Rejected
    state "tentative (limited)" as Tentative
    state "member" as Member
    state "attendance-paused (limited)" as AttendancePaused
    state "guidelines-paused" as GuidelinesPaused
    state "archived" as Archived

    [*] --> Visitor
    Visitor --> PublicRsvper: rsvps to an official public event
    Visitor --> Applicant: submits join form
    PublicRsvper --> Applicant: submits join form
    Visitor --> Member: admin creates account

    Applicant --> Tentative: vetter marks tentative
    Applicant --> Member: vetter approves
    Applicant --> Rejected: vetter rejects
    Rejected --> Applicant: re-applies, or vetter un-rejects

    Tentative --> Member: vetter approves, or checked in at official/club event
    Tentative --> Archived: admin archives from the members screen, or deletes own account

    Member --> AttendancePaused: admin pauses for attendance
    AttendancePaused --> Member: compliant check-in at official/club event (no admin unpause)

    Member --> GuidelinesPaused: admin pauses
    AttendancePaused --> GuidelinesPaused: admin pauses
    GuidelinesPaused --> AttendancePaused: admin lifts the guidelines pause

    Member --> Archived: admin deletes, or deletes own account
    AttendancePaused --> Archived: admin deletes, or deletes own account
    GuidelinesPaused --> Archived: admin deletes
    Archived --> Applicant: submits join form again (tentative or approval un-archives)

    Member --> [*]: admin hard-deletes (never logged in)
```

### What each transition does

| Transition | Effect | Source |
|------------|--------|--------|
| rsvps to an official public event | creates a `none` user with unusable password; issues or extends a 90-day `/my-rsvps` token (180-day cap) | `community/rsvps/public_submit.py` |
| submits join form | creates `JoinRequest` (pending), linked to an existing non-member by phone; no user row for a new visitor | `community/join_requests/submit.py` |
| vetter marks tentative | creates the user if needed, sets `needs_onboarding`, mints a magic link; status `tentative`. An existing account takes the join form's name. An archived account matched by phone is un-archived: `archived_at` cleared and every role dropped, or back to the pause in `status_before_archive` | `provision_tentative_user` |
| vetter approves | new user → create with member role; public rsvper → promote in place; tentative → promote in place, no new link; archived → clear `archived_at`, re-flag onboarding, back to `active_member`, or the pause in `status_before_archive`. All but tentative mint a magic link. `grant_membership` revokes rsvp tokens | `provision_approved_user` |
| checked in at official/club event | someone else checks a tentative user in → promoted, join request approved via that event. Takes the join form's name. Never while archived or once the request is closed; skipped while guidelines-paused. A failed promotion rolls back alone and is audited (`check_in_promotion_failed`); the check-in stays | `maybe_promote_tentative` |
| vetter rejects | pending join request rejected + email; the user row is untouched. They can't sign in (`auth.account_rejected`) or public-RSVP until they re-apply. A tentative request can't be rejected (400 `tentative_cannot_be_rejected`); an admin archives them from the members screen instead | `join_requests/manage.py` |
| vetter un-rejects | back to pending, unless the phone already has an open request | `join_requests/unreject.py` |
| admin creates account | member with member role + magic link | `users/_management.py` `create_user` |
| admin pauses for attendance | `attendance_paused`, `attendance_paused_at` set to now, `has_joined_whatsapp` and `unpaused_at` cleared, elevated roles stripped (member role kept), non-official/club RSVPs released, co-host spots dropped, solo-hosted events moved to draft, pending co-host invites rescinded. Refused while guidelines-paused; can't pause self or an admin | `apply_attendance_pause` |
| compliant check-in | the only way out of an attendance pause. Someone else checks them in at official/club and their attendance stats are compliant → `active_member`, `restored_at` stamped, `attendance_paused_at` cleared, member role re-granted, restore email, approvers notified. Never while archived. The PATCH refuses `attendance_paused: false` (400 `user.attendance_pause_lifts_on_check_in`), and the MCP `set_attendance_pause` refuses `paused=false` | `check_in_promotion.py` `promote_or_restore_on_check_in` |
| admin pauses (guidelines) | `guidelines_paused`, `has_joined_whatsapp` cleared; reads go through the status or `User.is_guidelines_paused`, which also covers an archived user whose `status_before_archive` is `guidelines_paused`; every upcoming RSVP released (official/club included), co-host spots dropped, solo-hosted events drafted, pending co-host invites rescinded, elevated roles stripped (member role kept), all audited. `attendance_paused_at` and `unpaused_at` cleared. Can't pause self or an admin | `users/_management.py` `update_user`, `User.apply_guidelines_pause`, `release_held_events` |
| admin lifts the guidelines pause | `attendance_paused`, `attendance_paused_at` set to now, member role kept; then `unpaused_at` stamped, `has_joined_whatsapp` cleared, and an unpaused email sent (not while archived). Still limited until a compliant check-in | `User.lift_guidelines_pause`, `users/_unpause.py` `mark_unpaused` |
| deletes / admin deletes | a tentative join request is closed (stamped and audited as `join_request_closed`), then soft archive: `archived` (the archiver lands in `membership_status_changed_by`), the prior status kept in `status_before_archive`, `archived_at` set, calendar token cleared, elevated roles stripped, upcoming RSVPs released, co-host spots dropped | `users/_archive.py` |
| pause changes while archived | `status_before_archive` takes the new pause in place of `membership_status`, with no status stamp. The field side effects still apply: a guidelines pause clears `attendance_paused_at`, `unpaused_at` and `has_joined_whatsapp`; a guidelines lift sets `attendance_paused_at`, stamps `unpaused_at` and clears `has_joined_whatsapp` (no email); an attendance pause sets `attendance_paused_at` and clears `has_joined_whatsapp` and `unpaused_at`. No RSVPs, host spots or roles are touched: archiving already released them | `User.set_membership_status`, `release_held_events` |
| hard-deletes | row deleted; only when `last_login` is null and nothing protected references it | `users/_user_deletion.py` |

`membership_status` is the source of truth; `is_member` is a property, true for `MEMBER_STATUSES` (active, guidelines-paused, attendance-paused). Change it only through `User.set_membership_status(status, by=...)` or `apply_guidelines_pause(by=...)` / `lift_guidelines_pause(by=...)`, which stamp `membership_status_changed_at` and `membership_status_changed_by`: the vetter, admin or checking-in host, or the user on self-delete. While archived they write `status_before_archive` instead and stamp nothing. A new account gets the stamp from `status_change_stamp` (the creating admin or vetter, `None` for a public RSVP). Attendance-paused users hold membership and the member role but get limited access. The two pauses are mutually exclusive: a guidelines pause replaces an attendance pause, an attendance pause is refused while guidelines-paused, and lifting a guidelines pause leaves them attendance-paused until a compliant check-in restores them. No admin path lifts an attendance pause.

## Join requests

A join request has its own status, separate from the person's `membership_status`. `status_changed_at`/`status_changed_by` record the last move.

```mermaid
stateDiagram-v2
    [*] --> pending: submits join form
    pending --> tentative: vetter marks tentative
    tentative --> approved: vetter approves, or checked in at official/club event
    pending --> approved: vetter approves
    pending --> rejected: vetter rejects
    rejected --> pending: vetter un-rejects
    tentative --> closed: admin archives them
```

`tentative → rejected` is refused (400 `tentative_cannot_be_rejected`); a `manage_users` admin archives them from the members screen, which lists tentative people, instead. That closes the request. `approved`, `rejected` and `closed` are terminal through the management API (400 `already_decided`). One open (pending or tentative) request per phone. A rejected or archived applicant re-applies with a new request, and the vetter card shows the earlier rejection and any archive.

## Getting in

Approval, tentative, and admin-create all hand the person a 7-day magic link. After that, the same gates apply to everyone who can sign in, in this order (`config/auth.py` `account_block_code`):

```mermaid
stateDiagram-v2
    state "magic link / password login" as Login
    state "blocked (403)" as Blocked
    state "/onboarding — name + password" as Onboarding
    state "/new-password — password only" as NewPassword
    state "profile + contact privacy step" as Profile
    state "/consent" as Consent
    state "in the app" as Ready

    [*] --> Login
    Login --> Blocked: archived, guidelines-paused, or not in SIGN_IN_STATUSES
    Login --> Onboarding: needs_onboarding, no name or email on file
    Login --> NewPassword: needs_onboarding with name + email, or needs_password_reset
    Login --> Consent: nothing pending but a consent
    Login --> Ready: nothing pending
    Onboarding --> Profile
    NewPassword --> Profile: needs_onboarding
    NewPassword --> Ready: password reset only
    Profile --> Consent: guidelines or SMS consent missing (admin-created)
    Profile --> Ready: consents on file (join-form applicants)
    Consent --> Ready
    Ready --> NewPassword: uses a self-service login link
```

A join-form applicant, tentative or approved, always has a name and email on file (the form requires both), so their magic link goes to `/new-password` and then the profile step; they never see `/onboarding` or `/consent`. Guidelines and SMS consent carry over from the join form, and `complete-onboarding` stamps contact privacy because the profile step shows those toggles. `/onboarding` is for an account missing a name or email (admin-created with no name, or legacy); it collects any missing consents inline. An admin-created account with a name gets `/new-password`, then `/consent` for guidelines and SMS.

A status outside `SIGN_IN_STATUSES` (`none`) is blocked with `auth.account_rejected` when the phone's latest join request was rejected (the magic-login screen offers "request to join again"), and `auth.not_a_member` otherwise. MCP OAuth refuses them the same way, and a self-service login link request gets the neutral "an admin will follow up" reply instead of a link.

Frontend routing for these gates lives in `frontend/src/auth/guards.tsx` (`OnboardingGate`) and `passwordSetupRedirect` / `consentRedirect` in `frontend/src/models/user.ts`.

## What each state can do

See [user-capabilities.md](user-capabilities.md).

## Open questions

- An archived member who tries to sign in is told the account is no longer active, with no prompt to request to join again ([#2244](https://github.com/ProteinDeficientsAnonymous/pda/issues/2244)).
