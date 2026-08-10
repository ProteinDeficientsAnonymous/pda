from dataclasses import dataclass, field
from datetime import timedelta

from django.utils import timezone
from users.models import User
from users.roles import Role

from community.models import Event, EventRSVP, EventRsvpQuestion, EventType, PageVisibility


@dataclass
class SeedEvent:
    title: str
    description: str
    delta_days: int
    duration_hours: float
    location: str
    event_type: str = EventType.COMMUNITY
    visibility: str = PageVisibility.PUBLIC
    rsvp_enabled: bool = False
    allow_plus_ones: bool = False
    max_attendees: int | None = None


@dataclass
class SeedRsvpQuestion:
    label: str
    field_type: str
    options: list[str] = field(default_factory=list)
    required: bool = False
    display_order: int = 0


def seed_events(stdout, events: list[SeedEvent], created_by: User | None) -> dict[str, Event]:
    """Seed events. Returns a title -> Event mapping."""
    now = timezone.now()
    result: dict[str, Event] = {}
    for data in events:
        start = now + timedelta(days=data.delta_days)
        end = start + timedelta(hours=data.duration_hours)
        event, created = Event.objects.get_or_create(
            title=data.title,
            defaults={
                "description": data.description,
                "start_datetime": start,
                "end_datetime": end,
                "location": data.location,
                "event_type": data.event_type,
                "visibility": data.visibility,
                "rsvp_enabled": data.rsvp_enabled,
                "allow_plus_ones": data.allow_plus_ones,
                "max_attendees": data.max_attendees,
                "created_by": created_by,
            },
        )
        result[data.title] = event
        stdout.write(f"  {'created' if created else 'exists'} event: {data.title}")
    return result


def get_or_create_seed_user(
    phone_number: str, password: str, defaults: dict, roles: list[Role]
) -> tuple[User, bool]:
    """get_or_create by phone, set password + roles on creation. Returns (user, created)."""
    user, created = User.objects.get_or_create(phone_number=phone_number, defaults=defaults)
    if created:
        user.set_password(password)
        user.save(update_fields=["password"])
        user.roles.set(roles)
    return user, created


def apply_rsvp(event: Event, user: User, defaults: dict, *, overwrite: bool = False) -> None:
    """Seed one RSVP row directly (bypassing capacity rules) so seeded statuses land verbatim."""
    if overwrite:
        EventRSVP.objects.update_or_create(event=event, user=user, defaults=defaults)
    else:
        EventRSVP.objects.get_or_create(event=event, user=user, defaults=defaults)


def _sync_seed_rsvp_question(question: EventRsvpQuestion, data: SeedRsvpQuestion) -> None:
    updates: list[str] = []
    for attr in ("field_type", "options", "required", "display_order"):
        value = getattr(data, attr)
        if getattr(question, attr) != value:
            setattr(question, attr, value)
            updates.append(attr)
    if updates:
        question.save(update_fields=updates)


def seed_event_rsvp_questions(
    stdout, event: Event, specs: list[SeedRsvpQuestion]
) -> dict[str, EventRsvpQuestion]:
    """Ensure RSVP questions exist on an event. Returns label→question mapping."""
    questions: dict[str, EventRsvpQuestion] = {}
    for data in specs:
        question, created = EventRsvpQuestion.objects.get_or_create(
            event=event,
            label=data.label,
            defaults={
                "field_type": data.field_type,
                "options": data.options,
                "required": data.required,
                "display_order": data.display_order,
            },
        )
        if not created:
            _sync_seed_rsvp_question(question, data)
        stdout.write(
            f"  {'created' if created else 'exists'} rsvp question: {event.title} / {question.label}"
        )
        questions[question.label] = question
    return questions


def questionnaire_snapshot(
    questions_by_label: dict[str, EventRsvpQuestion], answers: dict[str, str]
) -> dict:
    """Build {question_id: {label, answer}} from explicit label→answer pairs."""
    return {
        str(questions_by_label[label].id): {"label": label, "answer": answer}
        for label, answer in answers.items()
    }
