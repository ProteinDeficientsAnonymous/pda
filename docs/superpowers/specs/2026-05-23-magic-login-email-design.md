# Magic-Login Email + Resend Integration

**Status:** approved, ready for plan
**Date:** 2026-05-23
**Related issue:** #430 (smtp integration) — partial; remaining transactional emails (welcome, approval) deferred to follow-up

## Background

Phase 1 of the SMS→email pivot (PR #433) made email a first-class field on every user. This is phase 2: actually send something via email.

The first transactional send is the **magic-login link**. Today when a user hits "request login link" on `/login`, the backend generates a token, creates an in-app notification for admins, and admins manually broker delivery (currently via SMS or chat). With email collected for every user, we can skip the human in the loop and deliver the link straight to the user's inbox.

This phase also stands up the Resend-backed email-sending pipeline that future transactional emails (welcome, approval, blasts) will reuse.

## Goals

1. Add a provider-abstracted email-sender layer; Resend is the first implementation.
2. When a user requests a login link and has an email on file, deliver the magic link via email instead of via admin-mediated SMS.
3. Preserve the existing admin-notification path as a graceful-degradation fallback (no email on file, or send failed).
4. No UI changes on the `/login` entry point — only the success copy on the request-login-link confirmation.

## Non-goals (follow-up issues)

- **Welcome emails on admin user creation** — separate follow-up under #430. Will use the same `EmailSender`.
- **Approval emails on join-request approval** — same.
- **Email-based login entry point** (user submits *email* instead of phone on `/login`) — that's #429.
- **Full delivery observability** (webhooks, `EmailEvent` model, admin dashboard for bounces/spam) — explicitly considered and deferred. We rely on synchronous Resend API responses for now; expand later when send volume justifies the build.
- **Email blasts UI** — #431.
- **Email verification / double opt-in.**

## Design

### Provider layer

Three new modules in `backend/notifications/`:

- `email_sender.py` — defines the `EmailSender` protocol and `SendResult` dataclass:

  ```python
  class SendResult(BaseModel):
      success: bool
      provider_message_id: str | None = None
      error: str | None = None

  class EmailSender(Protocol):
      def send(self, to: str, subject: str, html: str, text: str) -> SendResult: ...
  ```

- `_resend_sender.py` — `ResendSender` class. Uses the official `resend` Python SDK. Reads `RESEND_API_KEY` and `RESEND_FROM_EMAIL` from settings. Returns the Resend message ID on success; catches exceptions and returns `success=False` on failure. Logs every send (success or failure).

- `_console_sender.py` — `ConsoleSender`. Dev/test fallback. Logs the email to stdout, returns `success=True`. Used when no `RESEND_API_KEY` is set.

A factory `get_email_sender()` in `email_sender.py` resolves the right implementation at module-import time based on `settings.RESEND_API_KEY`. In production with no API key set, raises at import (fail-fast). In dev/test, returns `ConsoleSender`.

### Settings

New env vars (added to `backend/config/settings.py`):

- `RESEND_API_KEY` — Resend API key. Required in production; absent in dev → console fallback.
- `RESEND_FROM_EMAIL` — From-address for outbound mail (e.g. `noreply@protein-deficients.org`). Required when `RESEND_API_KEY` is set.

`.env.example` updated with empty placeholders.

### Templates

Two template files under `backend/templates/emails/`:

- `magic_login.html` — HTML body. Contains: friendly greeting, a button styled inline (email-safe CSS) linking to the magic-login URL, a plain-text URL fallback below the button, an "expires in 7 days" note, and the standard footer. **Does not include the user's phone number** (no PII echoed in email).
- `magic_login.txt` — Plain-text alternative. Same content, no styling.

Rendered via `django.template.loader.render_to_string` with context `{display_name, magic_link_url, expires_at}`.

### Magic-login flow change

In `backend/community/_login_link.py` `request_login_link()`, after the existing token-generation step:

```
1. (existing) Validate phone, find user, rate-limit, dedup.
2. (existing) Generate magic_token.
3. NEW: If user.email is set:
   a. Render the magic_login email templates with context.
   b. Call email_sender.send(...).
   c. On success: audit_log "magic_link_email_sent" with provider_message_id. RETURN 200.
   d. On failure: audit_log "magic_link_email_failed". Fall through to step 4.
4. (existing) Create the admin in-app notification.
5. (existing) Audit-log "magic_link_requested".
6. Return the same generic 200 (anti-enumeration unchanged).
```

The frontend success copy on `RequestLoginLinkDialog` updates to:

> "if there's an account for that number, we sent a login link to the email on file."

Anti-enumeration shape preserved — same response regardless of whether the user exists, has an email, or the send succeeded.

### Error handling

| Failure | Behavior |
|---|---|
| Resend network/5xx error | Log exception. `send()` returns `success=False`. Caller falls through to admin notify. |
| Resend 4xx (e.g. invalid recipient) | Same as above — log, return failure, fall through. |
| Template rendering error | Caught, logged, returns `success=False`. Falls through. |
| Missing `RESEND_API_KEY` in production | Raised at startup (fail-fast). Dev unaffected (uses console). |
| Missing `RESEND_FROM_EMAIL` when key is set | Raised at startup. |

All paths return the same generic 200 to the endpoint caller to preserve anti-enumeration.

### Dependencies

New Python dep: `resend` (official Python SDK). Added to `pyproject.toml`.

## Components touched

**Backend** (~9 files)

1. `backend/config/settings.py` — Add `RESEND_API_KEY`, `RESEND_FROM_EMAIL`.
2. `backend/notifications/email_sender.py` (new) — Protocol, dataclass, factory.
3. `backend/notifications/_resend_sender.py` (new) — Resend implementation.
4. `backend/notifications/_console_sender.py` (new) — Console fallback.
5. `backend/templates/emails/magic_login.html` (new).
6. `backend/templates/emails/magic_login.txt` (new).
7. `backend/community/_login_link.py` — Email branch added before admin-notify path.
8. `backend/tests/test_request_login_link.py` — New tests for email path.
9. `backend/tests/test_email_sender.py` (new) — Unit tests for sender layer.
10. `.env.example` — Add empty `RESEND_API_KEY=` and `RESEND_FROM_EMAIL=`.
11. `pyproject.toml` — Add `resend` to deps.

**Frontend** (~2 files)

1. `frontend/src/screens/auth/RequestLoginLinkDialog.tsx` — Update success copy.
2. `frontend/src/screens/auth/RequestLoginLinkDialog.test.tsx` — Update / add test for new copy.

## Edge cases

- **User has email but Resend rejects it (e.g. typo'd address):** Email send fails → admin notification fires → admin handles it manually. Audit log captures both events for diagnosis.
- **User has email and send succeeds, but they don't get it:** No admin notification fires (we trust Resend's success response). User retries; the dedup check (`recent_token_exists` within 5 min) suppresses duplicate sends. After 5 min they can retry and a new token + email goes out.
- **User has no email yet (legacy):** Existing admin-notify path runs unchanged. We're in transition; the `RequireEmail` modal from phase 1 will eventually catch all of them.
- **Resend rate-limit hit:** Same as any other failure — falls through to admin notify.
- **Test environment:** `ConsoleSender` is used (no `RESEND_API_KEY`). Tests can either rely on console output or inject a `FakeSender` test double via a fixture.

## Testing

### Unit — email sender layer

- `ResendSender` with `responses` library mocking the Resend HTTP API:
  - 200 response → `SendResult(success=True, provider_message_id="...")`.
  - 4xx response → `SendResult(success=False, error=...)`.
  - 5xx response → `SendResult(success=False, error=...)`.
  - Network exception → `SendResult(success=False, error=...)`.
- `ConsoleSender`:
  - Returns `SendResult(success=True)`.
  - Logs the rendered email.
- Factory:
  - Returns `ResendSender` when `RESEND_API_KEY` set.
  - Returns `ConsoleSender` otherwise.
  - Raises in production when key is missing.

### Integration — request-login-link flow

- User with email + send succeeds → no admin notification, audit log "magic_link_email_sent".
- User with email + send fails → admin notification created, audit log "magic_link_email_failed" AND "magic_link_requested" (existing).
- User with no email → admin notification created (no email send attempt), audit log "magic_link_requested" only.
- Existing tests (rate-limit, dedup, invalid phone, unknown user) still pass.

### Templates

- `render_to_string("emails/magic_login.html", ctx)`:
  - Output contains the magic-login URL.
  - Output contains "expires" / "7 days" copy.
  - Output does NOT contain the phone number (PII guard).

## Rollout

1. Merge to staging. `RESEND_API_KEY` not set yet → console fallback, no real sends. Verify the admin-notify path still works.
2. Set `RESEND_API_KEY` + `RESEND_FROM_EMAIL` on staging Railway env.
3. Verify a magic-link request to a test account delivers a real email.
4. Promote to production with the prod Resend key.

## Open questions for plan-writing

- Confirm whether the `resend` SDK is preferred over plain `requests` to Resend's REST API. The SDK is officially supported and ~100 LOC of cover; using it is the cleaner default.
- Whether the `ConsoleSender` should also be the test default, or tests should inject a `FakeSender` via a fixture (cleaner assertions, no log capture needed). Lean toward `FakeSender` via fixture.
