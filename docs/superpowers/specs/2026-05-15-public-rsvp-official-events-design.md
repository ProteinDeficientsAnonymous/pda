# Public RSVP for official PDA events — design spec

**Date:** 2026-05-15 (revised 2026-05-16 to drop SMS dependency in favor of email magic links)
**Status:** ✅ Approved for implementation. Ships end-to-end in one phase.

## Summary

Allow people who are not PDA members to RSVP to **official** PDA events (`event_type=OFFICIAL`) without going through the full join flow. Community events, members-only events, and invite-only events are unaffected — non-members still get the existing "request to join" CTA on those.

Non-members become real `User` rows with a new `is_member=False` flag. They cannot log in. They can manage their RSVP later via an **email magic link** to a scoped `/my-rsvps` page. If they later submit a join request with the same phone (or email), the existing User row is reused and `is_member` is flipped on approval — their RSVP history carries over automatically.

SMS-based flows are **not** part of this spec — the project's SMS infrastructure (Twilio) is on the back burner. Email is the sole post-RSVP communication channel for non-members.

## Goals

- Low-friction RSVP for non-members on official public events (name + email + phone).
- Self-serve manage-rsvp via emailed magic link.
- Zero change for members; zero change for non-official events.
- Clean promotion path from non-member to member via the existing join flow.
- Reuse the existing RSVP infrastructure (capacity, plus-ones, waitlist, attendance) without duplication.

## Non-goals

- No public RSVP on community events, members-only events, or invite-only events.
- No login or session for non-members. Magic-link tokens are scoped only to RSVP management.
- No SMS in any form. SMS is back-burner project-wide; do not add Twilio calls anywhere in this work.
- No new permission system. Hosts manage non-member attendees through the existing attendee-list UI.
- No automated cleanup of stale non-member rows (separate future task).
- No backfill of member email addresses — that's a separate workstream. This spec treats member email as optional today.

## Data model

### `users.User` — new fields

- `is_member: BooleanField(default=True, db_index=True)`
  - `True` for accounts created by admins (members screen) or approved via the join flow.
  - `False` for non-members created by a public RSVP submission.
- `email` — verify what exists today on `User`. If the field already exists, keep it but ensure:
  - Optional (nullable / blank) — existing members are not guaranteed to have one yet.
  - Required at the application layer for non-member creation (the public RSVP endpoint validates this; the database does not).
  - Postgres **partial unique index**: `UNIQUE (email) WHERE email IS NOT NULL AND email != ''`. Allows multiple null/blank rows (existing members), but no two non-members can share a non-blank email.

Phone (`phone_number`) remains the `USERNAME_FIELD`. Login is still by phone. Email is for outbound communication (magic links, etc.), not authentication.

### `users.User` — new manager method

- `User.objects.members() → QuerySet[User]` returns `filter(is_member=True)`.
- Every existing `User.objects.*` call that conceptually means "members" is audited and migrated to this. RSVP-related queries that legitimately need to include non-members (e.g. `EventRSVP` joins) keep using the default manager.

### Derived behavior

- Non-members are created via `set_unusable_password()`. Existing login endpoints already reject those.
- Magic-link issuance for member login (if/when added) must check `is_member=True`. The new non-member-RSVP-management token type has its own narrower scope and a different table / different validation path.

### Migration

- Backfill all existing rows to `is_member=True`. No behavior change for existing users.
- Add the partial unique index on email (no-op for current data since most members likely have null/blank email).

### New model — `NonMemberRsvpToken` (or equivalent)

To support the emailed magic link to `/my-rsvps`:

- `id: UUIDField (primary key)`
- `user: ForeignKey(User, on_delete=CASCADE, related_name="rsvp_tokens")` — must be `is_member=False`; enforced at creation
- `token: CharField (unique, indexed)` — cryptographically random, URL-safe
- `created_at: DateTimeField (auto_now_add)`
- `expires_at: DateTimeField`
- `revoked_at: DateTimeField (nullable)` — set when the user converts to a member, or by an admin tool

Token lifecycle:

- Issued on every successful non-member RSVP, **bundled into the success email**. (Re-issuing on each RSVP keeps the link always-fresh; old tokens stay valid until expiration.)
- Validates on every `/my-rsvps?token=...` page load. Token never logs the user in; it grants scoped read/write access to the linked User's non-member RSVPs only.
- Expiration: 90 days from issuance. (Refresh on use — every successful manage-rsvp action issues a new token in the response email, extending the window.)
- Revocation: set `revoked_at` when `is_member` is flipped to True (the user is a real member now; they should use the member flow).

### No new RSVP model

`EventRSVP`, `Event.max_attendees`, plus-ones, waitlist, attendance, and check-in all work unchanged because non-members are real `User` rows.

## API surface

### New public endpoint — `POST /api/public/events/{event_id}/rsvp/`

- No auth.
- Rate limit: `5/h` per IP (matches public join-form pattern).
- Body: `{ name: str (max 100), email: EmailStr, phone_number: str (E.164), status: RSVPStatus, has_plus_one: bool, honeypot?: str }`.
- Honeypot field — matches `_honeypot_decoy_response` pattern from `_join_requests.py`.
- Behavior:
  1. Validate event is `event_type=OFFICIAL`, `status=ACTIVE`, `rsvp_enabled=True`, not past, not cancelled, `visibility=PUBLIC`. Anything else → 404 with `Code.Event.NOT_FOUND` (don't leak the existence of non-public events).
  2. Look up `User` by phone *and* by email (two queries). Resolve collisions:
     - **Either match is `is_member=True`** → 409 with `Code.RSVP.MEMBER_CONTACT_MUST_SIGN_IN`. No RSVP created. (Treat phone and email symmetrically — if either is a member's, we redirect to login.)
     - **Phone matches an `is_member=False` row, email does not match any row** → reuse the phone-matched row. If that row has no email saved, save the submitted email. If it has a different email saved, **keep the existing email** (don't overwrite — avoids identity churn).
     - **Email matches an `is_member=False` row, phone does not match any row** → reuse the email-matched row. If that row has no phone saved (shouldn't happen — phone is required for non-members), save it.
     - **Both match the same `is_member=False` row** → reuse, no changes.
     - **Phone matches one `is_member=False` row, email matches a *different* `is_member=False` row** → ambiguous. Phone wins (phone is the canonical identifier in this app). Reuse the phone-matched row; do not update its email; log a warning for admin attention.
     - **Neither matches** → create User with `is_member=False`, `display_name=name`, `phone_number=phone`, `email=email`, `set_unusable_password()`. Use `get_or_create` inside the transaction so a race produces one row.
  3. Run the same `_apply_rsvp_in_transaction` path the authenticated endpoint uses (capacity, plus-ones, auto-waitlist, waitlist promotion all reused).
  4. Issue a fresh `NonMemberRsvpToken` for the linked User.
  5. Send an email to the User's email address containing the RSVP confirmation, event details, and the magic link to `/my-rsvps?token=...`.
  6. Audit log a `public_rsvp_created` event with the user id and event id.
- Response: `{ event: EventOut, rsvp: { status, has_plus_one } }`. `EventOut` here is the same shape returned today to a member viewing this event — since a successful RSVP entitles the non-member to see location/links for this specific event, the response can safely include the fields that are already gated behind "is RSVP'd to this event". The response does **not** include the token (the token is delivered only via email — keeps it from leaking into browser history / referer headers).

### New public endpoint — `GET /api/public/my-rsvps/?token=...`

- No auth (token is the auth).
- Rate limit: `30/h` per IP.
- Behavior:
  1. Look up `NonMemberRsvpToken` by token string. If not found, expired, or revoked → 404.
  2. Return `{ user: { display_name, email, phone_number }, rsvps: [ { event: EventOut, status, has_plus_one, attendance } ... ] }` for the linked User's RSVPs on official events. (Don't surface attendance status — it's host-facing.)
- Response includes only official events the user has RSVP'd to. Other event types should never have non-member RSVPs anyway, but filter defensively.

### New public endpoint — `POST /api/public/my-rsvps/{event_id}/?token=...`

- No auth (token is the auth).
- Rate limit: `30/h` per IP.
- Body: `{ status: RSVPStatus, has_plus_one: bool }`.
- Behavior:
  1. Validate token (as above) — resolves to the User.
  2. Run the standard `_apply_rsvp_in_transaction` path with that User.
  3. Issue a fresh token (refresh the 90-day window).
  4. Send a "your rsvp was updated" email with the new magic link.
  5. Audit log a `public_rsvp_updated` event.

### New public endpoint — `DELETE /api/public/my-rsvps/{event_id}/?token=...`

- No auth (token is the auth).
- Rate limit: `30/h` per IP.
- Behavior: validate token, delete the RSVP, run waitlist promotion. Audit log `public_rsvp_deleted`.

### Existing authenticated RSVP endpoint — no change

Members keep using `POST /api/events/{event_id}/rsvp/`.

### Attendee list serialization — small change

Where the attendee list is rendered for hosts/co-hosts, non-members appear in the unified list. No chip, no tag — they look like any other attendee. Phone-number exposure to hosts is **not changed by this spec**; the implementation plan must verify what phone exposure exists today and keep parity (do not silently add phone visibility, do not silently add email visibility).

### Join-flow integration — modify `POST /api/join-requests/`

Phone-and-email lookup at submission time:

- **Match `is_member=True` by phone OR email** → 409 with `Code.JoinRequest.ALREADY_MEMBER`. The implementation plan reconciles this with the existing `Code.JoinRequest.PHONE_ALREADY_INVITED` code (consolidate, don't shadow).
- **Match `is_member=False` by phone OR email** → attach the new JoinRequest to that existing User. If the join form captures email and the existing non-member row has no email saved, save it. Submission proceeds normally.
- **No match** → unchanged from today.

On approval:

- If the JoinRequest is linked to an existing non-member User, flip `is_member=True` instead of creating a new User. Display-name / password setup happens at first onboarding login as today. All prior non-member RSVPs are automatically attributed to the now-member account.
- Revoke all outstanding `NonMemberRsvpToken` rows for this User (they should use the member flow now).
- If the linked User has been deleted between submit and approve, fall back to the existing "create new User" path defensively.

### Admin join-request view — small addition

For each JoinRequest, include `attached_user_official_rsvp_count` in the API response. Render in the admin UI as "rsvp'd to N official events" with a link list in the detail view.

## Frontend & UX

### Public event detail page (`/events/:id`) — anonymous user

If the event is `event_type=OFFICIAL` **and** `visibility=PUBLIC` **and** `rsvp_enabled=True` **and** active **and** not past:

Replace the existing `LoginOrJoinSection` with an inline RSVP form:

- Header: `rsvp`
- Name input (text, max 100)
- Email input (reuse existing email input)
- Phone input (reuse existing phone input from the join form)
- RSVP status: same three buttons members see — `i'm going` / `maybe` / `can't go`
- Plus-one toggle (only if `event.allow_plus_ones`)
- Honeypot field (hidden)
- Submit button: `rsvp`
- Disclaimer below the form: `rsvping doesn't make you a pda member — [request to join]`

For any other event state (community, members-only, invite-only, public-but-no-RSVP, past, cancelled), anonymous users see the existing `LoginOrJoinSection`. Nothing changes for those flows.

### Submit success → confirmation screen

New route `/events/:id/rsvp/confirmation` (or render inline as a card on the same detail page — implementation plan picks; the spec calls for a distinct confirmation surface either way).

- Event title, date/time, location, links — the full public event info the non-member can now see because they RSVP'd.
- Heading: `you're in! 🌱` (for `attending`) or `you're on the waitlist` (for `waitlisted`).
- Confirmation: `we just emailed you a link to manage your rsvp — check your inbox`
- CTA: `want to be part of the community? [request to join]`

### Manage-RSVP screen (`/my-rsvps`)

New public route, takes a `?token=...` query parameter.

- If token is missing / invalid / expired / revoked: empty state — `this link's expired or invalid — rsvp again to get a new one`.
- If valid: shows the user's display name and a list of their non-member RSVPs (one card per event), each with:
  - Event title, date/time, location, links
  - Current status with editable controls (same three buttons as the inline form)
  - Plus-one toggle if `event.allow_plus_ones`
  - Cancel-rsvp button
- After any edit, show a small toast `rsvp updated — check your email for an updated link`.
- A11y: standard form patterns.

### Calendar (`/calendar`)

No change. Entry to the RSVP form is through the event detail page, keeping the surface uniform.

### Member-facing changes

None. Members see no UX change. The attendee list, stats, and check-in views render non-members alongside members without any chip or visual distinction.

### Admin-facing changes

- **`/join-requests`**: each row that links to an existing non-member User shows a small note `rsvp'd to N official events`. The detail view shows the list of those events with links.
- **`/admin/members`** (member directory): filter by `User.objects.members()`. Non-members do not appear.
- **`/members`** (member-facing directory): same filter.
- **Audit logs**: no UI change; `public_rsvp_created`, `public_rsvp_updated`, `public_rsvp_deleted` are logged.

### Permissions

No new permission key. Hosts/co-hosts already have edit access to the attendee list; non-members are additional rows. The public RSVP endpoints are unauthenticated and gated by event-state checks + rate limiting + (for manage endpoints) token validity.

### Copy (follows [ui-copy-tone.md](../../../.claude/rules/ui-copy-tone.md))

- Form header: `rsvp`
- Status buttons: `i'm going` / `maybe` / `can't go`
- Disclaimer: `rsvping doesn't make you a pda member — [request to join]`
- Confirmation header (attending): `you're in! 🌱`
- Confirmation header (waitlisted): `you're on the waitlist`
- Confirmation line: `we just emailed you a link to manage your rsvp — check your inbox`
- Confirmation CTA: `want to be part of the community?`
- Member-contact collision: `looks like you already have an account — sign in to rsvp`
- Already-a-member join error: `looks like you're already a member — [sign in]`
- Rate-limit error: `you're rsvping too fast — try again in a few minutes`
- Event-state error (post-load): `this event isn't accepting public rsvps anymore — refresh`
- Manage-rsvp invalid token: `this link's expired or invalid — rsvp again to get a new one`
- Manage-rsvp update toast: `rsvp updated — check your email for an updated link`

### Email templates

Two new transactional emails. Tone: matches existing PDA emails (lowercase, friendly).

**Email 1 — RSVP confirmation**

- Subject: `you're in for {event title}` (or `you're on the waitlist for {event title}`)
- Body: friendly greeting; event details (date, time, location, links); explanation of the manage-rsvp link; the link itself; "rsvping doesn't make you a pda member — [request to join]"

**Email 2 — RSVP updated**

- Subject: `your rsvp was updated`
- Body: confirms the change; restates the event details; provides a fresh manage-rsvp link

**Email 3 — Waitlist promoted**

- Subject: `you're off the waitlist for {event title}`
- Body: confirms they're now attending; event details; manage-rsvp link

## Error handling & edge cases

### Validation errors (422)

- Missing/invalid name.
- Missing/invalid email.
- Missing/invalid phone (E.164). Reuse existing phone validator.
- Invalid `status` (reuse existing `Code.Event.RSVP_INVALID_STATUS`).

### Event-state errors (404)

To avoid information leak, all return `Code.Event.NOT_FOUND`:

- Event not found.
- `event_type != OFFICIAL`.
- `status != ACTIVE`.
- `visibility != PUBLIC`.
- `rsvp_enabled = False`.
- Event is past.
- Event is cancelled.

If the event becomes ineligible after the form loads and the user submits anyway, the 404 surfaces in the UI as `this event isn't accepting public rsvps anymore — refresh`.

### Honeypot

Honeypot filled → return a successful decoy response. No User, RSVP, or token row created. No email sent.

### Rate limit (429)

5/h per IP on RSVP submission. 30/h per IP on manage-rsvp reads/writes. Surfaces as `you're rsvping too fast — try again in a few minutes`.

### Capacity

Reuses `_resolve_rsvp_status` and `_apply_rsvp_in_transaction` verbatim:

- At-cap RSVP from a non-member → auto-waitlisted. Confirmation page and email say `you're on the waitlist`.
- Plus-one at cap → 400 `Code.Event.NO_PLUS_ONE_SPOTS`. Form shows the error inline.
- Spot frees → existing waitlist promotion path runs. **Non-member promoted off the waitlist is notified via email** (the "waitlist promoted" template above).

### Concurrency

- Two anonymous users submitting the same phone simultaneously: `get_or_create(phone_number=...)` inside the transaction + Postgres unique constraint on `phone_number` (implementation plan verifies the constraint exists) guarantees one row. On `IntegrityError`, re-fetch and reuse.
- Same for email — partial unique index prevents two non-members sharing an email.
- Event-level locking already serializes RSVP writes via `select_for_update`.

### Phone-or-email collision plus rate limit

Rate limit is checked first (decorator before view body), so a user spamming the form with a real member's contact details gets rate-limited before the leak-y `MEMBER_CONTACT_MUST_SIGN_IN` message could be enumerated.

### Join-flow edge cases

- Phone OR email matches `is_member=True` → 409 `ALREADY_MEMBER`. Implementation plan reconciles with existing `PHONE_ALREADY_INVITED` code.
- Phone OR email matches `is_member=False` → attach to existing User. Submission proceeds. Tokens carry over until approval.
- On approval, all outstanding `NonMemberRsvpToken` rows for the User are revoked (they're a member now).
- Linked User deleted between submit and approve → fall back to creating a new User on approval.

### Token lifecycle edge cases

- User RSVPs multiple times → multiple unrevoked tokens exist. All valid until expiration. The "most recent magic link" always works; older ones also work until expired. Acceptable.
- User loses access to their email → can't recover. Mitigation: they can RSVP again with the same phone+email; if the row already exists they get a fresh token to the same address. (Doesn't help if they've also lost the email account — at that point, no recovery short of a host manually editing the row.)
- User's email matches a different non-member by phone (and vice versa) → ambiguous case described above; phone wins, log warning.

### Email deliverability

- Transactional emails should follow the existing email-sending pattern (verify what's in place — likely Django's email backend with a configured provider).
- Failures to send the confirmation email should **not** roll back the RSVP. The RSVP is the user-visible action; the email is a follow-up. On send failure, audit-log `public_rsvp_email_failed` and continue. The user sees the success confirmation page; the manage-rsvp link is in their email (which they may not get). They can RSVP again to get a fresh attempt.

### Data anonymization (out of scope — spec note)

Non-member User rows accumulate over time with real PII (name, phone, email). A future job to delete non-member Users older than N months with no recent RSVPs is **out of scope for this spec**.

## Testing

### Backend — pytest

**New file `backend/tests/test_public_rsvp.py`:**

- Happy path: anonymous POST creates non-member User + EventRSVP + token, sends email, returns confirmation payload.
- Returning non-member by phone: second RSVP with same phone reuses the existing non-member User; no duplicate row; multiple RSVPs accumulate; fresh token issued each time.
- Returning non-member by email: second RSVP with same email but new phone — verify behavior matches the email-only-match branch (reuse email-matched row).
- Phone-and-email match different rows → phone wins; warning logged.
- Member-contact collision: phone matches `is_member=True` → 409 `MEMBER_CONTACT_MUST_SIGN_IN`; same for email match.
- Event-state gating — each returns 404:
  - `event_type=COMMUNITY`
  - `visibility=MEMBERS_ONLY`
  - `visibility=INVITE_ONLY`
  - `rsvp_enabled=False`
  - `status=DRAFT`
  - `status=CANCELLED`
  - past event
  - nonexistent event id
- Validation (422): missing name, missing email, invalid email, missing phone, invalid phone, invalid status.
- Honeypot filled → decoy response, no rows created, no email sent.
- Rate limit: 6th request in an hour → 429.
- Capacity: at-cap non-member auto-waitlisted (email reflects waitlist); plus-one denied at cap; spot freed promotes a waitlisted non-member and sends the promotion email.
- Concurrency: two concurrent POSTs with the same phone produce one User and one RSVP.
- Audit log: `public_rsvp_created` written with correct user id and event id.
- Email send failure does not roll back the RSVP; `public_rsvp_email_failed` is logged.

**New file `backend/tests/test_my_rsvps.py`:**

- GET with valid token → returns the user's RSVPs.
- GET with expired token → 404.
- GET with revoked token → 404.
- GET with unknown token → 404.
- POST updates an RSVP, issues a new token, sends "rsvp updated" email.
- DELETE removes the RSVP, runs waitlist promotion.
- Token-rotation: after POST, response email contains a different token than before.
- Rate limit: 31st request in an hour → 429.

**`User.objects.members()` manager (new or extend `test_user_manager.py`):**

- Returns only `is_member=True` rows.
- Default manager returns both.
- Migration backfills all existing rows to `is_member=True`.
- Partial unique index on `email` permits multiple nulls but rejects duplicate non-null values.

**Join-flow integration (extend `test_join_requests.py`):**

- Phone OR email matches `is_member=True` → 409 `ALREADY_MEMBER`.
- Phone OR email matches `is_member=False` → JoinRequest created and linked to existing User.
- Approval flow: linked non-member User has `is_member` flipped to `True`; outstanding `NonMemberRsvpToken` rows are revoked; no new User created; onboarding path runs as today.

**Member-only surfaces audit:**

- `/admin/members` excludes non-members.
- `/members` (member directory) excludes non-members.
- Any "list all users" code path used by member features (event invitations, role assignment, recipient lists, etc.) excludes non-members. Implementation plan enumerates these; test enumerates them in parallel.
- Login endpoints reject non-member User rows (`has_usable_password` already covers — test confirms).

### Frontend — vitest

**Public RSVP form (new component test):**

- Renders on event detail when anonymous + event is `OFFICIAL + PUBLIC + rsvp_enabled`.
- Does **not** render when any of those conditions fail.
- Submit posts to the public endpoint with the correct payload shape (name, email, phone, status, plus-one).
- 409 `MEMBER_CONTACT_MUST_SIGN_IN` shows inline error with sign-in link.
- 429 shows rate-limit error.
- Plus-one toggle renders only when `event.allow_plus_ones`.

**Confirmation surface (new screen test):**

- Renders event title, date/time, location, links.
- "you're in!" for `attending`; "you're on the waitlist" for `waitlisted`.
- Shows the "we just emailed you a link" line.
- Renders the join-the-community CTA.

**Manage-RSVP screen (new screen test):**

- Renders the user's RSVP list when token is valid.
- Shows the invalid-token empty state when token is missing/expired/revoked.
- Editing a status posts to the manage endpoint and shows the update toast.
- Cancel removes the RSVP from the list.

**Join screen (extend existing tests):**

- 409 `ALREADY_MEMBER` shows the "already a member" copy with sign-in link.
- Submitting a phone or email matching a non-member User → existing success flow (no UI difference visible to the submitter).

**Admin join-request screen (extend existing tests):**

- A JoinRequest linked to a non-member User with prior official RSVPs shows the "rsvp'd to N official events" note.

**A11y:**

- Public RSVP form passes axe.
- Confirmation surface passes axe.
- Manage-RSVP screen passes axe.

### Verification before claiming done

- `make agent-ci` — ruff, ty, pytest, vitest, eslint, prettier, openapi-codegen check.
- Manual smoke: anonymous → official public event detail → fill form → submit → receive email → click manage link → change status → re-receive email → click new link → cancel. Then re-submit same phone, verify dedupe. Open a community event, verify no form. Open a members-only event, verify no form.

## Open implementation questions (for the writing-plans step)

- What does the current `User.email` field look like? Confirm it exists, is optional, and what (if any) uniqueness constraint is in place. Add the partial unique index if missing.
- Does `JoinRequest` already have a User FK, or does it identify by phone only? Determines the "attach to existing User" mechanism.
- Does Postgres have a unique constraint on `User.phone_number`? Required for the get-or-create race protection.
- What's the existing phone visibility model for hosts on the attendee list? Implementation must preserve parity, not silently add phone or email exposure.
- Should the confirmation be a separate route (`/events/:id/rsvp/confirmation`) or an inline state on the event detail page? Either works; pick whichever fits the routing patterns better.
- Reconcile `Code.JoinRequest.PHONE_ALREADY_INVITED` vs the new `Code.JoinRequest.ALREADY_MEMBER` — likely consolidate to one code with a clear semantic.
- What's the existing transactional-email backend / template structure? New templates should fit the existing pattern, not add a new one.
