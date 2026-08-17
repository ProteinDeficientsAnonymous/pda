"""Brevo bulk email implementation."""

import logging
import time

import httpx
from django.conf import settings

from notifications.email_sender import SendResult, mask_recipient, validate_recipient

logger = logging.getLogger("notifications.brevo_sender")

_API_URL = "https://api.brevo.com/v3/smtp/email"

# Bulk sends run from the weekly-digest cron or in a loop behind an admin-only
# blast endpoint, so a longer ceiling than the transactional path is fine.
_REQUEST_TIMEOUT_SECONDS = 10

_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 0.5

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class _RetryableBrevoError(Exception):
    """Transient Brevo failure (transport error, 429, or 5xx) worth another attempt."""


class _BrevoApiError(Exception):
    """Non-retryable Brevo API error (4xx other than 429)."""


def _response_code(response: httpx.Response) -> str:
    """Return Brevo's error code only — its free-text message can echo the recipient."""
    try:
        body = response.json()
    except ValueError:
        return ""
    return str(body.get("code", "")) if isinstance(body, dict) else ""


def _message_id(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    return body.get("messageId") if isinstance(body, dict) else None


class BrevoSender:
    """Sends bulk email via Brevo's HTTP API; one pooled client per process.

    Brevo exposes no idempotency key here, so a retry after a queued-then-5xx'd
    send can duplicate it — retries stay bounded for that reason.
    """

    def __init__(self) -> None:
        self._client = httpx.Client(
            timeout=_REQUEST_TIMEOUT_SECONDS,
            headers={
                "api-key": settings.BREVO_API_KEY,
                "accept": "application/json",
                "content-type": "application/json",
            },
        )

    def _payload(self, to: str, subject: str, html: str, text: str) -> dict:
        sender: dict[str, str] = {"email": settings.BREVO_FROM_EMAIL}
        if settings.BREVO_FROM_NAME:
            sender["name"] = settings.BREVO_FROM_NAME
        return {
            "sender": sender,
            "to": [{"email": to}],
            "subject": subject,
            "htmlContent": html,
            "textContent": text,
        }

    def _attempt_send(self, payload: dict, masked: str, subject: str, attempt: int) -> SendResult:
        """Perform a single send; raises for the caller's retry policy to classify."""
        try:
            response = self._client.post(_API_URL, json=payload)
        except httpx.HTTPError as exc:
            raise _RetryableBrevoError(f"transport error: {type(exc).__name__}") from exc

        if response.status_code in _RETRYABLE_STATUS_CODES:
            raise _RetryableBrevoError(
                f"http {response.status_code} code={_response_code(response)}"
            )
        if response.status_code >= 400:
            raise _BrevoApiError(f"http {response.status_code} code={_response_code(response)}")

        message_id = _message_id(response)
        logger.info(
            "brevo_send_success subject=%s message_id=%s recipient=%s attempt=%d",
            subject,
            message_id,
            masked,
            attempt,
        )
        return SendResult(success=True, provider_message_id=message_id)

    def _backoff(self, exc: Exception, masked: str, subject: str, attempt: int) -> None:
        logger.warning(
            "brevo_send_retry subject=%s recipient=%s attempt=%d error=%s",
            subject,
            masked,
            attempt,
            exc,
        )
        time.sleep(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    def send(self, to: str, subject: str, html: str, text: str) -> SendResult:
        try:
            validate_recipient(to)
        except ValueError as exc:
            logger.warning("brevo_send_failure subject=%s error=invalid_recipient", subject)
            return SendResult(success=False, error=str(exc))

        payload = self._payload(to, subject, html, text)
        masked = mask_recipient(to)
        last_error: Exception | None = None
        attempt = 0

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return self._attempt_send(payload, masked, subject, attempt)
            except _RetryableBrevoError as exc:
                last_error = exc
                if attempt < _MAX_ATTEMPTS:
                    self._backoff(exc, masked, subject, attempt)
                    continue
                break
            except Exception as exc:  # noqa: BLE001 — one bad send must not abort a digest run
                last_error = exc
                break

        logger.warning(
            "brevo_send_failure subject=%s recipient=%s attempts=%d",
            subject,
            masked,
            attempt,
            exc_info=last_error,
        )
        return SendResult(success=False, error=str(last_error))
