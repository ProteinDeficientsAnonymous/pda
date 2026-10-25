from typing import TYPE_CHECKING

from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult

if TYPE_CHECKING:
    from community._host_digest import EventDigest


def send_host_digest_email(
    *,
    sender: EmailSender,
    to: str,
    display_name: str,
    events: list["EventDigest"],
    settings_url: str,
) -> SendResult:
    """Render and send one host's daily "what's new on your events" digest."""
    context = {
        "display_name": display_name or "",
        "events": events,
        "settings_url": settings_url,
    }
    html = render_to_string("emails/host_digest.html", context)
    text = render_to_string("emails/host_digest.txt", context)
    return sender.send(to=to, subject="what's new on your events", html=html, text=text)
