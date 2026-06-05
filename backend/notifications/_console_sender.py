"""Dev/test fallback that logs emails instead of sending them."""

import logging

from notifications.email_sender import SendResult, validate_recipient

logger = logging.getLogger("notifications.console_sender")


class ConsoleSender:
    """Logs the email and returns success. Use in dev and tests."""

    def send(self, to: str, subject: str, html: str, text: str) -> SendResult:
        validate_recipient(to)
        logger.info("EMAIL to=%s subject=%s", to, subject)
        logger.info("EMAIL text body:\n%s", text)
        return SendResult(success=True)
