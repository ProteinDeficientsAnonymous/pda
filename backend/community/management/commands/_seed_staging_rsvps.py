"""RSVP fixtures for the `seed_staging` command."""

from dataclasses import dataclass, field

from community.models.choices import AttendanceStatus, RsvpQuestionType, RSVPStatus

from ._seed_shared import SeedRsvpQuestion
from ._seed_staging_data import (
    NON_MEMBER_EVENT_TITLE,
    OFFICIAL_FULL_TITLE,
    OFFICIAL_PAST_TITLE,
    OFFICIAL_TODAY_TITLE,
)

TOKEN_VALID = "valid"
TOKEN_EXPIRED = "expired"
TOKEN_NONE = "none"

_ATTENDED = AttendanceStatus.ATTENDED
_NO_SHOW = AttendanceStatus.DIDNT_GO
_A, _M, _C, _W = RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.CANT_GO, RSVPStatus.WAITLISTED
_TRAVEL_Q = "How are you getting there?"
_NOTES_Q = "Anything we should know?"


@dataclass
class RsvpOnEvent:
    """One RSVP row a seeded user should hold on a named event."""

    event_title: str
    status: str
    attendance: str = AttendanceStatus.UNKNOWN
    answers: dict[str, str] = field(default_factory=dict)


def _rsvps(*rows: tuple) -> list[RsvpOnEvent]:
    """Build RsvpOnEvent rows from (title, status[, attendance][, answers])."""
    result: list[RsvpOnEvent] = []
    for row in rows:
        if row and isinstance(row[-1], dict):
            *head, answers = row
            result.append(RsvpOnEvent(*head, answers=answers))
        else:
            result.append(RsvpOnEvent(*row))
    return result


STAGING_EVENT_RSVP_QUESTIONS: dict[str, list[SeedRsvpQuestion]] = {
    OFFICIAL_TODAY_TITLE: [
        SeedRsvpQuestion(
            _TRAVEL_Q, RsvpQuestionType.SELECT, ["driving", "transit", "bike"], True, 0
        ),
        SeedRsvpQuestion(_NOTES_Q, RsvpQuestionType.TEXTAREA, display_order=1),
    ],
}


@dataclass
class MemberRsvpSpec:
    """RSVPs to attach to the condition member at ``cond_index``."""

    cond_index: int
    rsvps: list[RsvpOnEvent]


# Members across every RSVP state on the official events; the past event carries
# attendance marks so the attendance report shows a non-trivial member/non-member mix.
# OFFICIAL_TODAY also covers questionnaire complete / partial / empty answers.
MEMBER_RSVP_SPECS = [
    MemberRsvpSpec(
        0,
        _rsvps(
            (OFFICIAL_PAST_TITLE, _A, _ATTENDED),
            (
                OFFICIAL_TODAY_TITLE,
                _A,
                {_TRAVEL_Q: "transit", _NOTES_Q: "Bringing a +1 who is gluten-free."},
            ),
        ),
    ),
    MemberRsvpSpec(
        1,
        _rsvps(
            (OFFICIAL_PAST_TITLE, _A, _NO_SHOW),
            (OFFICIAL_TODAY_TITLE, _A, {_TRAVEL_Q: "bike"}),
        ),
    ),
    # Can't-go on today has no questionnaire — questions only apply when going.
    MemberRsvpSpec(2, _rsvps((OFFICIAL_PAST_TITLE, _M), (OFFICIAL_TODAY_TITLE, _C))),
    MemberRsvpSpec(3, _rsvps((OFFICIAL_PAST_TITLE, _A, _ATTENDED), (OFFICIAL_FULL_TITLE, _A))),
    MemberRsvpSpec(4, _rsvps((OFFICIAL_FULL_TITLE, _A))),
    MemberRsvpSpec(5, _rsvps((OFFICIAL_FULL_TITLE, _W))),
]


@dataclass
class NonMemberSpec:
    label: str
    rsvps: list[RsvpOnEvent]
    has_email: bool = True
    token_state: str = TOKEN_VALID


NON_MEMBER_SPECS = [
    NonMemberSpec("attending (valid token, email)", _rsvps((NON_MEMBER_EVENT_TITLE, _A))),
    NonMemberSpec(
        "maybe (valid token, no email)", _rsvps((NON_MEMBER_EVENT_TITLE, _M)), has_email=False
    ),
    NonMemberSpec(
        "can't-go (expired token)",
        _rsvps((NON_MEMBER_EVENT_TITLE, _C)),
        token_state=TOKEN_EXPIRED,
    ),
    NonMemberSpec(
        "multi-event attended (past + today)",
        _rsvps((OFFICIAL_PAST_TITLE, _A, _ATTENDED), (OFFICIAL_TODAY_TITLE, _A)),
    ),
    NonMemberSpec("past no-show (attendance report)", _rsvps((OFFICIAL_PAST_TITLE, _A, _NO_SHOW))),
    NonMemberSpec("waitlisted at capacity", _rsvps((OFFICIAL_FULL_TITLE, _W))),
    NonMemberSpec("no-rsvp (no token)", [], token_state=TOKEN_NONE),
]
