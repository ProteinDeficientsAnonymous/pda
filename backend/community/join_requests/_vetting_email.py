from django.conf import settings
from django.core.mail import send_mail

from community.shared import flatten_to_single_line, logger


def send_vetting_email(subject: str, body: str) -> None:
    """Best-effort email to VETTING_EMAIL; the subject is flattened against header injection."""
    if not settings.VETTING_EMAIL:
        return
    try:
        send_mail(
            subject=flatten_to_single_line(subject),
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL or "noreply@pda.org",
            recipient_list=[settings.VETTING_EMAIL],
        )
    except Exception:
        logger.exception("vetting_email_failed")
