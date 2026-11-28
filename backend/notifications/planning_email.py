from dataclasses import asdict, dataclass
from enum import StrEnum

from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


class PlanningEmailVariant(StrEnum):
    PROPOSED = "proposed"
    REMINDER = "reminder"
    UPCOMING = "upcoming"
    CONFIRMED = "confirmed"


_PLANNING_SUBJECTS = {
    PlanningEmailVariant.PROPOSED: "can you plan {label}?",
    PlanningEmailVariant.REMINDER: "still need an answer: can you plan {label}?",
    PlanningEmailVariant.UPCOMING: "{label} is coming up: create the event by {due}",
    PlanningEmailVariant.CONFIRMED: "you're planning {label} 🌱",
}

_MAX_NAMED_IN_SUBJECT = 3


def describe_slots(labels: tuple[str, ...]) -> str:
    """return(str): "march", "march and april", "march, april and may", or "5 slots" past three"""
    if len(labels) > _MAX_NAMED_IN_SUBJECT:
        return f"{len(labels)} slots"
    if len(labels) == 1:
        return labels[0]
    return f"{', '.join(labels[:-1])} and {labels[-1]}"


@dataclass(frozen=True)
class PlanningEmailDetails:
    to: str
    display_name: str
    slot_labels: tuple[str, ...]
    planning_url: str
    variant: PlanningEmailVariant
    due_label: str = ""
    announce_label: str = ""


def send_planning_email(
    *,
    sender: EmailSender,
    details: PlanningEmailDetails,
) -> SendResult:
    summary = describe_slots(details.slot_labels)
    context = {**asdict(details), "summary": summary}
    html = render_to_string("emails/planning_slot.html", context)
    text = render_to_string("emails/planning_slot.txt", context)
    return sender.send(
        to=details.to,
        subject=_PLANNING_SUBJECTS[details.variant].format(
            label=summary.lower(), due=details.due_label
        ),
        html=html,
        text=text,
    )


class AvailabilityEmailVariant(StrEnum):
    OPEN = "open"
    REMINDER = "reminder"


_AVAILABILITY_SUBJECTS = {
    AvailabilityEmailVariant.OPEN: "when can you plan in {year}?",
    AvailabilityEmailVariant.REMINDER: "still need your {year} planning availability",
}


@dataclass(frozen=True)
class AvailabilityEmailDetails:
    to: str
    display_name: str
    year: int
    availability_url: str
    variant: AvailabilityEmailVariant


def send_availability_email(
    *, sender: EmailSender, details: AvailabilityEmailDetails
) -> SendResult:
    context = asdict(details)
    return sender.send(
        to=details.to,
        subject=_AVAILABILITY_SUBJECTS[details.variant].format(year=details.year),
        html=render_to_string("emails/planning_availability.html", context),
        text=render_to_string("emails/planning_availability.txt", context),
    )
