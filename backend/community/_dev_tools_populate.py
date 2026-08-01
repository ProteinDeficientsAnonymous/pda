import secrets
from dataclasses import dataclass

from users.models import User

from community.models import EventCoHostInvite, EventRSVP, RSVPStatus
from community.models.choices import CoHostInviteStatus


@dataclass
class RsvpCounts:
    going: int
    maybe: int
    cant_go: int
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
    """Fill `count` distinct users from the existing pool (members or non-members),
    creating new ones once the pool runs out."""
    pool = list(
        User.objects.filter(is_member=is_member).exclude(id__in=exclude_ids)[: count * 2]
    )
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


def populate_rsvps(event, counts: RsvpCounts, *, allow_non_members: bool) -> None:
    """Fill RSVPs. When `max_attendees` caps `going`, the overflow lands as
    WAITLISTED instead of ATTENDING — mirrors the real capacity-check outcome
    (_apply_rsvp_in_transaction) without going through that endpoint."""
    exclude_ids = {event.created_by_id} if event.created_by_id else set()
    is_member = not allow_non_members

    if counts.max_attendees is not None and counts.going > counts.max_attendees:
        attending_count = counts.max_attendees
        waitlisted_count = counts.going - counts.max_attendees
    else:
        attending_count, waitlisted_count = counts.going, 0

    by_status = {
        RSVPStatus.ATTENDING: attending_count,
        RSVPStatus.WAITLISTED: waitlisted_count,
        RSVPStatus.MAYBE: counts.maybe,
        RSVPStatus.CANT_GO: counts.cant_go,
    }
    rows = []
    for status, count in by_status.items():
        for user in pick_filler_users(count, is_member=is_member, exclude_ids=exclude_ids):
            rows.append(EventRSVP(event=event, user=user, status=status))
    EventRSVP.objects.bulk_create(rows)


def populate_invited_users(event, *, count: int, allow_non_members: bool) -> None:
    exclude_ids = {event.created_by_id} if event.created_by_id else set()
    exclude_ids |= set(event.rsvps.values_list("user_id", flat=True))
    is_member = not allow_non_members
    users = pick_filler_users(count, is_member=is_member, exclude_ids=exclude_ids)
    event.invited_users.add(*users)
