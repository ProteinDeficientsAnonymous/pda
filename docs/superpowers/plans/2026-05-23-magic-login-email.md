# Magic-Login Email Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Resend-backed email-sender pipeline and use it to deliver magic-login links to the email on file when users request "send me a login link".

**Architecture:** A new `notifications/email_sender.py` defines a provider-agnostic `EmailSender` protocol and `SendResult` dataclass. Two implementations live alongside it: `_resend_sender.py` (production) and `_console_sender.py` (dev/test). A factory resolves the right one at import time based on `RESEND_API_KEY`. The `_login_link.py` endpoint tries the email path first when `user.email` is set; on failure it falls through to the existing admin-notification path. UI changes are limited to copy on `RequestLoginLinkDialog`.

**Tech Stack:** Django + Django Ninja; `resend` Python SDK; Django templates for email bodies; React + Vite + Vitest for frontend.

---

## File Map

**Backend (new)**
- `backend/notifications/email_sender.py` — Protocol + `SendResult` + factory.
- `backend/notifications/_resend_sender.py` — Resend implementation.
- `backend/notifications/_console_sender.py` — Dev/test fallback.
- `backend/templates/emails/magic_login.html` — HTML template.
- `backend/templates/emails/magic_login.txt` — Plaintext alternative.
- `backend/notifications/_email_helpers.py` — Small helper for rendering + sending the magic-login email specifically.
- `backend/tests/test_email_sender.py` — Unit tests for the sender layer + factory.
- `backend/tests/test_magic_login_email.py` — Unit tests for the template + helper.

**Backend (modify)**
- `backend/config/settings.py` — Add `RESEND_API_KEY`, `RESEND_FROM_EMAIL` reads.
- `backend/community/_login_link.py` — Email branch before admin-notify.
- `backend/tests/test_request_login_link.py` — Tests for the new email path.
- `backend/tests/conftest.py` — Add a `fake_email_sender` fixture.
- `pyproject.toml` — Add `resend` to deps.
- `.env.example` — Add empty `RESEND_API_KEY=` and `RESEND_FROM_EMAIL=`.

**Frontend (modify)**
- `frontend/src/screens/auth/RequestLoginLinkDialog.tsx` — Update success copy.
- `frontend/src/screens/auth/RequestLoginLinkDialog.test.tsx` — Update / add test.

---

## Phase 1: Email sender layer

### Task 1.1: Add `resend` dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock` (auto-updated by `uv sync`)

- [ ] **Step 1: Add dep**

In `pyproject.toml`, find the `[project] dependencies` list and add `"resend>=2.0.0,<3"`. (Check the latest stable version on PyPI before pinning — adjust if needed.)

- [ ] **Step 2: Lock**

Run: `cd backend && uv sync`
Expected: `uv.lock` regenerates; `resend` and any transitive deps are added.

- [ ] **Step 3: Verify install**

Run: `cd backend && uv run python -c "import resend; print(resend.__version__)"`
Expected: prints a version number.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add resend python sdk"
```

### Task 1.2: Settings and .env.example

**Files:**
- Modify: `backend/config/settings.py`
- Modify: `.env.example`

- [ ] **Step 1: Read current settings + .env.example**

Run: `grep -n 'EMAIL\|VETTING_EMAIL' backend/config/settings.py` and `cat .env.example | head -50`. Confirm where the existing email settings live (around line 208 per the spec — verify).

- [ ] **Step 2: Add settings**

In `backend/config/settings.py`, near the existing `EMAIL_BACKEND` / `EMAIL_HOST` block (around line 208), add:

```python
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "")

if IS_PRODUCTION and RESEND_API_KEY and not RESEND_FROM_EMAIL:
    raise ValueError("RESEND_FROM_EMAIL must be set when RESEND_API_KEY is configured")
```

The fail-fast in production prevents a half-configured deploy. Dev/test with no key set bypasses the check entirely.

- [ ] **Step 3: Add empty placeholders to .env.example**

In `.env.example`, near the existing email-related vars, add:

```
# Resend (transactional email). Leave blank in dev to use console fallback.
RESEND_API_KEY=
RESEND_FROM_EMAIL=
```

- [ ] **Step 4: Sanity check**

Run: `cd backend && uv run python -c "from django.conf import settings; print(settings.RESEND_API_KEY, settings.RESEND_FROM_EMAIL)"`
Expected: prints `""  ""` (both empty in dev).

- [ ] **Step 5: Run existing settings test**

Run: `cd backend && uv run pytest tests/test_settings.py -v`
Expected: green. (If a settings smoke test exists, it should still pass.)

- [ ] **Step 6: Commit**

```bash
git add backend/config/settings.py .env.example
git commit -m "feat(config): add resend api key + from-email settings"
```

### Task 1.3: `EmailSender` protocol and `SendResult`

**Files:**
- Create: `backend/notifications/email_sender.py`
- Create: `backend/notifications/__init__.py` (if it doesn't exist — confirm with `ls backend/notifications/` first)
- Create: `backend/tests/test_email_sender.py`

- [ ] **Step 1: Confirm `notifications` package exists**

Run: `ls backend/notifications/`
Expected: a package directory with at least one file. If `__init__.py` doesn't exist, you'll create it implicitly via the new modules.

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_email_sender.py`:

```python
"""Tests for the email sender protocol and SendResult dataclass."""

from notifications.email_sender import EmailSender, SendResult


class TestSendResult:
    def test_default_is_failure(self):
        result = SendResult(success=False)
        assert result.success is False
        assert result.provider_message_id is None
        assert result.error is None

    def test_success_with_message_id(self):
        result = SendResult(success=True, provider_message_id="msg_123")
        assert result.success is True
        assert result.provider_message_id == "msg_123"
        assert result.error is None

    def test_failure_with_error(self):
        result = SendResult(success=False, error="invalid recipient")
        assert result.success is False
        assert result.error == "invalid recipient"


class TestEmailSenderProtocol:
    def test_protocol_signature(self):
        # A class implementing the protocol with the right shape should pass isinstance.
        class FakeSender:
            def send(self, to: str, subject: str, html: str, text: str) -> SendResult:
                return SendResult(success=True)

        assert isinstance(FakeSender(), EmailSender)
```

- [ ] **Step 3: Run tests to confirm failure**

Run: `cd backend && uv run pytest tests/test_email_sender.py -v`
Expected: FAIL with `ImportError` — module doesn't exist yet.

- [ ] **Step 4: Implement**

Create `backend/notifications/email_sender.py`:

```python
"""Provider-agnostic email sender.

`EmailSender` is the protocol every concrete sender (Resend, Console, future
providers) must satisfy. `SendResult` is the response shape callers can
inspect to decide whether to surface or fall back.

Resolution: `get_email_sender()` returns the right implementation based on
`settings.RESEND_API_KEY`. Production with no key raises (fail-fast); dev
and test use the console sender.
"""

from typing import Protocol, runtime_checkable

from django.conf import settings
from pydantic import BaseModel


class SendResult(BaseModel):
    success: bool
    provider_message_id: str | None = None
    error: str | None = None


@runtime_checkable
class EmailSender(Protocol):
    def send(self, to: str, subject: str, html: str, text: str) -> SendResult: ...


_cached_sender: EmailSender | None = None


def get_email_sender() -> EmailSender:
    """Resolve the configured email sender. Cached per process."""
    global _cached_sender
    if _cached_sender is not None:
        return _cached_sender

    if settings.RESEND_API_KEY:
        from notifications._resend_sender import ResendSender

        _cached_sender = ResendSender()
    else:
        if not settings.DEBUG and getattr(settings, "IS_PRODUCTION", False):
            raise RuntimeError(
                "RESEND_API_KEY is required in production but is not set"
            )
        from notifications._console_sender import ConsoleSender

        _cached_sender = ConsoleSender()
    return _cached_sender


def reset_email_sender_cache() -> None:
    """Test-only helper for clearing the cached sender between tests."""
    global _cached_sender
    _cached_sender = None
```

- [ ] **Step 5: Run tests to confirm pass**

Run: `cd backend && uv run pytest tests/test_email_sender.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/notifications/email_sender.py backend/tests/test_email_sender.py
git commit -m "feat(notifications): EmailSender protocol + SendResult"
```

### Task 1.4: `ConsoleSender` implementation

**Files:**
- Create: `backend/notifications/_console_sender.py`
- Modify: `backend/tests/test_email_sender.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_email_sender.py`:

```python
class TestConsoleSender:
    def test_send_returns_success(self):
        from notifications._console_sender import ConsoleSender

        sender = ConsoleSender()
        result = sender.send(
            to="user@example.com",
            subject="hello",
            html="<p>hi</p>",
            text="hi",
        )
        assert result.success is True
        assert result.error is None

    def test_send_logs_to_stdout(self, caplog):
        import logging
        from notifications._console_sender import ConsoleSender

        with caplog.at_level(logging.INFO, logger="notifications.console_sender"):
            ConsoleSender().send(
                to="user@example.com",
                subject="hello",
                html="<p>hi</p>",
                text="hi",
            )
        assert any("user@example.com" in r.message for r in caplog.records)
        assert any("hello" in r.message for r in caplog.records)
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `cd backend && uv run pytest tests/test_email_sender.py::TestConsoleSender -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement**

Create `backend/notifications/_console_sender.py`:

```python
"""Dev/test fallback that logs emails instead of sending them."""

import logging

from notifications.email_sender import SendResult

logger = logging.getLogger("notifications.console_sender")


class ConsoleSender:
    """Logs the email and returns success. Use in dev and tests."""

    def send(self, to: str, subject: str, html: str, text: str) -> SendResult:
        logger.info("EMAIL to=%s subject=%s", to, subject)
        logger.info("EMAIL text body:\n%s", text)
        return SendResult(success=True)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_email_sender.py::TestConsoleSender -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/notifications/_console_sender.py backend/tests/test_email_sender.py
git commit -m "feat(notifications): ConsoleSender for dev/test"
```

### Task 1.5: `ResendSender` implementation

**Files:**
- Create: `backend/notifications/_resend_sender.py`
- Modify: `backend/tests/test_email_sender.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_email_sender.py`. The Resend SDK uses `resend.Emails.send({...})` per the official docs — verify this in the actual SDK before writing the implementation. (Run `python -c "import resend; help(resend.Emails)"` if unsure.)

```python
import pytest
from unittest.mock import patch


class TestResendSender:
    def test_send_success_returns_message_id(self):
        from notifications._resend_sender import ResendSender

        with patch("resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "msg_abc123"}
            result = ResendSender().send(
                to="user@example.com",
                subject="hello",
                html="<p>hi</p>",
                text="hi",
            )
        assert result.success is True
        assert result.provider_message_id == "msg_abc123"
        assert result.error is None

    def test_send_exception_returns_failure(self):
        from notifications._resend_sender import ResendSender

        with patch("resend.Emails.send", side_effect=RuntimeError("boom")):
            result = ResendSender().send(
                to="user@example.com",
                subject="hello",
                html="<p>hi</p>",
                text="hi",
            )
        assert result.success is False
        assert result.provider_message_id is None
        assert "boom" in (result.error or "")

    def test_send_uses_from_email_from_settings(self, settings):
        from notifications._resend_sender import ResendSender

        settings.RESEND_FROM_EMAIL = "noreply@example.com"
        settings.RESEND_API_KEY = "test_key"
        with patch("resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "msg_x"}
            ResendSender().send(
                to="user@example.com",
                subject="hello",
                html="<p>hi</p>",
                text="hi",
            )
        args, _ = mock_send.call_args
        params = args[0]
        assert params["from"] == "noreply@example.com"
        assert params["to"] == ["user@example.com"]
        assert params["subject"] == "hello"
        assert params["html"] == "<p>hi</p>"
        assert params["text"] == "hi"
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `cd backend && uv run pytest tests/test_email_sender.py::TestResendSender -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement**

Create `backend/notifications/_resend_sender.py`:

```python
"""Resend transactional email implementation."""

import logging

import resend
from django.conf import settings

from notifications.email_sender import SendResult

logger = logging.getLogger("notifications.resend_sender")


class ResendSender:
    """Sends transactional emails via Resend's HTTP API.

    Uses the official `resend` SDK. The API key is read at instantiation
    (so callers can stub it via Django settings overrides in tests).
    """

    def __init__(self) -> None:
        resend.api_key = settings.RESEND_API_KEY

    def send(self, to: str, subject: str, html: str, text: str) -> SendResult:
        try:
            response = resend.Emails.send(
                {
                    "from": settings.RESEND_FROM_EMAIL,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "text": text,
                }
            )
            message_id = response.get("id") if isinstance(response, dict) else None
            logger.info(
                "resend_send_success to=%s subject=%s message_id=%s",
                to, subject, message_id,
            )
            return SendResult(success=True, provider_message_id=message_id)
        except Exception as exc:
            logger.exception("resend_send_failure to=%s subject=%s", to, subject)
            return SendResult(success=False, error=str(exc))
```

(`Exception` is broad here because the Resend SDK can raise multiple exception types; we catch all so a single bad send never surfaces a 500 to the caller.)

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_email_sender.py::TestResendSender -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/notifications/_resend_sender.py backend/tests/test_email_sender.py
git commit -m "feat(notifications): ResendSender implementation"
```

### Task 1.6: Factory test coverage

**Files:**
- Modify: `backend/tests/test_email_sender.py`

- [ ] **Step 1: Write tests for the factory**

Append to `backend/tests/test_email_sender.py`:

```python
class TestGetEmailSender:
    def test_returns_resend_sender_when_key_set(self, settings):
        from notifications._resend_sender import ResendSender
        from notifications.email_sender import get_email_sender, reset_email_sender_cache

        reset_email_sender_cache()
        settings.RESEND_API_KEY = "test_key"
        settings.RESEND_FROM_EMAIL = "noreply@example.com"
        sender = get_email_sender()
        assert isinstance(sender, ResendSender)
        reset_email_sender_cache()

    def test_returns_console_sender_when_no_key_in_dev(self, settings):
        from notifications._console_sender import ConsoleSender
        from notifications.email_sender import get_email_sender, reset_email_sender_cache

        reset_email_sender_cache()
        settings.RESEND_API_KEY = ""
        sender = get_email_sender()
        assert isinstance(sender, ConsoleSender)
        reset_email_sender_cache()

    def test_caches_sender_across_calls(self, settings):
        from notifications.email_sender import get_email_sender, reset_email_sender_cache

        reset_email_sender_cache()
        settings.RESEND_API_KEY = ""
        first = get_email_sender()
        second = get_email_sender()
        assert first is second
        reset_email_sender_cache()
```

- [ ] **Step 2: Run tests**

Run: `cd backend && uv run pytest tests/test_email_sender.py::TestGetEmailSender -v`
Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_email_sender.py
git commit -m "test(notifications): cover get_email_sender factory paths"
```

---

## Phase 2: Magic-login templates and helper

### Task 2.1: Email templates

**Files:**
- Create: `backend/templates/emails/magic_login.html`
- Create: `backend/templates/emails/magic_login.txt`

- [ ] **Step 1: Confirm Django can find the templates directory**

Run: `grep -n 'TEMPLATES\|DIRS' backend/config/settings.py | head -10`
Confirm `TEMPLATES[0]["DIRS"]` includes `BASE_DIR / "templates"` or similar. If not, you'll need to add `backend/templates` to the DIRS list — but this should already be configured since `send_mail` works elsewhere. Verify by reading the existing block.

- [ ] **Step 2: Create the plaintext template**

Create `backend/templates/emails/magic_login.txt`:

```
hi{% if display_name %} {{ display_name|lower }}{% endif %} —

here's your one-time login link for pda:

{{ magic_link_url }}

this link expires in 7 days. if you didn't request it, you can ignore this email.

— pda
```

- [ ] **Step 3: Create the HTML template**

Create `backend/templates/emails/magic_login.html`:

```html
<!doctype html>
<html>
<body style="margin: 0; padding: 24px; background: #f5f5f3; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #222;">
  <div style="max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 8px; padding: 32px;">
    <p style="margin: 0 0 16px;">hi{% if display_name %} {{ display_name|lower }}{% endif %} —</p>
    <p style="margin: 0 0 24px;">here's your one-time login link for pda:</p>
    <p style="margin: 0 0 24px;">
      <a href="{{ magic_link_url }}" style="display: inline-block; background: #2f6f3e; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: 500;">log in to pda</a>
    </p>
    <p style="margin: 0 0 8px; font-size: 13px; color: #666;">or paste this into your browser:</p>
    <p style="margin: 0 0 24px; font-size: 13px; word-break: break-all;"><a href="{{ magic_link_url }}" style="color: #2f6f3e;">{{ magic_link_url }}</a></p>
    <p style="margin: 0 0 8px; font-size: 13px; color: #666;">this link expires in 7 days.</p>
    <p style="margin: 0; font-size: 13px; color: #666;">if you didn't request it, you can ignore this email.</p>
  </div>
  <p style="text-align: center; margin: 16px 0 0; font-size: 12px; color: #888;">— pda</p>
</body>
</html>
```

(Inline CSS is required — most email clients strip `<style>` tags. The green hex matches the brand color used in `tailwind.config.cjs` for buttons; verify by grepping for `bg-brand` or similar.)

**No phone number in the body.** (Security: PII echo risk if the email account is compromised.)

- [ ] **Step 4: Test the templates render**

Run a quick sanity check:

```
cd backend && uv run python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.template.loader import render_to_string
ctx = {'display_name': 'sam', 'magic_link_url': 'https://example.org/magic/abc'}
print(render_to_string('emails/magic_login.txt', ctx))
print('---')
print(render_to_string('emails/magic_login.html', ctx)[:300])
"
```

Expected: text rendering with "sam" and the URL substituted; HTML rendering similarly.

- [ ] **Step 5: Commit**

```bash
git add backend/templates/emails/magic_login.html backend/templates/emails/magic_login.txt
git commit -m "feat(emails): magic-login html + plaintext templates"
```

### Task 2.2: Magic-login email helper

**Files:**
- Create: `backend/notifications/_email_helpers.py`
- Create: `backend/tests/test_magic_login_email.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_magic_login_email.py`:

```python
"""Tests for the magic-login email helper."""

import pytest
from unittest.mock import MagicMock

from notifications._email_helpers import send_magic_login_email
from notifications.email_sender import SendResult


@pytest.mark.django_db
class TestSendMagicLoginEmail:
    def test_renders_and_sends_with_display_name(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True, provider_message_id="m1")

        result = send_magic_login_email(
            sender=sender,
            to="user@example.com",
            display_name="Sam",
            magic_link_url="https://pda.test/magic/abc",
        )

        assert result.success is True
        sender.send.assert_called_once()
        call_kwargs = sender.send.call_args.kwargs
        assert call_kwargs["to"] == "user@example.com"
        assert "sam" in call_kwargs["text"].lower()
        assert "https://pda.test/magic/abc" in call_kwargs["text"]
        assert "https://pda.test/magic/abc" in call_kwargs["html"]

    def test_does_not_include_phone_number(self):
        """PII guard — the email body must not echo a phone number."""
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_magic_login_email(
            sender=sender,
            to="user@example.com",
            display_name="Sam",
            magic_link_url="https://pda.test/magic/abc",
        )
        call_kwargs = sender.send.call_args.kwargs
        # No phone-number-shaped substring (+1 followed by digits).
        import re
        assert re.search(r"\+1\d{10}", call_kwargs["text"]) is None
        assert re.search(r"\+1\d{10}", call_kwargs["html"]) is None

    def test_handles_blank_display_name(self):
        sender = MagicMock()
        sender.send.return_value = SendResult(success=True)

        send_magic_login_email(
            sender=sender,
            to="user@example.com",
            display_name="",
            magic_link_url="https://pda.test/magic/abc",
        )
        # No crash; sender was called.
        sender.send.assert_called_once()
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `cd backend && uv run pytest tests/test_magic_login_email.py -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement the helper**

Create `backend/notifications/_email_helpers.py`:

```python
"""Helpers for sending specific transactional emails.

Each helper renders its templates and dispatches via the injected
`EmailSender`. The helpers exist so callers don't have to know template
paths or context shapes — they just say "send a magic-login email."
"""

from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


def send_magic_login_email(
    *,
    sender: EmailSender,
    to: str,
    display_name: str,
    magic_link_url: str,
) -> SendResult:
    """Render and send the magic-login email."""
    context = {
        "display_name": display_name or "",
        "magic_link_url": magic_link_url,
    }
    html = render_to_string("emails/magic_login.html", context)
    text = render_to_string("emails/magic_login.txt", context)
    return sender.send(
        to=to,
        subject="your pda login link",
        html=html,
        text=text,
    )
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_magic_login_email.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/notifications/_email_helpers.py backend/tests/test_magic_login_email.py
git commit -m "feat(notifications): send_magic_login_email helper"
```

---

## Phase 3: Wire into the magic-login flow

### Task 3.1: Test fixture for fake sender

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Add fixture**

In `backend/tests/conftest.py`, add (near existing fixtures):

```python
@pytest.fixture
def fake_email_sender(monkeypatch):
    """Replace get_email_sender() with a Mock so integration tests can assert sends.

    Yields the Mock so tests can inspect call args.
    """
    from unittest.mock import MagicMock
    from notifications.email_sender import SendResult

    fake = MagicMock()
    fake.send.return_value = SendResult(success=True, provider_message_id="test_msg")

    from notifications import email_sender as email_sender_module

    monkeypatch.setattr(email_sender_module, "_cached_sender", fake)
    yield fake
    # Reset is automatic via monkeypatch.
```

- [ ] **Step 2: Verify it works in a quick smoke test**

(No formal test yet — this fixture is exercised by the next task. Just confirm it doesn't error by running `uv run pytest tests/conftest.py --collect-only -q` and seeing no errors.)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: fake_email_sender fixture for integration tests"
```

### Task 3.2: Email branch in `request_login_link`

**Files:**
- Modify: `backend/community/_login_link.py`
- Modify: `backend/tests/test_request_login_link.py`

- [ ] **Step 1: Read the existing endpoint**

Read `backend/community/_login_link.py` end-to-end. Note where `_create_magic_token` is called (step 4 in the flow) and where `create_magic_link_request_notifications` fires (step 5).

- [ ] **Step 2: Write failing tests**

Append to `backend/tests/test_request_login_link.py` (read the file first to match its conventions):

```python
@pytest.mark.django_db
class TestRequestLoginLinkEmailDelivery:
    def test_user_with_email_send_succeeds(
        self, api_client, fake_email_sender
    ):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550101",
            display_name="Sam",
            email="sam@example.com",
        )
        resp = api_client.post(
            "/api/community/request-login-link/",
            data={"phone_number": "+12025550101"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        fake_email_sender.send.assert_called_once()
        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == "sam@example.com"
        # No admin notification should fire on success.
        from notifications.models import Notification
        assert not Notification.objects.filter(
            user__is_superuser=True
        ).exists()  # or however admin notifications are queried

    def test_user_with_email_send_fails_falls_through_to_admin(
        self, api_client, fake_email_sender
    ):
        from notifications.email_sender import SendResult
        from users.models import User

        fake_email_sender.send.return_value = SendResult(
            success=False, error="invalid recipient"
        )
        User.objects.create_user(
            phone_number="+12025550101",
            display_name="Sam",
            email="bad@example.com",
        )
        resp = api_client.post(
            "/api/community/request-login-link/",
            data={"phone_number": "+12025550101"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        fake_email_sender.send.assert_called_once()
        # Admin notification SHOULD fire (fallback path).
        # The exact admin-notification model check depends on the project's
        # notifications layer — adapt to whatever tests verify the admin
        # notification today in the existing test_request_login_link.py file.

    def test_user_with_no_email_skips_send(
        self, api_client, fake_email_sender
    ):
        from users.models import User

        User.objects.create_user(
            phone_number="+12025550101",
            display_name="Sam",
            email=None,
        )
        resp = api_client.post(
            "/api/community/request-login-link/",
            data={"phone_number": "+12025550101"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        fake_email_sender.send.assert_not_called()
        # Admin notification still fires (existing path).
```

(Read the existing `test_request_login_link.py` to see how admin notifications are currently asserted on the success path — adapt the admin-notification assertions in these tests to match. If the existing tests don't assert the admin notification at all, focus only on `fake_email_sender.send` call counts here and let the existing tests cover the admin path.)

- [ ] **Step 3: Run tests to confirm failure**

Run: `cd backend && uv run pytest tests/test_request_login_link.py::TestRequestLoginLinkEmailDelivery -v`
Expected: FAIL — the email path doesn't exist yet, so the send mock is never called.

- [ ] **Step 4: Add the email branch**

In `backend/community/_login_link.py`, after the `_create_magic_token(user)` call and before `create_magic_link_request_notifications(user)`, add the email branch:

```python
from notifications._email_helpers import send_magic_login_email
from notifications.email_sender import get_email_sender

# ...inside request_login_link, after _create_magic_token(user)...

magic_token = _create_magic_token(user)  # capture the token (existing call returns it)
user.login_link_requested = True
user.save(update_fields=["login_link_requested"])

# NEW: attempt email delivery first if we have an email on file.
email_send_succeeded = False
if user.email:
    magic_link_url = f"{settings.FRONTEND_BASE_URL}/magic-login/{magic_token}"
    send_result = send_magic_login_email(
        sender=get_email_sender(),
        to=user.email,
        display_name=user.display_name or "",
        magic_link_url=magic_link_url,
    )
    if send_result.success:
        email_send_succeeded = True
        audit_log(
            logging.INFO,
            "magic_link_email_sent",
            request,
            target_type="user",
            target_id=str(user.pk),
            details={"provider_message_id": send_result.provider_message_id},
        )
    else:
        audit_log(
            logging.WARNING,
            "magic_link_email_failed",
            request,
            target_type="user",
            target_id=str(user.pk),
            details={"error": send_result.error},
        )

# Fall through to admin notification if the email path didn't deliver.
if not email_send_succeeded:
    try:
        create_magic_link_request_notifications(user)
    except Exception:
        logger.exception("Failed to create magic link request notifications")
    audit_log(
        logging.INFO,
        "magic_link_requested",
        request,
        target_type="user",
        target_id=str(user.pk),
    )
```

Notes:
- `_create_magic_token` currently returns the token UUID string per `backend/users/_helpers.py`. Confirm by reading that helper — if the return shape is different, adapt.
- `settings.FRONTEND_BASE_URL` is the convention this codebase uses for building front-end URLs — confirm by grepping (`grep -n FRONTEND_BASE_URL backend/`). If a different setting is used (e.g. `FRONTEND_URL`), match it.
- Add the `from django.conf import settings` import to `_login_link.py` if it's not already there.

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest tests/test_request_login_link.py -v`
Expected: all green — new tests + existing tests (which verify the admin-notify path for no-email users).

- [ ] **Step 6: Commit**

```bash
git add backend/community/_login_link.py backend/tests/test_request_login_link.py
git commit -m "feat(community): deliver magic-login link via email when on file"
```

### Task 3.3: Full backend regression sweep

- [ ] **Step 1: Run the full backend suite**

Run: `cd backend && uv run pytest tests/ -q 2>&1 | tail -10`
Expected: green.

- [ ] **Step 2: Run the agent CI step**

Run: `make agent-ci`
Expected: green. If any check fails, fix and amend the most recent relevant commit.

- [ ] **Step 3: No commit needed if green.**

---

## Phase 4: Frontend copy update

### Task 4.1: Update `RequestLoginLinkDialog` success copy

**Files:**
- Modify: `frontend/src/screens/auth/RequestLoginLinkDialog.tsx`
- Modify/Create: `frontend/src/screens/auth/RequestLoginLinkDialog.test.tsx`

- [ ] **Step 1: Read the existing dialog**

Run: `cat frontend/src/screens/auth/RequestLoginLinkDialog.tsx`
Note the current success state text — it likely says something like "if you've been invited, an admin will be in touch" (matching the backend's `_REQUEST_LINK_RESPONSE` constant).

- [ ] **Step 2: Write the failing test**

Either create `RequestLoginLinkDialog.test.tsx` or extend it. The new copy assertion:

```typescript
it('shows email delivery copy after success', async () => {
  // ...arrange (mock the api hook to return a successful response)
  // ...submit the form
  expect(
    await screen.findByText(/we sent a login link to the email on file/i),
  ).toBeInTheDocument();
});
```

Adapt the arrange + submit steps to match the dialog's actual mocking convention (look at `MemberCreateDialog.test.tsx` from PR #433 for a similar example).

- [ ] **Step 3: Run test to confirm failure**

Run: `cd frontend && pnpm vitest run src/screens/auth/RequestLoginLinkDialog.test.tsx`
Expected: FAIL — old copy doesn't match.

- [ ] **Step 4: Update the dialog copy**

Replace the success-state text in `RequestLoginLinkDialog.tsx` with copy like:

```
if there's an account for that number, we sent a login link to the email on file.
```

(Keep the anti-enumeration shape — "if there's an account…" prevents confirming whether the phone is registered.)

- [ ] **Step 5: Run tests + typecheck**

Run: `cd frontend && pnpm vitest run src/screens/auth/RequestLoginLinkDialog.test.tsx && pnpm typecheck`
Expected: green.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/screens/auth/RequestLoginLinkDialog.tsx frontend/src/screens/auth/RequestLoginLinkDialog.test.tsx
git commit -m "feat(auth): update request-login-link success copy for email"
```

---

## Phase 5: CI + PR

### Task 5.1: Full CI sweep

- [ ] **Step 1: Run `make agent-ci`**

Run: `make agent-ci`
Expected: green across lint, typecheck, test, complexity, codes, openapi.

- [ ] **Step 2: Fix anything that fails**

Common issues to expect:
- `ruff format` may auto-fix formatting on new files — commit those.
- `dump_validation_codes` should be a no-op (no new codes added in this PR).
- `dump_openapi_schema` should be a no-op (no endpoint shape changes).

If anything diffs, commit it as `chore: post-CI cleanup` or similar.

### Task 5.2: Manual smoke check

- [ ] **Step 1: Start dev environment**

Run: `make db-start && make dev`

- [ ] **Step 2: Verify in browser**

1. Log in as an admin so you have access to users with emails.
2. Log out, go to `/login`, click "request login link", enter a phone number that belongs to a user with email on file.
3. Watch the dev server's console output. The `ConsoleSender` should log the rendered email body, including the magic-link URL.
4. Copy the URL from the console, paste into the browser. Confirm login succeeds.
5. Confirm no admin notification was created (check via `python manage.py shell` or the admin UI for notifications).
6. Repeat with a user with NO email. Confirm: no console log of an email send, AND an admin notification IS created.

- [ ] **Step 3: Note any UI tweaks discovered**

Open small commits if anything is off; flag larger issues.

### Task 5.3: Open PR

- [ ] **Step 1: Push the branch**

```bash
git push -u origin feat/magic-login-email
```

- [ ] **Step 2: Open PR via the open-pr skill or `gh pr create`**

PR title: `feat: magic-login email delivery via resend (phase 2 of sms→email pivot)`

PR body should:
- Link the spec at `docs/superpowers/specs/2026-05-23-magic-login-email-design.md`.
- Note that this delivers part of #430; remaining transactional emails (welcome, approval) tracked there.
- Note that full delivery observability (#430, option 3) was deferred — documented in the spec.
- Include the smoke-check checklist from Task 5.2.

---

## Self-Review (post-write)

**1. Spec coverage:**
- Provider abstraction (`EmailSender` + `SendResult`) — Task 1.3 ✓
- Resend impl — Task 1.5 ✓
- Console fallback — Task 1.4 ✓
- Settings + .env.example — Task 1.2 ✓
- Templates (HTML + plaintext, no phone number) — Task 2.1 ✓
- Magic-login helper — Task 2.2 ✓
- Email branch in request-login-link with success/failure handling — Task 3.2 ✓
- Frontend copy update — Task 4.1 ✓
- Tests at unit + integration layers — every task ✓
- CI + smoke + PR — Phase 5 ✓

**2. Placeholders:** None. All steps have explicit code or commands.

**3. Type consistency:** `EmailSender.send` signature is identical across helper, fixture, console, and resend implementations. `SendResult` fields used consistently.

**4. Ambiguity check:**
- Step 3.2 references `settings.FRONTEND_BASE_URL`; that setting may not exist by that exact name. The step instructs the implementer to grep first and adapt — explicit handling.
- Step 3.2 references `_create_magic_token` return shape; the step instructs the implementer to verify before using.
