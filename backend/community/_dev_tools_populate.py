import secrets
from dataclasses import dataclass

from users.models import User

from community._dev_tools_content import pick_question_templates, random_answer
from community.models import EventCoHostInvite, EventRSVP, EventRsvpQuestion, RSVPStatus
from community.models.choices import CoHostInviteStatus


@dataclass
class RsvpCounts:
    going: int
    non_member_going: int
    maybe: int
    cant_go: int
    waitlisted: int
    max_attendees: int | None


FILLER_PHONE_PREFIX = "+1555"

_FIRST_NAMES = [
    "Avery",
    "Blair",
    "Cameron",
    "Dakota",
    "Emerson",
    "Finley",
    "Harper",
    "Indigo",
    "Jules",
    "Kai",
    "Logan",
    "Marlowe",
    "Nico",
    "Oakley",
    "Parker",
    "Quinn",
    "Reese",
    "Sage",
    "Tatum",
    "Wren",
]
_LAST_NAMES = [
    "Abara",
    "Bergstrom",
    "Castellanos",
    "Dionne",
    "Ekwueme",
    "Fontaine",
    "Grabowski",
    "Halvorsen",
    "Iwasaki",
    "Jarvi",
    "Kowalczyk",
    "Lindqvist",
    "Moreno",
    "Njoku",
    "Okonkwo",
    "Petrosyan",
    "Quintero",
    "Rasmussen",
    "Sundaram",
    "Vasquez",
]


def _random_name() -> tuple[str, str]:
    return secrets.choice(_FIRST_NAMES), secrets.choice(_LAST_NAMES)


def _create_filler_user(*, is_member: bool) -> User:
    first_name, last_name = _random_name()
    phone_number = f"{FILLER_PHONE_PREFIX}{secrets.randbelow(10**7):07d}"
    return User.objects.create_user(
        phone_number=phone_number,
        first_name=first_name,
        last_name=last_name,
        is_member=is_member,
    )


def pick_filler_users(count: int, *, is_member: bool, exclude_ids: set) -> list[User]:
    pool = list(User.objects.filter(is_member=is_member).exclude(id__in=exclude_ids)[: count * 2])
    picked: list[User] = []
    for _ in range(count):
        if pool:
            user = pool.pop(secrets.randbelow(len(pool)))
        else:
            user = _create_filler_user(is_member=is_member)
        picked.append(user)
        exclude_ids.add(user.id)
    return picked


def populate_cohosts(event, *, accepted_count: int, invited_count: int, invited_by) -> None:
    exclude_ids = {event.created_by_id} if event.created_by_id else set()
    accepted = pick_filler_users(accepted_count, is_member=True, exclude_ids=exclude_ids)
    event.co_hosts.add(*accepted)

    invited = pick_filler_users(invited_count, is_member=True, exclude_ids=exclude_ids)
    EventCoHostInvite.objects.bulk_create(
        [
            EventCoHostInvite(
                event=event,
                user=user,
                invited_by=invited_by,
                status=CoHostInviteStatus.PENDING,
            )
            for user in invited
        ]
    )


def _split_by_capacity(going: int, max_attendees: int | None) -> tuple[int, int]:
    """Returns (attending, waitlisted), mirroring _apply_rsvp_in_transaction."""
    if max_attendees is not None and going > max_attendees:
        return max_attendees, going - max_attendees
    return going, 0


def populate_rsvps(event, counts: RsvpCounts) -> None:
    exclude_ids = {event.created_by_id} if event.created_by_id else set()
    total_going = counts.going + counts.non_member_going
    attending_total, waitlisted_total = _split_by_capacity(total_going, counts.max_attendees)
    non_member_attending = min(counts.non_member_going, attending_total)
    non_member_waitlisted = counts.non_member_going - non_member_attending
    member_attending = attending_total - non_member_attending
    member_waitlisted = waitlisted_total - non_member_waitlisted

    rows = []
    member_counts = {
        RSVPStatus.ATTENDING: member_attending,
        RSVPStatus.WAITLISTED: member_waitlisted + counts.waitlisted,
        RSVPStatus.MAYBE: counts.maybe,
        RSVPStatus.CANT_GO: counts.cant_go,
    }
    for status, count in member_counts.items():
        for user in pick_filler_users(count, is_member=True, exclude_ids=exclude_ids):
            rows.append(EventRSVP(event=event, user=user, status=status))

    non_member_counts = {
        RSVPStatus.ATTENDING: non_member_attending,
        RSVPStatus.WAITLISTED: non_member_waitlisted,
    }
    for status, count in non_member_counts.items():
        for user in pick_filler_users(count, is_member=False, exclude_ids=exclude_ids):
            rows.append(EventRSVP(event=event, user=user, status=status))

    # bulk_create skips EventRSVP.save(), which normally assigns waitlist positions.
    waitlisted_rows = [row for row in rows if row.status == RSVPStatus.WAITLISTED]
    for position, row in enumerate(waitlisted_rows, start=1):
        row.waitlist_position = position

    EventRSVP.objects.bulk_create(rows)


def populate_invited_users(event, *, count: int) -> None:
    exclude_ids = {event.created_by_id} if event.created_by_id else set()
    exclude_ids |= set(event.rsvps.values_list("user_id", flat=True))
    users = pick_filler_users(count, is_member=True, exclude_ids=exclude_ids)
    event.invited_users.add(*users)


def populate_rsvp_questions(event, *, required_count: int, optional_count: int) -> None:
    """Going + waitlisted guests answer every required question and ~half the optional ones."""
    total = required_count + optional_count
    if total == 0:
        return
    required_flags = [True] * required_count + [False] * optional_count
    secrets.SystemRandom().shuffle(required_flags)
    templates = pick_question_templates(total)
    questions = EventRsvpQuestion.objects.bulk_create(
        [
            EventRsvpQuestion(
                event=event,
                label=template.label,
                field_type=template.field_type,
                options=list(template.options),
                required=required,
                display_order=order,
            )
            for order, (template, required) in enumerate(
                zip(templates, required_flags, strict=True)
            )
        ]
    )

    rsvps = list(event.rsvps.filter(status__in=[RSVPStatus.ATTENDING, RSVPStatus.WAITLISTED]))
    for rsvp in rsvps:
        rsvp.questionnaire_responses = {
            str(question.id): {"label": question.label, "answer": random_answer(template)}
            for question, template in zip(questions, templates, strict=True)
            if question.required or secrets.randbelow(2)
        }
    EventRSVP.objects.bulk_update(rsvps, ["questionnaire_responses"])
