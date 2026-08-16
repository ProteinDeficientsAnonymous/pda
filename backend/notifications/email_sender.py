"""Provider-agnostic email sender.

`EmailSender` is the protocol every concrete sender (Resend, Brevo, Console)
must satisfy. `SendResult` is the response shape callers can inspect to decide
whether to surface or fall back.

Sends are split into two streams so one-per-member broadcasts cannot exhaust
the transactional provider's daily allowance:

- `EmailStream.TRANSACTIONAL` (Resend) — login links, RSVP confirmations,
  join approvals, invites, host nudges. Low volume, latency-sensitive.
- `EmailStream.BULK` (Brevo) — weekly digest, event blasts. High volume,
  fan-out to the whole membership.

Resolution: `get_email_sender(stream)` returns the right implementation based
on the provider key configured for that stream. Production with no key raises
(fail-fast) so bulk volume never silently falls back onto the transactional
provider; dev and test use the console sender.
"""

import hashlib
import logging
import threading
from collections.abc import Callable
from enum import StrEnum
from typing import Protocol, runtime_checkable

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from pydantic import BaseModel

logger = logging.getLogger("notifications.email_sender")


class SendResult(BaseModel):
    success: bool
    provider_message_id: str | None = None
    error: str | None = None


def mask_recipient(to: str) -> str:
    """Return a non-reversible, low-cardinality token for log correlation.

    Avoids logging the raw recipient address (PII). Lives at the email boundary
    so every sender masks recipients the same way and logs stay correlatable
    without exposing the address. Keep only a short hash prefix.
    """
    digest = hashlib.sha256(to.strip().lower().encode("utf-8")).hexdigest()
    return f"sha256:{digest[:12]}"


def validate_recipient(to: str) -> None:
    """Reject malformed recipients and header-injection attempts.

    Validated at the sender boundary so every email type and every concrete
    sender is protected — not just whichever helper remembers to call it.
    ``validate_email`` already rejects embedded newlines/carriage returns
    (the header-injection vector), so it is the sole check needed.
    """
    try:
        validate_email(to)
    except DjangoValidationError as exc:
        raise ValueError(f"invalid recipient address: {to!r}") from exc


@runtime_checkable
class EmailSender(Protocol):
    def send(self, to: str, subject: str, html: str, text: str) -> SendResult: ...


class EmailStream(StrEnum):
    """Which provider a send is routed to. See the module docstring."""

    TRANSACTIONAL = "transactional"
    BULK = "bulk"


def _console_sender() -> EmailSender:
    # lazy import avoids circular dependency with email_sender
    from notifications._console_sender import ConsoleSender

    return ConsoleSender()


def _resolve_transactional() -> EmailSender:
    if settings.RESEND_API_KEY:
        # lazy import avoids circular dependency with email_sender
        from notifications._resend_sender import ResendSender

        return ResendSender()
    if getattr(settings, "IS_PRODUCTION", False):
        raise RuntimeError("RESEND_API_KEY is required in production but is not set")
    return _console_sender()


def _resolve_bulk() -> EmailSender:
    if settings.BREVO_API_KEY:
        # lazy import avoids circular dependency with email_sender
        from notifications._brevo_sender import BrevoSender

        return BrevoSender()
    if getattr(settings, "IS_PRODUCTION", False):
        # Deliberately not falling back to Resend: bulk fan-out is exactly what
        # exhausts the transactional daily allowance, so an unconfigured bulk
        # provider must fail the digest/blast rather than quietly consume it.
        raise RuntimeError("BREVO_API_KEY is required in production but is not set")
    return _console_sender()


_RESOLVERS: dict[EmailStream, Callable[[], EmailSender]] = {
    EmailStream.TRANSACTIONAL: _resolve_transactional,
    EmailStream.BULK: _resolve_bulk,
}

_cached_senders: dict[EmailStream, EmailSender] = {}
_cache_lock = threading.Lock()


def get_email_sender(stream: EmailStream = EmailStream.TRANSACTIONAL) -> EmailSender:
    """Resolve the configured sender for a stream. Cached per process (thread-safe).

    param stream(EmailStream): which provider to route through; defaults to transactional
    return(EmailSender): the resolved sender for that stream
    """
    cached = _cached_senders.get(stream)
    if cached is not None:
        return cached

    with _cache_lock:
        # Double-checked: another thread may have populated the cache while we
        # were waiting on the lock.
        cached = _cached_senders.get(stream)
        if cached is not None:
            return cached

        sender = _RESOLVERS[stream]()
        _cached_senders[stream] = sender
        logger.info(
            "email sender resolved: stream=%s sender=%s", stream.value, type(sender).__name__
        )
        return sender


def reset_email_sender_cache() -> None:
    """Test-only helper for clearing the cached senders between tests."""
    with _cache_lock:
        _cached_senders.clear()
