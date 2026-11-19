"""Route sends by recipient: test-domain → log_only, otherwise → provider."""

from notifications.email_types import TEST_EMAIL_DOMAIN, EmailSender, SendResult


def is_log_only_test_recipient(to: str) -> bool:
    return to.strip().lower().endswith(f"@{TEST_EMAIL_DOMAIN}")


class RoutingEmailSender:
    """Per-recipient router: seeded test addresses never hit the real provider."""

    def __init__(self, provider: EmailSender, log_only: EmailSender) -> None:
        self.provider = provider
        self.log_only = log_only

    def send(self, to: str, subject: str, html: str, text: str) -> SendResult:
        if is_log_only_test_recipient(to):
            return self.log_only.send(to=to, subject=subject, html=html, text=text)
        return self.provider.send(to=to, subject=subject, html=html, text=text)
