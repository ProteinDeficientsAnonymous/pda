from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


def send_event_feedback_email(  # noqa: PLR0913
    *,
    sender: EmailSender,
    to: str,
    display_name: str,
    event_title: str,
    event_date: str | None,
    url: str,
    reminder: bool,
) -> SendResult:
    """Render and send the post-event feedback request (or its single reminder)."""
    name = "event_feedback_reminder" if reminder else "event_feedback_request"
    context = {
        "display_name": display_name or "",
        "event_title": event_title,
        "event_date": event_date or "",
        "url": url,
    }
    html = render_to_string(f"emails/{name}.html", context)
    text = render_to_string(f"emails/{name}.txt", context)
    title = event_title.lower()
    subject = f"still keen to hear about {title}" if reminder else f"how was {title}?"
    return sender.send(to=to, subject=subject, html=html, text=text)
