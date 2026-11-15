from dataclasses import asdict, dataclass
from enum import StrEnum

from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


class PlanningEmailVariant(StrEnum):
    PROPOSED = "proposed"
    REMINDER = "reminder"
    UPCOMING = "upcoming"


_PLANNING_SUBJECTS = {
    PlanningEmailVariant.PROPOSED: "can you plan {label}?",
    PlanningEmailVariant.REMINDER: "still need an answer: can you plan {label}?",
    PlanningEmailVariant.UPCOMING: "{label} is coming up",
}


@dataclass(frozen=True)
class PlanningEmailDetails:
    to: str
    display_name: str
    slot_label: str
    planning_url: str
    variant: PlanningEmailVariant


def send_planning_email(
    *,
    sender: EmailSender,
    details: PlanningEmailDetails,
) -> SendResult:
    context = asdict(details)
    html = render_to_string("emails/planning_slot.html", context)
    text = render_to_string("emails/planning_slot.txt", context)
    return sender.send(
        to=details.to,
        subject=_PLANNING_SUBJECTS[details.variant].format(label=details.slot_label),
        html=html,
        text=text,
    )
