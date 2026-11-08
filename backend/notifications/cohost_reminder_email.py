from dataclasses import asdict, dataclass

from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


@dataclass(frozen=True)
class CohostReminderEmailDetails:
    """Recipient + event details for the "add facilitators as co-hosts" host reminder."""

    to: str
    display_name: str
    event_title: str
    event_when: str
    edit_url: str


def send_cohost_reminder_email(
    *,
    sender: EmailSender,
    details: CohostReminderEmailDetails,
) -> SendResult:
    context = asdict(details)
    html = render_to_string("emails/cohost_reminder.html", context)
    text = render_to_string("emails/cohost_reminder.txt", context)
    return sender.send(
        to=details.to,
        subject=f"add co-hosts to {details.event_title.lower()}",
        html=html,
        text=text,
    )
