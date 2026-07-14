# Explore: auth method options (phone / email / passkey) for login (#789) — Findings

**Date:** 2026-07-13
**Issue:** https://github.com/ProteinDeficientsAnonymous/pda/issues/789 (part of #249)
**Branch / PR:** `auto-789-auth-method-options` (draft PR linked below)

## The ask

A spike to evaluate login-method options and recommend an approach **before**
any implementation. Today login is phone-number-based (`USERNAME_FIELD =
"phone_number"`). Issue #249 wants to enable passkey and/or email login, with
phone kept as the ideal primary method. This spike documents the current auth
flow, WebAuthn/passkey feasibility in the Django Ninja + React stack,
email-login trade-offs, security considerations (recovery, credential binding,
admin-only account creation), and a recommended phased rollout with follow-up
sub-issues. **No auth code is changed in this spike.**

## What we found

### Current auth is password + JWT, keyed on phone — plus a working magic-link channel

Login is **password-based, keyed on `phone_number`**, issuing JWTs via
`ninja_jwt`:

- `POST /api/auth/login/` (`backend/users/_auth.py:64-91`) calls Django's
  `authenticate(username=phone_number, password=...)`
  (`_auth.py:69`), rejects archived/paused users, then issues
  `RefreshToken.for_user(user)` (`_auth.py:87`) and sets the refresh token as an
  **httpOnly cookie** (`set_refresh_cookie`, `_auth.py:89`;
  `backend/users/_refresh_cookie.py`). The access token is returned in JSON and
  sent as `Authorization: Bearer`.
- No custom `AUTHENTICATION_BACKENDS` is set (`backend/config/settings.py` has
  `AUTH_USER_MODEL = "users.User"` at `:71` but no backends override), so
  `authenticate()` uses Django's default `ModelBackend`, which matches on
  `USERNAME_FIELD` (phone) + password.
- JWT config: `NINJA_JWT` at `settings.py:75` — 15-min access, 7-day refresh,
  Bearer header.

A **second, passwordless login channel already exists** via magic links:

- Self-service: `POST /api/community/request-login-link/`
  (`backend/community/_login_link.py:60-145`) — unauthenticated, rate-limited
  5/m, always returns 200 (anti-enumeration). The user enters a **phone
  number**; if a matching account has an email on file, a magic link is emailed
  (`_try_email_delivery`, `_login_link.py:148-186`); otherwise it flags
  `login_link_requested` and notifies admins.
- Admin-issued: `POST /api/auth/users/{user_id}/magic-link/`
  (`backend/users/_magic_links.py:24-123`, gated on `MANAGE_USERS`).
- Redemption: `GET /api/auth/magic-login/{token}/`
  (`backend/users/_magic_login.py:124-142`) — single-use, row-locked against
  replay (`_consume_magic_token`, `_magic_login.py:74-121`), 7-day expiry,
  cross-user click blocked. On success it issues a JWT the **same way** as the
  password path (`RefreshToken.for_user`, `_magic_login.py:132`).

The token issuance layer is therefore **already credential-agnostic**: any new
method just needs to reach `RefreshToken.for_user(user)` + `set_refresh_cookie`.

### A per-request auth gate must be honored by any new method

`GatedJWTAuth` (`backend/config/auth.py`) is the shared chokepoint for protected
endpoints. It re-checks account state on every request that a still-valid token
could otherwise outlive: it hard-blocks archived (`auth.py:59`) and paused
(`auth.py:61`) users, and for pending users (needs onboarding / password reset /
guidelines consent) it blocks everything except an allowlist
(`_PENDING_ALLOWLIST`, `auth.py:32`: `/me/`, `/complete-onboarding/`,
`/change-password/`, `/accept-consents/`). **Any new auth method must produce a
user that passes this gate**, and if a WebAuthn *registration* ceremony must run
during onboarding (before the pending state clears), its endpoint must be added
to `_PENDING_ALLOWLIST`.

### The email field is nullable and only partially unique — the central email-login gotcha

`email = models.EmailField(null=True, blank=True)`
(`backend/users/models.py:84`). Uniqueness is **not** field-level `unique=True`;
it is a partial constraint `unique_non_blank_email` (`models.py:120-128`,
migration `0028_user_is_member_email_partial_unique.py`) that only applies when
email is non-null and non-empty. This is deliberate — bulk phone-only members
share a null email (`backend/users/_management.py` bulk-create sets
`set_unusable_password()` + `needs_onboarding=True` with no email). So:

- Not every user has an email; email login cannot be universal without a data
  backfill and making email required/unique.
- An email→user lookup must tolerate many rows with null/blank email.
- Email *is* required at onboarding today (`complete_onboarding`,
  `_auth.py:285-322`), so users who have completed onboarding will generally
  have one — but legacy/never-onboarded accounts will not.

### No WebAuthn/passkey code or dependency exists anywhere

Confirmed by grep across `backend/` and `frontend/src/`: no `webauthn`, `fido2`,
`py_webauthn`, `django-otp`, `@simplewebauthn/*`, `navigator.credentials`, or
`publicKey` usage. (The only `otp` hits are log-redaction keyword lists in
`config/logging_config.py`; the only "credentials" hits are unrelated admin
welcome-credential dialogs.) Passkeys are fully greenfield on both sides.

### Deployment is single-origin with a stable HTTPS domain — favorable for WebAuthn

In production, one container runs nginx (serving the built SPA and
reverse-proxying `/api/`) in front of Django, so **frontend and backend are
same-origin** — no cross-origin ceremony concerns. Production domain is
`proteindeficientsanonymous.com` and staging is `staging-pda.up.railway.app`
(`README.md:40-41`). Prod enforces HTTPS/HSTS (`settings.py` security block).
`FRONTEND_BASE_URL` (`settings.py:223`) already carries the public origin used to
build magic-link URLs and is the natural source for a WebAuthn RP ID.

**RP-ID gotcha:** staging and prod are different apex domains, so a passkey
registered on one won't work on the other — RP ID must be env-configured, not
hardcoded. `*.up.railway.app` is on the Public Suffix List, so the staging RP ID
must be the full host `staging-pda.up.railway.app` (an RP ID of `up.railway.app`
is rejected). `localhost` works for dev without HTTPS.

### Frontend has clean seams for a new method

The auth store (`frontend/src/auth/store.ts`) keeps the access token in memory
only and exposes `login`, `magicLogin`, `restoreSession`, `completeOnboarding`,
`logout`, `forceLogout` actions. A store↔axios bridge (`setAuthBridge`,
`store.ts:168-176`) deliberately breaks a circular import — **new client-touching
auth code must not import the store into `client.ts`**. Every successful login
runs `queryClient.clear()` (`store.ts:69`) to avoid leaking the previous user's
cache — a new login action must replicate this.

The login screen (`frontend/src/screens/auth/LoginScreen.tsx`) is a two-step
phone-first flow (`Step = 'phone' | 'password' | 'pending'`, `LoginScreen.tsx:22`);
the identifier step and the `Step` union are the natural seam for adding an
email path or a method toggle. A passkey button would sit alongside the existing
"request a login link" button in `PasswordStep` (`LoginScreen.tsx:223`). Public
auth routes are wired in `frontend/src/router/routes.tsx` outside `AppShell`.

### Test coverage is substantial and constrains new work

`backend/tests/` covers login (incl. **email-format username explicitly
rejected**, `test_auth.py:94`), rate-limiting, refresh cookie behavior, the
`GatedJWTAuth` state gate (`test_auth_gate.py`), magic-login single-use/replay/
cross-user (`test_magic_login.py`), self-service login-link delivery matrix
(`test_request_login_link.py`), and onboarding email rules
(`test_onboarding.py`). An autouse conftest fixture auto-stamps guidelines
consent + `is_member` on `create_user` (`conftest.py:60`) — new auth paths that
create users interact with the guidelines-consent gate.

## Relevant code

| Area | Location | Role |
|---|---|---|
| User model | `backend/users/models.py:75-128` | phone `USERNAME_FIELD`, UUID PK, nullable partial-unique email |
| Email uniqueness | `backend/users/models.py:120-128` | `unique_non_blank_email` partial constraint |
| Password login | `backend/users/_auth.py:64-91` | `authenticate()` on phone + JWT issuance |
| Onboarding / password set | `backend/users/_auth.py:285-322` | sets password, requires name + email |
| JWT issuance pattern | `backend/users/_auth.py:87-89`, `_magic_login.py:132-134` | `RefreshToken.for_user` + `set_refresh_cookie` (credential-agnostic) |
| Magic-link redemption | `backend/users/_magic_login.py:74-142` | single-use, row-locked, cross-user guarded |
| Admin magic-link gen | `backend/users/_magic_links.py:24-123` | `MANAGE_USERS`-gated link generation |
| Self-service login link | `backend/community/_login_link.py:60-186` | phone → emailed magic link / admin fallback |
| Token model | `backend/users/models.py:160-195` | `MagicLoginToken` — template for a new token/challenge table |
| Per-request gate | `backend/config/auth.py:32-95` | `GatedJWTAuth` + `_PENDING_ALLOWLIST` |
| Router merge | `backend/users/api.py:23-28` | where a new `_webauthn` / `_email_login` router registers |
| JWT / origin config | `backend/config/settings.py:71,75,223` | `AUTH_USER_MODEL`, `NINJA_JWT`, `FRONTEND_BASE_URL` |
| Email sender | `backend/notifications/email_sender.py`, `_email_helpers.py:82-105` | Resend-backed `send_magic_login_email` |
| Auth store | `frontend/src/auth/store.ts:65-176` | login actions + axios bridge + `queryClient.clear()` |
| Login screen | `frontend/src/screens/auth/LoginScreen.tsx:22,223` | phone-first `Step` machine; passkey/email seam |
| API client | `frontend/src/api/client.ts`, `frontend/src/api/auth.ts:95` | `authClient` (no interceptor) vs `apiClient`; `login()` |
| Deps (backend) | `pyproject.toml`, `uv.lock` | Django 6.0, ninja 1.6, ninja-jwt 5.4; **no webauthn** |
| Deps (frontend) | `frontend/package.json` | React 19, react-router 7; **no @simplewebauthn** |
| Deploy / domains | `README.md:40-41`, `nginx.conf.template` | single-origin; prod `proteindeficientsanonymous.com` |

## Options

The issue frames three candidate methods. They are not mutually exclusive; the
real question is sequencing and how much each costs.

### Option A — Email magic-link login (extend the existing channel)

Let users initiate login with an **email address** (not just phone), reusing the
existing `MagicLoginToken` + `send_magic_login_email` + `/magic-login/{token}/`
machinery. The only genuinely new backend work is an email→user lookup path and
a new initiation entry point; the frontend already has `MagicLoginScreen` and
`RequestLoginLinkDialog` to build on.

- **Pros:** ~90% of the plumbing already exists (token model, email delivery,
  JWT issuance, redemption screen, anti-enumeration pattern). No new
  dependency. Passwordless. Good recovery story.
- **Cons:** Email is nullable/partial-unique — lookup must handle absent/blank
  emails, and it only works for users who have an email on file. Email
  deliverability and inbox latency are UX risks. Doesn't satisfy the "passkey"
  half of #249.
- **Cost:** Small–medium (mostly a lookup + a thin initiation endpoint + a UI
  toggle).

### Option B — Email + password login (add email as an alternate identifier)

Add a second login path (or a custom `AUTHENTICATION_BACKENDS` entry) that
resolves an email to a user and checks the password.

- **Pros:** Familiar UX; reuses the existing password machinery.
- **Cons:** Introduces a second password-based identifier surface (more attack
  surface, more rate-limit/lockout care). Still limited by nullable/partial-
  unique email. `USERNAME_FIELD` stays phone, so this needs a custom backend or
  a parallel endpoint — a deliberate divergence from the tested "phone-only
  username" invariant (`test_auth.py:94` explicitly rejects email usernames
  today). Lower incremental value than A or C given a magic-link channel
  already exists.
- **Cost:** Medium.

### Option C — Passkey / WebAuthn (greenfield, highest value long-term)

Add FIDO2 passkeys via `py_webauthn` (backend) + `@simplewebauthn/browser`
(frontend). Needs: a new credential model (`credential_id` unique, `public_key`,
`sign_count`, per-user FK), a short-lived challenge store, and begin/finish
endpoint pairs for both registration and authentication, all funneling into the
existing `RefreshToken.for_user` + `set_refresh_cookie` issuance and honoring
`GatedJWTAuth`.

- **Pros:** Strongest security (phishing-resistant, no shared secret), best
  modern UX, directly satisfies the passkey half of #249. Single-origin HTTPS
  deploy is ideal for it.
- **Cons:** Most new surface area (new deps both sides, two model tables,
  four+ endpoints, browser ceremony). RP-ID must be env-configured (staging vs
  prod apex domains differ; `*.up.railway.app` PSL caveat). **Requires a
  non-passkey recovery fallback** for lost authenticators — which the existing
  magic-link flow already provides. Registration ceremony must slot into the
  admin-created → magic-link-onboard model: the admin can't register a passkey
  on the user's behalf, so registration happens during/after the user's
  first magic-link login (needs an allowlisted onboarding-time endpoint).
- **Cost:** Large (justifies its own multi-PR sub-epic).

## Recommendation

**Phased rollout, in this order:**

1. **Phase 1 — Email magic-link login (Option A).** Highest value-to-effort:
   it reuses the existing token/email/redemption stack, adds no dependency, and
   immediately gives members a phone-optional way in. Scope: an email→user
   lookup that respects the partial-unique/nullable-email reality, a thin
   initiation endpoint (or an email branch of `request-login-link`), a
   `LoginScreen` identifier toggle, and tests mirroring the existing
   login-link suite. Keep phone as the primary/default identifier.

2. **Phase 2 — Passkey / WebAuthn (Option C)**, as its **own sub-epic** (it is
   too large for a single ≤400-line PR — split into: dependency + credential/
   challenge models & migration; registration begin/finish endpoints wired into
   onboarding + `_PENDING_ALLOWLIST`; authentication begin/finish endpoints;
   frontend `@simplewebauthn/browser` ceremony + login-screen button; settings
   screen to manage/remove passkeys; RP-ID env configuration for
   dev/staging/prod). Passkeys should be **additive** — offered alongside, never
   replacing, phone login, and always backed by the magic-link recovery
   fallback.

3. **Deprioritize Option B (email + password).** With a magic-link channel
   already present and passkeys planned, a second password identifier adds
   attack surface for little incremental benefit. Revisit only if user research
   shows members specifically want email+password.

**Suggested follow-up sub-issues to file** (all under #249):

- `feat: email-initiated magic-link login` (Phase 1).
- `feat(webauthn): credential + challenge models and dependency` (Phase 2a).
- `feat(webauthn): passkey registration during onboarding` (Phase 2b).
- `feat(webauthn): passkey authentication endpoints + login-screen button`
  (Phase 2c).
- `feat(webauthn): manage/remove passkeys in settings` (Phase 2d).
- `chore(webauthn): env-configured RP ID for dev/staging/prod` (Phase 2e).

Cross-cutting requirements for **every** new method (record in each sub-issue):
issue JWTs via `RefreshToken.for_user` + `set_refresh_cookie`; pass
`GatedJWTAuth` (archived/paused/pending); apply `@rate_limit` (auth endpoints use
`5/m` by IP) and `audit_log(...)`; register new routers in
`backend/users/api.py:23-28`; and put new models in a dedicated
`users/_*_models.py` re-exported module rather than appending to `models.py`
(already 328 lines against a 500-line hard max).

## Open questions

1. **Product intent for email login — magic-link vs password?** Issue #249 says
   "email login" without specifying. This spec recommends the magic-link form
   (Option A) as it reuses existing infrastructure; if stakeholders specifically
   want email + password (Option B), Phase 1 scope changes. *(Design decision —
   deferred to the user; not resolved in this spike.)*

2. **Should email login require making `email` unique/required?** Today email is
   nullable and only partially unique. Making it a first-class login identifier
   may argue for a backfill campaign + a `unique=True` migration, which is a
   data-migration project of its own. Left open — Phase 1 can ship for
   email-having users without forcing this.

3. **Passkey rollout gating — all members, or a permission/opt-in?** Given
   admin-only account creation, do passkeys become available to every member
   during onboarding, or gated behind a flag/permission for a controlled
   rollout? Not resolved here.

4. **Env-var name & source for the WebAuthn RP ID.** Recommendation is to derive
   it from `FRONTEND_BASE_URL` (or a dedicated `WEBAUTHN_RP_ID` env var) per
   environment, but the exact configuration surface (and Railway variable
   wiring for staging vs prod) is a Phase 2 implementation decision.

5. **Recovery UX when a user has *only* a passkey and loses it.** The magic-link
   fallback covers this, but only if the user has an email on file. Members
   with neither a usable password, a passkey, nor an email fall back to
   admin-issued magic links — acceptable, but worth confirming as the intended
   floor for account recovery.
