from dataclasses import asdict, dataclass

from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


@dataclass(frozen=True)
class EventUnpublishedEmailDetails:
    to: str
    display_name: str
    event_title: str
    event_when: str


def send_event_unpublished_email(
    *,
    sender: EmailSender,
    details: EventUnpublishedEmailDetails,
) -> SendResult:
    context = asdict(details)
    html = render_to_string("emails/event_unpublished.html", context)
    text = render_to_string("emails/event_unpublished.txt", context)
    return sender.send(
        to=details.to,
        subject=f"{details.event_title.lower()} was unpublished",
        html=html,
        text=text,
    )
