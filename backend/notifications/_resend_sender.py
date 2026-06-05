"""Resend transactional email implementation."""

import logging
import time

import resend
from django.conf import settings
from resend.exceptions import RateLimitError, ResendError

from notifications.email_sender import SendResult, mask_recipient, validate_recipient

logger = logging.getLogger("notifications.resend_sender")

# Bound how long a single send may block. The Resend SDK's default HTTP client
# uses a 30s timeout, which is far too long to hold a request thread for a
# transactional send. We install our own client with a tighter timeout.
#
# The send runs INLINE in the request/response cycle (request_login_link), so
# the worst-case time the worker thread can block is bounded by:
#   _MAX_ATTEMPTS * _REQUEST_TIMEOUT_SECONDS  (network/timeout)
#   + sum of backoff sleeps between attempts.
# Keep both small so a Resend outage degrades latency gracefully (and falls back
# to the admin-notification path) instead of exhausting the worker pool.
_REQUEST_TIMEOUT_SECONDS = 4

# Bounded retry for transient failures (network errors, 5xx, 429). Hand-rolled
# to avoid pulling in a retry dependency.
_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 0.5

# HTTP status codes (as strings, matching ResendError.code) worth retrying.
_RETRYABLE_CODES = {"429", "500", "502", "503", "504"}


def _is_retryable(exc: ResendError) -> bool:
    """Return True for transient Resend failures worth retrying.

    The SDK wraps all transport-level failures (network/timeout) into a
    ResendError with error_type "HttpClientError", and surfaces 5xx/429 as
    ResendError subclasses. We retry those; client errors (4xx other than 429)
    are not retried.
    """
    if isinstance(exc, RateLimitError):
        return True
    if getattr(exc, "error_type", None) == "HttpClientError":
        return True
    return str(getattr(exc, "code", "")) in _RETRYABLE_CODES


class ResendSender:
    """Sends transactional emails via Resend's HTTP API.

    Uses the official `resend` SDK with an explicit request timeout and a
    bounded retry/backoff for transient failures. The API key is read at
    instantiation so callers can stub it via Django settings overrides in tests.

    Callers must inspect ``SendResult.success`` to determine whether the send
    succeeded — a failed send never raises.
    """

    def __init__(self) -> None:
        resend.api_key = settings.RESEND_API_KEY
        # Install an HTTP client with a bounded timeout. The default client
        # holds a request thread for up to 30s on a hung connection.
        resend.default_http_client = resend.RequestsClient(timeout=_REQUEST_TIMEOUT_SECONDS)

    def _attempt_send(self, params: dict, masked: str, attempt: int) -> SendResult:
        """Perform a single send and log success.

        Never catches — the caller owns the retry/error policy. Returns a
        successful SendResult; on failure the underlying exception propagates.
        """
        response = resend.Emails.send(params)
        # SendResponse is a dict subclass; access id via .get() for safety
        message_id = response.get("id") if isinstance(response, dict) else None
        logger.info(
            "resend_send_success subject=%s message_id=%s recipient=%s attempt=%d",
            params["subject"],
            message_id,
            masked,
            attempt,
        )
        return SendResult(success=True, provider_message_id=message_id)

    def _backoff(self, exc: ResendError, masked: str, subject: str, attempt: int) -> None:
        """Log a retry and sleep with exponential backoff before the next attempt."""
        logger.warning(
            "resend_send_retry subject=%s recipient=%s attempt=%d code=%s",
            subject,
            masked,
            attempt,
            getattr(exc, "code", "?"),
        )
        time.sleep(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    def send(self, to: str, subject: str, html: str, text: str) -> SendResult:
        validate_recipient(to)
        params = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
            "text": text,
        }
        masked = mask_recipient(to)
        last_error: Exception | None = None
        attempt = 0

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return self._attempt_send(params, masked, attempt)
            except ResendError as exc:
                last_error = exc
                if attempt < _MAX_ATTEMPTS and _is_retryable(exc):
                    self._backoff(exc, masked, subject, attempt)
                    continue
                break
            except Exception as exc:  # noqa: BLE001 — never let a send 500 a public endpoint
                last_error = exc
                break

        # Report the true number of attempts (a non-retryable error breaks after
        # one), and attach the traceback so unexpected (non-ResendError) failures
        # stay debuggable.
        logger.warning(
            "resend_send_failure subject=%s recipient=%s attempts=%d",
            subject,
            masked,
            attempt,
            exc_info=last_error,
        )
        return SendResult(success=False, error=str(last_error))
