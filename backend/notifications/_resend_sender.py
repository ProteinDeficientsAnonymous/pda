"""Resend transactional email implementation."""

import logging

import resend
from django.conf import settings

from notifications.email_sender import SendResult

logger = logging.getLogger("notifications.resend_sender")


class ResendSender:
    """Sends transactional emails via Resend's HTTP API.

    Uses the official `resend` SDK. The API key is read at instantiation
    so callers can stub it via Django settings overrides in tests.

    The broad ``except Exception`` is intentional: the Resend SDK can raise
    multiple exception types (network errors, API errors, validation errors),
    and we never want a single failed send to surface a 500 from a public
    endpoint. Callers must inspect ``SendResult.success`` to determine
    whether the send succeeded.
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
            # SendResponse is a dict subclass; access id via .get() for safety
            message_id = response.get("id") if isinstance(response, dict) else None
            logger.info(
                "resend_send_success to=%s subject=%s message_id=%s",
                to,
                subject,
                message_id,
            )
            return SendResult(success=True, provider_message_id=message_id)
        except Exception as exc:
            logger.exception("resend_send_failure to=%s subject=%s", to, subject)
            return SendResult(success=False, error=str(exc))
