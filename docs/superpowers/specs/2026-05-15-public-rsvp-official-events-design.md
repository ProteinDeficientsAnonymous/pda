# Public RSVP for official PDA events — design spec

**Date:** 2026-05-15
**Status:** ⏸ Blocked on Twilio. The spec is complete and approved. Implementation should not begin until Twilio is set up — the self-serve "manage my rsvp" affordance for non-members depends on SMS magic links, and shipping without it would leave a meaningful UX gap (no self-serve cancel, silent waitlist promotion for non-members). When Twilio lands, resume from this spec into the writing-plans skill.

## Summary

Allow people who are not PDA members to RSVP to **official** PDA events (`event_type=OFFICIAL`) without going through the full join flow. Community events, members-only events, and invite-only events are unaffected — non-members still get the existing "request to join" CTA on those.

Non-members become real `User` rows with a new `is_member=False` flag. They cannot log in. They can manage their RSVP later via an SMS magic link (Phase 2, Twilio-dependent). If they later submit a join request with the same phone, the existing User row is reused and `is_member` is flipped on approval — their RSVP history carries over automatically.

## Goals

- Low-friction RSVP for non-members on official public events (name + phone only).
- Zero change for members; zero change for non-official events.
- Clean promotion path from non-member to member via the existing join flow.
- Reuse the existing RSVP infrastructure (capacity, plus-ones, waitlist, attendance) without duplication.

## Non-goals

- No public RSVP on community events, members-only events, or invite-only events.
- No login or session for non-members.
- No new permission system. Hosts manage non-member attendees through the existing attendee-list UI.
- No automated cleanup of stale non-member rows (separate future task).

## Data model

### `users.User` — new field

- `is_member: BooleanField(default=True, db_index=True)`
  - `True` for accounts created by admins (members screen) or approved via the join flow.
  - `False` for non-members created by a public RSVP submission.

### `users.User` — new manager method

- `User.objects.members() → QuerySet[User]` returns `filter(is_member=True)`.
- Every existing `User.objects.*` call that conceptually means "members" is audited and migrated to this. RSVP-related queries that legitimately need to include non-members (e.g. `EventRSVP` joins) keep using the default manager.

### Derived behavior

- Non-members are created via `set_unusable_password()`. Existing login endpoints already reject those.
- Future magic-login link issuance (Phase 2) must check `is_member=True` *except* for the new non-member-RSVP-management token type, which has its own narrower scope.

### Migration

- Backfill all existing rows to `is_member=True`. No behavior change for existing users.

### No new model

`EventRSVP`, `Event.max_attendees`, plus-ones, waitlist, attendance, and check-in all work unchanged because non-members are real `User` rows.

## API surface

### New public endpoint — `POST /api/public/events/{event_id}/rsvp/`

- No auth.
- Rate limit: `5/h` per IP (matches public join-form pattern).
- Body: `{ name: str (max 100), phone_number: str (E.164), status: RSVPStatus, has_plus_one: bool, honeypot?: str }`.
- Honeypot field — matches `_honeypot_decoy_response` pattern from `_join_requests.py`.
- Behavior:
  1. Validate event is `event_type=OFFICIAL`, `status=ACTIVE`, `rsvp_enabled=True`, not past, not cancelled, `visibility=PUBLIC`. Anything else → 404 with `Code.Event.NOT_FOUND` (don't leak the existence of non-public events).
  2. Look up `User` by phone:
     - **Match `is_member=True`** → 409 with `Code.RSVP.MEMBER_PHONE_MUST_SIGN_IN`. No RSVP created.
     - **Match `is_member=False`** → reuse that User row. Do **not** overwrite `display_name` with a new submission — keep first-submitted to avoid identity churn.
     - **No match** → create User with `is_member=False`, `display_name=name`, `phone_number=phone`, `set_unusable_password()`. Use `get_or_create` inside the transaction so a race produces one row, not two.
  3. Run the same `_apply_rsvp_in_transaction` path the authenticated endpoint uses (capacity, plus-ones, auto-waitlist, waitlist promotion all reused).
  4. Audit log a `public_rsvp_created` event with the user id and event id.
- Response: `{ event: EventOut, rsvp: { status, has_plus_one } }`. `EventOut` here is the same shape returned today to a member viewing this event — since a successful RSVP entitles the non-member to see location/links/etc. for this specific event, the response can safely include the fields that are already gated behind "is RSVP'd to this event". Phase 2 will add a token / SMS-magic-link reference to this response.

### Existing authenticated RSVP endpoint — no change

Members keep using `POST /api/events/{event_id}/rsvp/`.

### Attendee list serialization — small change

Where the attendee list is rendered for hosts/co-hosts, non-members appear in the unified list. No chip, no tag — they look like any other attendee. Phone-number exposure to hosts is **not changed by this spec**; the implementation plan must verify what phone exposure exists today and keep parity (do not silently add phone visibility).

### Join-flow integration — modify `POST /api/join-requests/`

Phone lookup at submission time:

- **Match `is_member=True`** → 409 with `Code.JoinRequest.ALREADY_MEMBER`. The implementation plan reconciles this with the existing `Code.JoinRequest.PHONE_ALREADY_INVITED` code (consolidate, don't shadow).
- **Match `is_member=False`** → attach the new JoinRequest to that existing User. Submission proceeds normally; the existing JoinRequest model may need a User FK if it doesn't have one yet — verify in the implementation plan.
- **No match** → unchanged from today.

On approval:

- If the JoinRequest is linked to an existing non-member User, flip `is_member=True` instead of creating a new User. Display-name / password setup happens at first onboarding login as today. All prior non-member RSVPs are automatically attributed to the now-member account.
- If the linked User has been deleted between submit and approve, fall back to the existing "create new User" path defensively.

### Admin join-request view — small addition

For each JoinRequest, include `attached_user_official_rsvp_count` in the API response (number of `EventRSVP` rows attached to the linked non-member User on `event_type=OFFICIAL` events). Render in the admin UI as "rsvp'd to N official events" with a link list in the detail view.

## Frontend & UX

### Public event detail page (`/events/:id`) — anonymous user

If the event is `event_type=OFFICIAL` **and** `visibility=PUBLIC` **and** `rsvp_enabled=True` **and** active **and** not past:

Replace the existing `LoginOrJoinSection` with an inline RSVP form:

- Header: "rsvp"
- Name input (text, max 100)
- Phone input (reuse the existing phone input from the join form)
- RSVP status: same three buttons members see — "i'm going" / "maybe" / "can't go"
- Plus-one toggle (only if `event.allow_plus_ones`)
- Honeypot field (hidden)
- Submit button: "rsvp"
- Disclaimer below the form: "rsvping doesn't make you a pda member — [request to join]"

For any other event state (community, members-only, invite-only, public-but-no-RSVP, past, cancelled), anonymous users see the existing `LoginOrJoinSection`. Nothing changes for those flows.

### Submit success → confirmation screen

New route `/events/:id/rsvp/confirmation` (or render inline as a card on the same detail page — implementation plan picks; the spec calls for a distinct confirmation surface either way).

- Event title, date/time, location, links — the full public event info the non-member can now see because they RSVP'd.
- Heading: "you're in! 🌱" (for `attending`) or "you're on the waitlist" (for `waitlisted`).
- Phase 2 (Twilio): "we'll text you a link to manage your rsvp". Pre-Twilio: omit this line; the host handles edits/cancellations manually.
- CTA: "want to be part of the community? [request to join]".
- No "my rsvps" link until Phase 2.

### Calendar (`/calendar`)

No change. Entry to the RSVP form is through the event detail page, keeping the surface uniform.

### Member-facing changes

None. Members see no UX change. The attendee list, stats, and check-in views render non-members alongside members without any chip or visual distinction.

### Admin-facing changes

- **`/join-requests`**: each row that links to an existing non-member User shows a small note "rsvp'd to N official events". The detail view shows the list of those events with links.
- **`/admin/members`** (member directory): filter by `User.objects.members()`. Non-members do not appear.
- **`/members`** (member-facing directory): same filter.
- **Audit logs**: no UI change; `public_rsvp_created` is logged.

### Permissions

No new permission key. Hosts/co-hosts already have edit access to the attendee list; non-members are additional rows. The public RSVP endpoint itself is unauthenticated and gated by the `OFFICIAL + PUBLIC + rsvp_enabled` event-state check + rate limiting.

### Copy (follows [ui-copy-tone.md](../../../.claude/rules/ui-copy-tone.md))

- Form header: `rsvp`
- Status buttons: `i'm going` / `maybe` / `can't go`
- Disclaimer: `rsvping doesn't make you a pda member — [request to join]`
- Confirmation header (attending): `you're in! 🌱`
- Confirmation header (waitlisted): `you're on the waitlist`
- Confirmation CTA: `want to be part of the community?`
- Member-phone collision: `looks like you already have an account — sign in to rsvp`
- Already-a-member join error: `looks like you're already a member — [sign in] or get a [magic-login link]`
- Rate-limit error: `you're rsvping too fast — try again in a few minutes`
- Event-state error (post-load): `this event isn't accepting public rsvps anymore — refresh`

## Error handling & edge cases

### Validation errors (422)

- Missing/invalid name.
- Missing/invalid phone (E.164). Reuse existing phone validator.
- Invalid `status` (reuse existing `Code.Event.RSVP_INVALID_STATUS`).

### Event-state errors (404)

To avoid information leak, all of these return `Code.Event.NOT_FOUND`:

- Event not found.
- `event_type != OFFICIAL`.
- `status != ACTIVE`.
- `visibility != PUBLIC`.
- `rsvp_enabled = False`.
- Event is past.
- Event is cancelled.

If the event becomes ineligible after the form loads (host disables RSVP, cancels, etc.) and the user submits anyway, the 404 surfaces in the UI as "this event isn't accepting public rsvps anymore — refresh".

### Honeypot

Honeypot filled → return a successful decoy response. No User or RSVP row created.

### Rate limit (429)

5/h per IP. Surfaces as "you're rsvping too fast — try again in a few minutes".

### Capacity

Reuses `_resolve_rsvp_status` and `_apply_rsvp_in_transaction` verbatim:

- At-cap RSVP from a non-member → auto-waitlisted. Confirmation page shows "you're on the waitlist".
- Plus-one at cap → 400 `Code.Event.NO_PLUS_ONE_SPOTS`. Form shows the error inline.
- Spot frees → existing waitlist promotion path runs.
- **Phase 2 (Twilio)**: non-member promoted off the waitlist is notified via SMS.
- **Phase 1 / pre-Twilio**: silent promotion. The host must notice and contact the non-member manually. This is part of why the feature is blocked on Twilio.

### Concurrency

- Two anonymous users submitting the same phone simultaneously: `User.objects.get_or_create(phone_number=...)` inside the transaction + Postgres unique constraint on `phone_number` (implementation plan must verify the constraint exists) guarantees one row. On `IntegrityError`, re-fetch and reuse.
- Event-level locking already serializes RSVP writes via `select_for_update`.

### Phone collision plus rate limit

Rate limit is checked first (decorator before view body), so a user spamming the form with a real member's phone gets rate-limited before the leak-y `MEMBER_PHONE_MUST_SIGN_IN` message could be enumerated.

### Join-flow edge cases

- Phone matches `is_member=True` → 409 `ALREADY_MEMBER`. Implementation plan must reconcile with existing `PHONE_ALREADY_INVITED` code (probably consolidate).
- Phone matches `is_member=False` → attach to existing User. Submission proceeds.
- Linked User deleted between submit and approve → fall back to creating a new User on approval.

### Data anonymization (out of scope — spec note)

Non-member User rows accumulate over time. They are real PII (name, phone). A future job to delete non-member Users older than N months with no recent RSVPs is **out of scope for this spec**.

### Failure modes explicitly deferred to Phase 2

- Mistyped phone → no way to find the RSVP. Phase 2 SMS magic link makes this self-recoverable. Pre-Phase-2, host handles by hand.
- Non-member wants to add a plus-one or change status after submitting. Phase 2 manage-rsvp page. Pre-Phase-2, host handles.

## Testing

### Backend — pytest

**New file `backend/tests/test_public_rsvp.py`:**

- Happy path: anonymous POST creates non-member User + EventRSVP, returns confirmation payload.
- Returning non-member: second RSVP with same phone reuses the existing non-member User; no duplicate row; multiple RSVPs accumulate against the same user.
- Member-phone collision: phone matches `is_member=True` → 409 `MEMBER_PHONE_MUST_SIGN_IN`, no RSVP created.
- Event-state gating — each returns 404:
  - `event_type=COMMUNITY`
  - `visibility=MEMBERS_ONLY`
  - `visibility=INVITE_ONLY`
  - `rsvp_enabled=False`
  - `status=DRAFT`
  - `status=CANCELLED`
  - past event
  - nonexistent event id
- Validation (422): missing name, missing phone, invalid phone, invalid status.
- Honeypot filled → decoy response, no rows created.
- Rate limit: 6th request in an hour → 429.
- Capacity: at-cap non-member auto-waitlisted; plus-one denied at cap; spot freed promotes a waitlisted non-member.
- Concurrency: two concurrent POSTs with the same phone produce one User and one RSVP.
- Audit log: `public_rsvp_created` written with correct user id and event id.

**`User.objects.members()` manager (new or extend `test_user_manager.py`):**

- Returns only `is_member=True` rows.
- Default manager returns both.
- Migration backfills all existing rows to `is_member=True`.

**Join-flow integration (extend `test_join_requests.py`):**

- Phone matches `is_member=True` → 409 `ALREADY_MEMBER`.
- Phone matches `is_member=False` → JoinRequest created and linked to existing User.
- Approval flow: linked non-member User has `is_member` flipped to `True`; no new User created; onboarding path runs as today.

**Member-only surfaces audit:**

- `/admin/members` excludes non-members.
- `/members` (member directory) excludes non-members.
- Any "list all users" code path used by member features (event invitations, role assignment, recipient lists, etc.) excludes non-members. The implementation plan enumerates these; the test enumerates them in parallel.
- Login endpoints reject non-member User rows (`has_usable_password` already covers — test confirms).

### Frontend — vitest

**Public RSVP form (new component test):**

- Renders on event detail when anonymous + event is `OFFICIAL + PUBLIC + rsvp_enabled`.
- Does **not** render when any of those conditions fail (community event, members-only, RSVPs disabled, past, cancelled).
- Submit posts to the public endpoint with the correct payload shape.
- 409 `MEMBER_PHONE_MUST_SIGN_IN` shows inline error with sign-in link.
- 429 shows rate-limit error.
- Plus-one toggle renders only when `event.allow_plus_ones`.

**Confirmation surface (new screen test):**

- Renders event title, date/time, location, links.
- "you're in!" for `attending`; "you're on the waitlist" for `waitlisted`.
- Renders the join-the-community CTA.

**Join screen (extend existing tests):**

- 409 `ALREADY_MEMBER` shows the "already a member" copy with sign-in link.
- Submitting a phone matching a non-member User → existing success flow (no UI difference visible to the submitter).

**Admin join-request screen (extend existing tests):**

- A JoinRequest linked to a non-member User with prior official RSVPs shows the "rsvp'd to N official events" note.

**A11y:**

- Public RSVP form passes axe.
- Confirmation surface passes axe.

### Verification before claiming done

- `make agent-ci` — ruff, ty, pytest, vitest, eslint, prettier, openapi-codegen check.
- Manual smoke: anonymous → official public event detail → fill form → submit → confirmation. Re-submit same phone, verify dedupe. Open a community event, verify no form. Open a members-only event, verify no form.

## Phase split

**Phase 1 — blocked on Twilio.** Everything in this spec except:

- The SMS magic link from confirmation page.
- The `/my-rsvps` self-serve page for non-members.
- SMS waitlist-promotion notification.

**Phase 2 — when Twilio is live.** Adds the SMS magic link, the scoped manage-rsvp page, and the waitlist-promotion SMS. No data-model change; only new endpoints, a new token type, and one screen.

The current decision is to **not start Phase 1 until Twilio is set up**, because shipping Phase 1 alone leaves non-members with no self-serve way to cancel or be notified of waitlist promotion, and these gaps are large enough that the feature isn't worth shipping in isolation.

## Open implementation questions (for the writing-plans step)

- Does `JoinRequest` already have a User FK, or does it identify by phone only? Determines the "attach to existing User" mechanism.
- Does Postgres have a unique constraint on `User.phone_number`? Required for the get-or-create race protection.
- What's the existing phone visibility model for hosts on the attendee list? Implementation must preserve parity, not silently add exposure.
- Should the confirmation be a separate route (`/events/:id/rsvp/confirmation`) or an inline state on the event detail page? Either works; pick whichever fits the routing patterns better.
- Reconcile `Code.JoinRequest.PHONE_ALREADY_INVITED` vs the new `Code.JoinRequest.ALREADY_MEMBER` — likely consolidate to one code with a clear semantic.
