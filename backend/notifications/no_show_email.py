from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


def send_no_show_email(  # noqa: PLR0913
    *,
    sender: EmailSender,
    to: str,
    display_name: str,
    event_title: str,
    event_date: str | None,
    calendar_url: str,
) -> SendResult:
    """Render and send the notice to a member marked didn't go at an event."""
    context = {
        "display_name": display_name or "",
        "event_title": event_title,
        "event_date": event_date or "",
        "calendar_url": calendar_url,
    }
    html = render_to_string("emails/no_show.html", context)
    text = render_to_string("emails/no_show.txt", context)
    return sender.send(
        to=to, subject=f"we missed you at {event_title.lower()}", html=html, text=text
    )
