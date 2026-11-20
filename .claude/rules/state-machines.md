---
paths:
  - "backend/**/*.py"
---

# Status Changes Go Through the State Machines

Two lifecycles are event-driven state machines. Their state fields change **only** inside the machine; every other module fires a named event method.

| Lifecycle | State fields | Transition table | Event methods | Only writer |
|-----------|--------------|------------------|---------------|-------------|
| `User` membership | `membership_status`, `status_before_archive`, `archived_at` (+ `membership_status_changed_*` stamps) | `ALLOWED_MEMBERSHIP_TRANSITIONS` (`users/membership.py`) | `mark_tentative`, `approve_membership`, `promote_on_check_in`, `apply_attendance_pause`, `lift_attendance_pause`, `restore_on_check_in`, `apply_guidelines_pause`, `lift_guidelines_pause`, `archive` | `users/_transitions.py` |
| `JoinRequest` | `status` (+ `status_changed_*` stamps) | `ALLOWED_JOIN_REQUEST_TRANSITIONS` (`community/models/choices.py`) | `mark_tentative`, `approve`, `promote_on_check_in`, `reject`, `unreject`, `close` | `community/models/_join_request_transitions.py` |

## Rules

- **Never write a state field directly**: no `user.membership_status = …`, `join_request.status = …`, `.update(membership_status=…)`, `.update(status=JoinRequestStatus.…)`, `bulk_update(fields=[…state…])` or `setattr(…, "membership_status", …)`.
- **Call the event method, then save the fields it returns**: `user.save(update_fields=user.archive(by=request.auth))`. Methods validate the `(state, event)` edge, stamp who/when, and return `update_fields`.
- **Illegal edges raise `InvalidStateTransition`**. Don't pre-check state to dodge it; let it raise so the rejection is audited (`user_transition_rejected` / `join_request_transition_rejected`) after rollback.
- **Lock before transitioning on a request path**: `select_for_update()` the row and re-read, so a concurrent request can't transition a stale instance.
- **Side effects live outside the machine**: emails, roles, RSVP release, provisioning and success audits run in the orchestration code after the save. The machine stays free of I/O.
- **A new lifecycle edge is a table change**: add it to the `ALLOWED_*_TRANSITIONS` table (plus any side-field logic in the transitions module), then expose or reuse an event method. Update `.claude/docs/user-states.md` too.

## Allowed exceptions

- **Creates** set the initial state: `User.objects.create(membership_status=…, **status_change_stamp(by))`, `JoinRequest.objects.create(status=…)`.
- **Tests and migrations** may write state directly to build fixtures or backfill.

## Enforcement

`backend/tests/test_state_transition_guard.py` statically scans production code and fails on any direct state write outside the transition modules. If it flags your change, route it through an event method; don't add an exemption.

Background: `.claude/docs/adr/0001-event-driven-status-transitions.md`.
