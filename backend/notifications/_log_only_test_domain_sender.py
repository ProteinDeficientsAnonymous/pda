"""Wrap any EmailSender so seeded test-domain addresses never hit a provider."""

import logging

from notifications.email_sender import (
    TEST_EMAIL_DOMAIN,
    EmailSender,
    SendResult,
    validate_recipient,
)

logger = logging.getLogger("notifications.log_only_test_domain")


def is_log_only_test_recipient(to: str) -> bool:
    return to.strip().lower().endswith(f"@{TEST_EMAIL_DOMAIN}")


class LogOnlyTestDomainSender:
    """Log-and-succeed for ``@{TEST_EMAIL_DOMAIN}``; otherwise delegate."""

    def __init__(self, inner: EmailSender) -> None:
        self.inner = inner

    def send(self, to: str, subject: str, html: str, text: str) -> SendResult:
        if not is_log_only_test_recipient(to):
            return self.inner.send(to=to, subject=subject, html=html, text=text)

        try:
            validate_recipient(to)
        except ValueError as exc:
            return SendResult(success=False, error=str(exc))

        logger.info("EMAIL (test-domain, not sent) to=%s subject=%s", to, subject)
        logger.info("EMAIL text body:\n%s", text)
        return SendResult(success=True)
