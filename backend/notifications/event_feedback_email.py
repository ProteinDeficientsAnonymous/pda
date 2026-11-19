from dataclasses import dataclass

from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


@dataclass(frozen=True)
class EventFeedbackMail:
    display_name: str
    event_title: str
    event_date: str | None
    url: str
    reminder: bool


def send_event_feedback_email(
    *,
    sender: EmailSender,
    to: str,
    mail: EventFeedbackMail,
) -> SendResult:
    """Render and send the post-event feedback request (or its single reminder)."""
    name = "event_feedback_reminder" if mail.reminder else "event_feedback_request"
    context = {
        "display_name": mail.display_name or "",
        "event_title": mail.event_title,
        "event_date": mail.event_date or "",
        "url": mail.url,
    }
    html = render_to_string(f"emails/{name}.html", context)
    text = render_to_string(f"emails/{name}.txt", context)
    title = mail.event_title.lower()
    subject = f"we'd still love to hear about {title}" if mail.reminder else f"how was {title}?"
    return sender.send(to=to, subject=subject, html=html, text=text)
