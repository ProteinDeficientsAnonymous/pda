"""Helpers for sending specific transactional emails.

Each helper renders its templates and dispatches via the injected
`EmailSender`. The helpers exist so callers don't have to know template
paths or context shapes — they just say "send a magic-login email."
"""

from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


def send_magic_login_email(
    *,
    sender: EmailSender,
    to: str,
    display_name: str,
    magic_link_url: str,
) -> SendResult:
    """Render and send the magic-login email.

    Recipient validation (RFC-validity + header-injection guard) happens at the
    `EmailSender.send()` boundary, so every email type is protected uniformly.
    """
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


def send_event_blast_email(
    *,
    sender: EmailSender,
    to: str,
    event_title: str,
    subject: str,
    message: str,
) -> SendResult:
    """Render and send one event email-blast message to a single recipient."""
    context = {
        "event_title": event_title,
        "message": message,
    }
    html = render_to_string("emails/event_blast.html", context)
    text = render_to_string("emails/event_blast.txt", context)
    return sender.send(
        to=to,
        subject=subject,
        html=html,
        text=text,
    )
