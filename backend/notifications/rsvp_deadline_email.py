from dataclasses import asdict, dataclass

from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


@dataclass(frozen=True)
class RsvpDeadlineReminderEmailDetails:
    to: str
    display_name: str
    event_title: str
    deadline: str
    rsvp_url: str


def send_rsvp_deadline_reminder_email(
    *,
    sender: EmailSender,
    details: RsvpDeadlineReminderEmailDetails,
) -> SendResult:
    context = asdict(details)
    html = render_to_string("emails/rsvp_deadline_reminder.html", context)
    text = render_to_string("emails/rsvp_deadline_reminder.txt", context)
    return sender.send(
        to=details.to,
        subject=f"confirm your rsvp to {details.event_title.lower()}",
        html=html,
        text=text,
    )
