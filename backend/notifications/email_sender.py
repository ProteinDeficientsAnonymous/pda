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
        if getattr(settings, "IS_PRODUCTION", False):
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
