"""Dev/test fallback that logs emails instead of sending them."""

import logging

from notifications.email_types import (
    BatchSendResult,
    SendResult,
    mask_recipient,
    validate_recipient,
)

logger = logging.getLogger("notifications.console_sender")


class ConsoleSender:
    """Logs the email and returns success. Use in dev and tests."""

    def send(self, to: str, subject: str, html: str, text: str) -> SendResult:
        validate_recipient(to)
        logger.info("EMAIL to=%s subject=%s", to, subject)
        logger.info("EMAIL text body:\n%s", text)
        return SendResult(success=True)

    def send_batch(
        self, recipients: list[str], subject: str, html: str, text: str
    ) -> BatchSendResult:
        for recipient in recipients:
            validate_recipient(recipient)
            logger.info("EMAIL to=%s subject=%s", mask_recipient(recipient), subject)
        return BatchSendResult(accepted=len(recipients))
