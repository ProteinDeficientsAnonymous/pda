"""Wrap any EmailSender so seeded test-domain addresses never hit a provider."""

from notifications._console_sender import ConsoleSender
from notifications.email_types import TEST_EMAIL_DOMAIN, EmailSender, SendResult


def is_log_only_test_recipient(to: str) -> bool:
    return to.strip().lower().endswith(f"@{TEST_EMAIL_DOMAIN}")


class LogOnlyTestDomainSender:
    """Route ``@{TEST_EMAIL_DOMAIN}`` through ConsoleSender; otherwise delegate."""

    def __init__(self, inner: EmailSender) -> None:
        self.inner = inner
        self._console = ConsoleSender()

    def send(self, to: str, subject: str, html: str, text: str) -> SendResult:
        if is_log_only_test_recipient(to):
            return self._console.send(to=to, subject=subject, html=html, text=text)
        return self.inner.send(to=to, subject=subject, html=html, text=text)
