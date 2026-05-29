"""Helpers for sending specific transactional emails.

Each helper renders its templates and dispatches via the injected
`EmailSender`. The helpers exist so callers don't have to know template
paths or context shapes — they just say "send a magic-login email."
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


def _validate_recipient(to: str) -> None:
    """Reject malformed recipients and header-injection attempts.

    Newlines/carriage returns in a recipient can be used to inject extra
    headers (BCC, etc.) into the outbound message, so we reject them before
    the address ever reaches the provider.
    """
    if "\n" in to or "\r" in to:
        raise ValueError("recipient address must not contain newlines")
    try:
        validate_email(to)
    except DjangoValidationError as exc:
        raise ValueError(f"invalid recipient address: {to!r}") from exc


def send_magic_login_email(
    *,
    sender: EmailSender,
    to: str,
    display_name: str,
    magic_link_url: str,
) -> SendResult:
    """Render and send the magic-login email."""
    _validate_recipient(to)
    context = {
        "display_name": display_name or "",
        "magic_link_url": magic_link_url,
    }
    html = render_to_string("emails/magic_login.html", context)
    text = render_to_string("emails/magic_login.txt", context)
    return sender.send(
        to=to,
        subject="your pda login link",
        html=html,
        text=text,
    )
