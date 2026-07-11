# Public RSVP — manage-RSVP backend endpoints design

**Date:** 2026-07-11
**Status:** ✅ Approved for implementation.
**Parent epic:** [#490 — public RSVP for official PDA events](https://github.com/ProteinDeficientsAnonymous/pda/issues/490)
**Parent spec:** [`2026-05-15-public-rsvp-official-events-design.md`](2026-05-15-public-rsvp-official-events-design.md) (sections "API surface" lines 105–130, "Testing" lines 353–362)

## Summary

Stage 4 of the public-RSVP epic: the backend manage-RSVP endpoints a non-member
uses to view, update, and cancel their own RSVPs via the emailed magic link. The
submit endpoint (`POST /api/public/events/{id}/rsvp/`), the `NonMemberRsvpToken`
model, and the token helpers (`resolve_user`, `issue_or_extend`) already exist on
`main`. These three endpoints are the last unbuilt backend piece and are a hard
dependency for the `/my-rsvps` frontend screen (#626).

## Scope

In scope:

- `GET /api/public/my-rsvps/?token=...` — list the non-member's RSVPs.
- `POST /api/public/my-rsvps/{event_id}/?token=...` — update one RSVP.
- `DELETE /api/public/my-rsvps/{event_id}/?token=...` — cancel one RSVP.
- New test file `backend/tests/test_my_rsvps.py`.
- Extract shared helpers out of `_public_rsvp.py` so the new module reuses them
  without a circular import.
- Staging seed: extend the `seed_staging` command with non-member users so the
  full flow is testable on staging (see "Staging seed" below).

Out of scope (follow-ups, each its own issue):

- "rsvp updated" email (Email 2 in the parent spec) — deferred to keep this PR
  small (#705). POST/DELETE still call `issue_or_extend` so the emailed link keeps
  resolving; they just don't send a new email yet.
- "show non-members" toggle on `/admin/members` (#706) — the epic deliberately
  filters non-members out of the member directory; adding an admin way to view
  them is a separate feature. Until it lands, the seed prints the manage links
  directly.
- Frontend `/my-rsvps` screen + anon form (#626, handled in the July bug sweep).
- Wiring `issue_or_extend` into the *submit* endpoint (#630, July bug sweep).

## Structure

- New file `backend/community/_my_rsvps.py` holds the three endpoints on their own
  `Router`, mounted in `community/api.py` alongside the existing public-rsvp router.
- A shared token-auth helper resolves the `?token=...` query param via
  `NonMemberRsvpToken.resolve_user(token)` and raises `Code.Event.NOT_FOUND`
  (404) on `None`. No auth — the token is the auth.
- Helpers currently in `_public_rsvp.py` that both modules need
  (`_load_public_rsvp_event`, `_email_details`, `_email_promoted_non_members`)
  move to a shared location (a new `_public_rsvp_shared.py`) so neither endpoint
  module imports the other.

## Endpoints

### `GET /api/public/my-rsvps/?token=...`

- No auth. Rate limit `30/h` per IP (`client_ip`).
- Resolve token → user, else 404.
- Response: `{ user: { display_name, email, phone_number }, rsvps: [ { event: EventOut, status, has_plus_one } ] }`.
- Filter to OFFICIAL events only (defensive — non-members should never have RSVPs
  on other event types). No attendance field (host-facing).

### `POST /api/public/my-rsvps/{event_id}/?token=...`

- No auth. Rate limit `30/h` per IP.
- Body: `{ status: RSVPStatus, has_plus_one: bool }`.
- Resolve token → user, else 404.
- Re-validate the event is still public-RSVP-eligible via `_load_public_rsvp_event`
  (OFFICIAL + PUBLIC + ACTIVE + rsvp_enabled + not past); ineligible → 404.
- Validate status via `_validate_rsvp_status`.
- Run `_apply_rsvp_in_transaction(event.id, user, status, has_plus_one)`.
- Call `NonMemberRsvpToken.issue_or_extend(user)` to push out the link's expiry
  (no email sent this PR).
- Email any promoted waitlisted non-members via `_email_promoted_non_members`.
- Audit-log `public_rsvp_updated`.
- Response: `PublicRsvpOut` (same shape the submit endpoint returns).

### `DELETE /api/public/my-rsvps/{event_id}/?token=...`

- No auth. Rate limit `30/h` per IP.
- Resolve token → user, else 404.
- Inside a locked transaction, delete that user's RSVP for the event.
- If no RSVP exists for this user+event → 404 (`Code.Event.RSVP_NOT_FOUND`).
- Run `promote_from_waitlist(event)` if the deleted RSVP was ATTENDING.
- Audit-log `public_rsvp_deleted`.
- Response: 204.

## Reuse

Reused verbatim, no duplication: `NonMemberRsvpToken.resolve_user` /
`issue_or_extend`, `_apply_rsvp_in_transaction`, `promote_from_waitlist`,
`_event_out`, `_validate_rsvp_status`, `_load_public_rsvp_event`,
`_email_details`, `_email_promoted_non_members`, `PublicRsvpOut` /
`PublicRsvpStateOut` schemas.

## Staging seed

Extend the existing `seed_staging` management command (idempotent, staging-gated,
`--reset`-aware) so the non-member flow is testable end-to-end on staging.

- Add one new event to `STAGING_EVENTS`: OFFICIAL + PUBLIC + `rsvp_enabled=True`,
  near-future (a few days out), purpose-built for the non-member demo. (The two
  existing official events stay; this adds a clearly-eligible one.)
- Seed ~4 non-member users on a new phone band `+170255503NN` (distinct from the
  `...501` perm and `...502` condition bands so `--reset` can scope-delete them):
  `is_member=False`, `set_unusable_password()`, email `nonmember{NN}@staging.example`,
  display names like `non-member: attending` / `waitlisted` / `multi-event` / `no-rsvp`.
- Give each RSVP'd non-member EventRSVPs on the official events spanning
  attending / maybe / waitlisted, and a valid `NonMemberRsvpToken`
  (`issue_or_extend`).
- The command summary prints each non-member's `/my-rsvps?token=...` URL. Tokens
  in staging deploy logs are acceptable (staging only, low-sensitivity); this is
  the stopgap until the `/admin/members` non-member toggle lands. Reuse
  `FRONTEND_BASE_URL` for the link.
- Extend `_reset()` to remove the `+170255503` band and the new event.
- Pure data/helpers (phone/email builders, the non-member spec list) go in
  `_seed_staging_data.py` next to the existing helpers.

Tests (extend `backend/tests/test_seed_staging.py`): non-members created with
`is_member=False` and unusable passwords; each has a valid token and the expected
RSVPs; `--reset` removes the non-member band and the seeded event; idempotent
re-run makes no duplicates.

## Testing — `backend/tests/test_my_rsvps.py`

- GET with a valid token returns the user's RSVPs; only OFFICIAL events appear.
- GET with expired / revoked / unknown / missing token → 404.
- POST updates an RSVP's status and plus-one; returns the updated payload.
- POST extends the token expiry (same token string still resolves afterward).
- POST on an ineligible event (cancelled / past / non-official) → 404.
- POST with an invalid status → 400.
- DELETE removes the RSVP; a subsequent GET no longer lists it.
- DELETE of an ATTENDING RSVP promotes a waitlisted non-member.
- DELETE when no RSVP exists → 404.
- Rate limit: 31st request in an hour → 429 (per endpoint group).
- Audit logs `public_rsvp_updated` / `public_rsvp_deleted` written.

## Verification before done

- `make agent-ci` (ruff, ty, pytest, vitest, eslint, prettier, openapi-codegen check).
- Regenerate frontend API types (`make frontend-types`) so the new endpoints land
  in the generated client for the #626 frontend work.
