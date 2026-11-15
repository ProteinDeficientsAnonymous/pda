from dataclasses import asdict, dataclass

from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


@dataclass(frozen=True)
class RsvpReminderEmailDetails:
    """Recipient + event details for the day-before rsvp reminder."""

    to: str
    display_name: str
    status: str
    event_title: str
    event_when: str
    event_location: str
    rsvp_url: str


def send_rsvp_reminder_email(
    *, sender: EmailSender, details: RsvpReminderEmailDetails
) -> SendResult:
    context = asdict(details)
    html = render_to_string("emails/rsvp_reminder.html", context)
    text = render_to_string("emails/rsvp_reminder.txt", context)
    return sender.send(
        to=details.to,
        subject=f"reminder: {details.event_title.lower()} is tomorrow",
        html=html,
        text=text,
    )
