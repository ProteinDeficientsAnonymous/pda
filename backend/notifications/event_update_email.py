from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


def send_event_update_email(
    *,
    sender: EmailSender,
    to: str,
    display_name: str,
    text: str,
    clubs_without_events: list[str],
) -> SendResult:
    """Send the copy-and-paste event update to one member who posts it."""
    context = {
        "display_name": display_name or "",
        "update_text": text,
        "clubs_without_events": clubs_without_events,
    }
    return sender.send(
        to=to,
        subject="your event update to post",
        html=render_to_string("emails/event_update.html", context),
        text=render_to_string("emails/event_update.txt", context),
    )
