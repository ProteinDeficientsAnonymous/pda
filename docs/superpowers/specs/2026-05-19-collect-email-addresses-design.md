# Collect Email Addresses from All Users

**Status:** approved, ready for plan
**Date:** 2026-05-19
**Related issues:** #429 (email magic-link login), #430 (smtp integration), #431 (email blasts ui), #432 (favor email over sms)

## Background

We've been trying to use SMS as our primary outbound channel (welcome links, magic logins, blasts, event reminders). Twilio toll-free verification and ongoing TCPA defensibility have made this painful and expensive. We're pivoting: email becomes the primary outbound channel, phone stays as the login identity (`USERNAME_FIELD`).

This spec covers **only the data-collection half of the pivot** — making sure every user has an email address on file. The actual *uses* of email (sending, magic-link login, blasts) are tracked as follow-up issues and are out of scope here.

## Goals

1. Every active user has a unique, valid email address on their account.
2. New users (via public join requests, admin create, onboarding) provide an email at the earliest possible point.
3. Existing users without an email are forced to provide one at next login via a blocking modal.
4. Phone number remains the login identity (no change to `USERNAME_FIELD`).

## Non-goals (follow-up issues)

- **Email-based magic-link login** — collect now, switch login flow later (#429).
- **SMTP integration / sending welcome + approval + login emails** — provider wiring is its own project (#430).
- **Email blasts UI** — replacement for the planned text-blasts feature (#431).
- **Removing SMS code paths** — SMS scaffolding stays in place, dormant; we just favor email going forward (#432).
- **Email verification / double opt-in** — trust what the user enters for now; revisit when we start sending.

## Design

### Data model changes

**`User.email`** (`backend/users/models.py`)
- Was: `EmailField(blank=True)` — optional, not unique, defaults to `""`.
- Becomes: `EmailField(unique=True, null=True, blank=True)` — optional at DB level (NULL allowed), unique across non-null values.
- Why `null=True`: PostgreSQL allows multiple NULL values in a UNIQUE index. This means existing users with no email don't collide. Once they fill it in, uniqueness is enforced.
- Why still `blank=True`: keeps admin/forms happy when the field is left empty.

**`JoinRequest.email`** (`backend/community/models/join_form.py`)
- New field: `email = models.EmailField()` (required, not unique — same applicant resubmitting shouldn't break).
- Validated at the API layer for well-formedness on submission.

### Migrations

Two migrations to make this safe:

1. **Data migration**: convert every existing `User.email == ""` to `NULL`. Runs before the schema change.
2. **Schema migration**: add `unique=True, null=True` to `User.email`. Add `email` (required) to `JoinRequest`. For existing `JoinRequest` rows (historical), provide a default of empty string OR backfill from approved user (decided at plan time — leaning toward `default=""` since historical join requests are read-only).

### Required-at-collection-point rules

| Surface | Behavior |
|---|---|
| Public join form (`JoinScreen` + `_join_requests.py`) | Email is **required** (form + API). |
| Admin "add member" dialog (`MemberCreateDialog`) | Email is **optional** with strong nudge copy ("if you skip, they'll be asked at first login"). API already accepts optional email — no change there. |
| Bulk create (`BulkCreateDialog`) | **No change** in this PR. Bulk-created users hit the blocking modal at first login. |
| Onboarding (`OnboardingScreen`) | Email becomes **required** (was optional). Drop the `email === ''` escape hatch. |
| Existing logged-in user with no email | **Blocking modal** (`RequireEmail`) renders over the app shell. No close, no skip. |

### Blocking modal: `RequireEmail`

- New component: `frontend/src/components/RequireEmail.tsx`.
- Wired into the authenticated route guard / `AppShell` so that any logged-in user with `currentUser.email == null` sees it instead of the app.
- Single form field (email), submit button.
- Server-side validation: format + uniqueness. Collision returns 400 with friendly copy ("that email is already on another account — try a different one or contact admin"). Surfaced inline.
- After successful submit: invalidate the user query, modal disappears, app renders.

### Backend endpoint

- New: `POST /api/users/me/email` with body `{email: str}`.
- Alternative: extend existing `PATCH /api/users/me/` if it already accepts email. Plan-writer to confirm and pick the simpler option.
- Validation: well-formed email (Django `EmailField`), unique across users (case-insensitive comparison recommended — Django default is case-sensitive, but we should lowercase on save for consistency).

### Frontend API hook

- New: `useSetEmail()` in `frontend/src/api/users.ts`.
- Posts to the endpoint above, invalidates `users/me` query on success.

### Validation rules (both surfaces)

- **Format**: Zod `z.email()` client-side, Django `EmailField` server-side.
- **Uniqueness**: enforced at DB level. Surfaced as a 400 with friendly copy.
- **Case**: lowercase on save (server-side) to avoid `Foo@bar.com` vs `foo@bar.com` collisions.

## Data flow

- **New public join request** → form requires email → stored on `JoinRequest` → vetting team sees it → on approval, copied to `User.email` (unique check runs here; on collision, approval surfaces a friendly error to the admin so they can resolve manually).
- **New admin-created user (single)** → email optional in dialog → user created → first login → blocking modal if email is null.
- **New admin-created user (bulk)** → no email collected → first login → blocking modal.
- **Onboarding flow (for `needs_onboarding=True` users)** → email required alongside display name + password. After completion, no modal.
- **Existing user logs in with no email** → blocking modal.
- **Existing user logs in with email already set** → no change, no modal.

## Components touched

### Backend (~6 files)

1. `backend/users/models.py` — `User.email` field change.
2. `backend/users/migrations/00XX_user_email_null.py` — data migration: `""` → `NULL`.
3. `backend/users/migrations/00XX_user_email_unique.py` — schema migration: add unique + null. (May be one combined migration depending on Django constraints — plan-writer to decide.)
4. `backend/community/models/join_form.py` — add `email` to `JoinRequest`.
5. `backend/community/migrations/00XX_joinrequest_email.py` — schema migration.
6. `backend/community/_join_requests.py` + `_join_form.py` schemas — add required email to public join payload.
7. `backend/users/_management.py` + `schemas.py` — confirm `create_user` accepts optional email (no breaking change expected).
8. `backend/users/api.py` (or `_management.py`) — new `POST /me/email` endpoint (or extend PATCH `/me/`).

### Frontend (~7 files)

1. `frontend/src/screens/public/JoinScreen.tsx` (or wherever the public form lives) — add required email field.
2. `frontend/src/screens/admin/MemberCreateDialog.tsx` — add optional email field + nudge copy.
3. `frontend/src/screens/auth/OnboardingScreen.tsx` — email becomes required.
4. `frontend/src/components/RequireEmail.tsx` — **new** blocking modal.
5. `frontend/src/layout/AppShell.tsx` (or auth route guard) — wire `RequireEmail`.
6. `frontend/src/api/users.ts` — `useSetEmail()` mutation hook.
7. `frontend/src/api/types.gen.ts` — regenerated via `make frontend-types`.

## Edge cases

- **Admin creates user with email that collides with an existing user** → API returns 400 → admin dialog surfaces inline error → admin corrects or leaves blank.
- **User on blocking modal enters a colliding email** → 400 surfaced inline; modal stays open.
- **Existing user has `email=""`** (the common case right now) → data migration converts to NULL → blocking modal fires at next login. This is the intended path.
- **Existing user already has a valid email** → no migration impact, no modal.
- **Join request approval where the email already exists on another user** → approval endpoint returns a friendly error so admin can handle (e.g., the applicant may already have an account; admin investigates).
- **Case-sensitivity / whitespace** → lowercase + trim on save, both server and client side.

## Testing

### Backend

- Migration test: existing `email=""` rows become `NULL` after the data migration.
- Migration test: schema migration succeeds when there are multiple NULL emails (no unique-index violation).
- API: public join request rejects payload without email (400).
- API: public join request rejects malformed email (400).
- API: `POST /me/email` rejects empty / malformed (400).
- API: `POST /me/email` rejects duplicate (case-insensitive) (400).
- API: `POST /me/email` lowercases on save.
- API: onboarding completion rejects payload without email.
- API: approval of a join request copies email to the new user; collision returns 400.

### Frontend

- `RequireEmail` renders when `currentUser.email == null`; doesn't render when set.
- `RequireEmail` submit clears the modal and unblocks the app.
- `RequireEmail` collision error renders inline.
- `OnboardingScreen` rejects empty email on submit.
- Admin `MemberCreateDialog` allows empty email and shows nudge text.
- Public join form rejects empty / malformed email.

## Rollout

1. Merge migrations to staging; verify existing users get `email=NULL`.
2. Log in as a no-email user; confirm `RequireEmail` blocks the app.
3. Submit an email; confirm the modal disappears and `users/me` reflects the new value.
4. Verify a fresh public join request requires email.
5. Verify admin "add member" still works without email.
6. Verify uniqueness collision error renders cleanly on all three surfaces.
7. Promote to production.

## Open questions for plan-writing

- Single migration or two for the `User.email` change? Plan-writer to decide based on Django's constraint behavior when changing `blank` + `null` + `unique` in one step.
- New `POST /me/email` endpoint vs. extending `PATCH /me/`? Pick the simpler option after inspecting existing PATCH endpoint.
- Where exactly is the public join form rendered? Confirm during plan-writing (likely `frontend/src/screens/public/`).
