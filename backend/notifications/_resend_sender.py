"""Resend transactional email implementation."""

import hashlib
import logging
import time

import resend
from django.conf import settings
from resend.exceptions import RateLimitError, ResendError

from notifications.email_sender import SendResult

logger = logging.getLogger("notifications.resend_sender")

# Bound how long a single send may block. The Resend SDK's default HTTP client
# uses a 30s timeout, which is far too long to hold a request thread for a
# transactional send. We install our own client with a tighter timeout.
_REQUEST_TIMEOUT_SECONDS = 10

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


def _mask_recipient(to: str) -> str:
    """Return a non-reversible, low-cardinality token for log correlation.

    Avoids logging the raw recipient address (PII). We keep only a short hash
    so repeated sends to the same address can be correlated in logs without
    exposing the address itself.
    """
    digest = hashlib.sha256(to.strip().lower().encode("utf-8")).hexdigest()
    return f"sha256:{digest[:12]}"


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

    def send(self, to: str, subject: str, html: str, text: str) -> SendResult:
        params = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
            "text": text,
        }
        masked = _mask_recipient(to)
        last_error: Exception | None = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = resend.Emails.send(params)
                # SendResponse is a dict subclass; access id via .get() for safety
                message_id = response.get("id") if isinstance(response, dict) else None
                logger.info(
                    "resend_send_success subject=%s message_id=%s recipient=%s attempt=%d",
                    subject,
                    message_id,
                    masked,
                    attempt,
                )
                return SendResult(success=True, provider_message_id=message_id)
            except ResendError as exc:
                last_error = exc
                if attempt < _MAX_ATTEMPTS and _is_retryable(exc):
                    backoff = _BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                    logger.warning(
                        "resend_send_retry subject=%s recipient=%s attempt=%d code=%s",
                        subject,
                        masked,
                        attempt,
                        getattr(exc, "code", "?"),
                    )
                    time.sleep(backoff)
                    continue
                break
            except Exception as exc:  # noqa: BLE001 — never let a send 500 a public endpoint
                last_error = exc
                break

        logger.warning(
            "resend_send_failure subject=%s recipient=%s attempts=%d",
            subject,
            masked,
            _MAX_ATTEMPTS,
        )
        return SendResult(success=False, error=str(last_error))
