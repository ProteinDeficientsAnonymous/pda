import secrets
from dataclasses import dataclass

from users.models import User

from community.models import EventCoHostInvite, EventRSVP, RSVPStatus
from community.models.choices import CoHostInviteStatus


@dataclass
class RsvpCounts:
    going: int
    non_member_going: int
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
    """Returns (attending, waitlisted). Overflow past max_attendees waitlists,
    mirroring the real capacity-check outcome (_apply_rsvp_in_transaction)
    without going through that endpoint."""
    if max_attendees is not None and going > max_attendees:
        return max_attendees, going - max_attendees
    return going, 0


def populate_rsvps(event, counts: RsvpCounts) -> None:
    """Fill RSVPs. `non_member_going` draws from a separate non-member pool —
    non-members are RSVP-only, never cohosts or invitees (see
    populate_cohosts/populate_invited_users)."""
    exclude_ids = {event.created_by_id} if event.created_by_id else set()
    total_going = counts.going + counts.non_member_going
    attending_total, waitlisted_total = _split_by_capacity(total_going, counts.max_attendees)
    # Fill non-member going/waitlisted slots first so the member split absorbs
    # any capacity overflow consistently regardless of which pool is larger.
    non_member_attending = min(counts.non_member_going, attending_total)
    non_member_waitlisted = counts.non_member_going - non_member_attending
    member_attending = attending_total - non_member_attending
    member_waitlisted = waitlisted_total - non_member_waitlisted

    rows = []
    member_counts = {
        RSVPStatus.ATTENDING: member_attending,
        RSVPStatus.WAITLISTED: member_waitlisted,
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

    EventRSVP.objects.bulk_create(rows)


def populate_invited_users(event, *, count: int) -> None:
    exclude_ids = {event.created_by_id} if event.created_by_id else set()
    exclude_ids |= set(event.rsvps.values_list("user_id", flat=True))
    users = pick_filler_users(count, is_member=True, exclude_ids=exclude_ids)
    event.invited_users.add(*users)
