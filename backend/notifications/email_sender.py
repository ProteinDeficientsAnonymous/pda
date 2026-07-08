"""Provider-agnostic email sender.

`EmailSender` is the protocol every concrete sender (Resend, Console, future
providers) must satisfy. `SendResult` is the response shape callers can
inspect to decide whether to surface or fall back.

Resolution: `get_email_sender()` returns the right implementation based on
`settings.RESEND_API_KEY`. Production with no key raises (fail-fast); dev
and test use the console sender.
"""

import hashlib
import logging
import threading
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


_cached_sender: EmailSender | None = None
_cache_lock = threading.Lock()


def get_email_sender() -> EmailSender:
    """Resolve the configured email sender. Cached per process (thread-safe)."""
    global _cached_sender
    if _cached_sender is not None:
        return _cached_sender

    with _cache_lock:
        # Double-checked: another thread may have populated the cache while we
        # were waiting on the lock.
        if _cached_sender is not None:
            return _cached_sender

        if settings.RESEND_API_KEY:
            # lazy import avoids circular dependency with email_sender
            from notifications._resend_sender import ResendSender

            _cached_sender = ResendSender()
            logger.info("email sender resolved: ResendSender")
        else:
            if getattr(settings, "IS_PRODUCTION", False):
                raise RuntimeError("RESEND_API_KEY is required in production but is not set")
            # lazy import avoids circular dependency with email_sender
            from notifications._console_sender import ConsoleSender

            _cached_sender = ConsoleSender()
            logger.info("email sender resolved: ConsoleSender (no RESEND_API_KEY)")
        return _cached_sender


def reset_email_sender_cache() -> None:
    """Test-only helper for clearing the cached sender between tests."""
    global _cached_sender
    with _cache_lock:
        _cached_sender = None
