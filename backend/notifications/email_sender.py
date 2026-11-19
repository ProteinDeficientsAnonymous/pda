import logging
import threading
from collections.abc import Callable
from enum import StrEnum

from django.conf import settings

from notifications._brevo_sender import BrevoSender
from notifications._console_sender import ConsoleSender
from notifications._resend_sender import ResendSender
from notifications._routing_email_sender import RoutingEmailSender
from notifications.email_types import (
    TEST_EMAIL_DOMAIN,
    EmailSender,
    SendResult,
    mask_recipient,
    validate_recipient,
)

# Re-export the shared contract so existing ``from notifications.email_sender import …``
# call sites keep working.
__all__ = [
    "TEST_EMAIL_DOMAIN",
    "EmailSender",
    "EmailStream",
    "SendResult",
    "get_email_sender",
    "mask_recipient",
    "reset_email_sender_cache",
    "send_best_effort",
    "validate_recipient",
]

logger = logging.getLogger("notifications.email_sender")


def send_best_effort(send: Callable[[], SendResult], log_key: str) -> bool:
    """param(send): performs one send; param(log_key): log action prefix; return(bool): success."""
    try:
        result = send()
    except Exception:  # noqa: BLE001 — one bad send must not abort the caller's batch
        logger.warning(f"{log_key}_send_exception", exc_info=True)
        return False
    if not result.success:
        logger.warning(f"{log_key}_failed", extra={"error": result.error})
    return result.success


class EmailStream(StrEnum):
    TRANSACTIONAL = "transactional"
    BULK = "bulk"


def _resolve_provider(stream: EmailStream) -> EmailSender:
    if stream is EmailStream.TRANSACTIONAL:
        if settings.RESEND_API_KEY:
            return ResendSender()
        if getattr(settings, "IS_PRODUCTION", False):
            raise RuntimeError("RESEND_API_KEY is required in production but is not set")
        return ConsoleSender()

    if settings.BREVO_API_KEY:
        return BrevoSender()
    if getattr(settings, "IS_PRODUCTION", False):
        # Deliberately no Resend fallback: bulk fan-out is what exhausts the
        # transactional allowance, so an unconfigured provider must fail loudly.
        raise RuntimeError("BREVO_API_KEY is required in production but is not set")
    return ConsoleSender()


_cached_senders: dict[EmailStream, EmailSender] = {}
_cache_lock = threading.Lock()


def get_email_sender(stream: EmailStream = EmailStream.TRANSACTIONAL) -> EmailSender:
    """Factory: pick the provider for ``stream``, then wrap in a recipient router.

    Cached per process (thread-safe). The router sends seeded test-domain
    addresses to ConsoleSender and everything else to the resolved provider.
    """
    cached = _cached_senders.get(stream)
    if cached is not None:
        return cached

    with _cache_lock:
        # Double-checked: another thread may have populated the cache while we waited.
        cached = _cached_senders.get(stream)
        if cached is not None:
            return cached

        provider = _resolve_provider(stream)
        sender = RoutingEmailSender(provider=provider, log_only=ConsoleSender())
        _cached_senders[stream] = sender
        logger.info(
            "email sender resolved: stream=%s sender=%s provider=%s",
            stream.value,
            type(sender).__name__,
            type(provider).__name__,
        )
        return sender


def reset_email_sender_cache() -> None:
    """Test-only helper for clearing the cached senders between tests."""
    with _cache_lock:
        _cached_senders.clear()
