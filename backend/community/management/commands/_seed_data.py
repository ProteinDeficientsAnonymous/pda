"""Static seed data (dataclasses + constants) for the `seed` command."""

from dataclasses import dataclass, field

from community.models import JoinRequestStatus
from community.models.choices import (
    AttendanceStatus,
    EventType,
    JoinFormQuestionType,
    RSVPStatus,
)

PASSWORD = "testpass123"


@dataclass
class SeedUser:
    phone_number: str
    first_name: str
    is_superuser: bool
    last_name: str = ""
    email: str = ""
    bio: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


@dataclass
class SeedEvent:
    title: str
    description: str
    delta_days: int
    duration_hours: float
    location: str
    event_type: str = EventType.COMMUNITY
    rsvp_enabled: bool = False
    allow_plus_ones: bool = False
    max_attendees: int | None = None


@dataclass
class SeedNonMember:
    phone_number: str
    first_name: str
    last_name: str = ""
    email: str = ""


@dataclass
class SeedRSVP:
    """An RSVP to seed, keyed by event title + seed-user phone number.

    `attendance` only applies to attending RSVPs on a past / in-check-in-window
    event — mirroring the API, which rejects attendance on non-attending RSVPs.
    """

    event_title: str
    phone_number: str
    status: str
    has_plus_one: bool = False
    attendance: str = AttendanceStatus.UNKNOWN


@dataclass
class SeedJoinRequest:
    first_name: str
    phone_number: str
    answers: dict[str, str]
    status: str
    last_name: str = ""
    decided_days_ago: int | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


@dataclass
class SeedJoinFormQuestion:
    label: str
    field_type: str = JoinFormQuestionType.TEXT
    required: bool = True
    options: list[str] = field(default_factory=list)
    display_order: int = 0


SEED_USERS = [
    SeedUser(
        phone_number="+17025550001",
        first_name="Seed",
        last_name="Admin",
        is_superuser=True,
        email="admin@pda.test",
        bio="org admin — ping me if anything's broken 🌿",
    ),
    SeedUser(
        phone_number="+17025550002",
        first_name="Seed",
        last_name="Member",
        is_superuser=False,
        email="member@pda.test",
        bio="vegan six years, big into potlucks and mutual aid.",
    ),
    SeedUser(
        phone_number="+17025550003",
        first_name="Jamie",
        last_name="Okafor",
        is_superuser=False,
        email="jamie@pda.test",
        bio="food not bombs volunteer. cook, eat, organize.",
    ),
    SeedUser(
        phone_number="+17025550004",
        first_name="Rin",
        last_name="Takahashi",
        is_superuser=False,
        email="rin@pda.test",
    ),
    SeedUser(
        phone_number="+17025550005",
        first_name="Ash",
        last_name="Morales",
        is_superuser=False,
        email="ash@pda.test",
        bio="plant-based chef, always down to swap recipes.",
    ),
]

SEED_JOIN_FORM_QUESTIONS = [
    SeedJoinFormQuestion(
        label="Why do you want to join?",
        field_type=JoinFormQuestionType.TEXT,
        required=True,
        display_order=0,
    ),
    SeedJoinFormQuestion(
        label="How did you hear about us?",
        field_type=JoinFormQuestionType.TEXT,
        required=False,
        display_order=1,
    ),
    SeedJoinFormQuestion(
        label="What are your pronouns?",
        field_type=JoinFormQuestionType.TEXT,
        required=False,
        display_order=2,
    ),
]

SEED_EVENTS = [
    # Capacity-limited so the "event is full", waitlist, and FIFO-promotion UI
    # have data. max_attendees=3 is filled exactly by an attending +1 below.
    SeedEvent(
        title="Vegan Potluck",
        description="Bring your favourite dish to share!",
        delta_days=7,
        duration_hours=3,
        location="Community Center",
        event_type=EventType.COMMUNITY,
        rsvp_enabled=True,
        allow_plus_ones=True,
        max_attendees=3,
    ),
    SeedEvent(
        title="Plant-Based Cooking Workshop",
        description="Learn to make tofu scramble, cashew cheese, and more.",
        delta_days=14,
        duration_hours=2,
        location="Kitchen Lab",
        event_type=EventType.OFFICIAL,
        rsvp_enabled=True,
        allow_plus_ones=True,
    ),
    SeedEvent(
        title="Movie Night",
        description="Documentary screening followed by group discussion.",
        delta_days=21,
        duration_hours=2.5,
        location="Living Room",
        event_type=EventType.COMMUNITY,
    ),
    # Past + check-in closed so attendance (attended / no_show) can be marked and
    # the host stats panel renders populated.
    SeedEvent(
        title="Past Potluck (seed)",
        description="Last month's potluck — great turnout!",
        delta_days=-30,
        duration_hours=3,
        location="Community Center",
        event_type=EventType.COMMUNITY,
        rsvp_enabled=True,
        allow_plus_ones=True,
    ),
    SeedEvent(
        title="Past Club Meetup (seed)",
        description="Last cycle's club meetup.",
        delta_days=-14,
        duration_hours=2,
        location="Back Room",
        event_type=EventType.CLUB,
        rsvp_enabled=True,
    ),
]

# Seed-user phone numbers (mirror SEED_USERS) referenced by SEED_RSVPS.
_ADMIN = "+17025550001"
_MEMBER = "+17025550002"
_JAMIE = "+17025550003"
_RIN = "+17025550004"
_ASH = "+17025550005"

# Non-member (join-request applicant) phone numbers, referenced by SEED_RSVPS
# and SEED_JOIN_REQUESTS so the join-requests list has applicants across a
# spread of engagement states — attended, upcoming, and neither — instead of
# every request looking identically brand-new.
_PRIYA_NON_MEMBER = "+17025550013"
_RILEY_NON_MEMBER = "+17025550015"
_TAYLOR_NON_MEMBER = "+17025550016"

SEED_NON_MEMBERS = [
    SeedNonMember(
        phone_number=_PRIYA_NON_MEMBER,
        first_name="Priya",
        last_name="Raghavendra-Nakamura",
        email="priya.rn@example.com",
    ),
    SeedNonMember(
        phone_number=_RILEY_NON_MEMBER,
        first_name="Riley",
        last_name="Okonkwo-Vasquez",
        email="riley.ov@example.com",
    ),
    SeedNonMember(
        phone_number=_TAYLOR_NON_MEMBER,
        first_name="Taylor",
        last_name="Kim",
        email="taylor.kim@example.com",
    ),
]

SEED_RSVPS = [
    # Vegan Potluck — max_attendees=3. Admin +1 (2 spots) and Member (1 spot)
    # fill it, so the rest sit on the FIFO waitlist (ordered by insertion below).
    SeedRSVP("Vegan Potluck", _ADMIN, RSVPStatus.ATTENDING, has_plus_one=True),
    SeedRSVP("Vegan Potluck", _MEMBER, RSVPStatus.ATTENDING),
    SeedRSVP("Vegan Potluck", _JAMIE, RSVPStatus.WAITLISTED),
    SeedRSVP("Vegan Potluck", _RIN, RSVPStatus.WAITLISTED),
    SeedRSVP("Vegan Potluck", _ASH, RSVPStatus.MAYBE),
    # Plant-Based Cooking Workshop — uncapped, mixed statuses.
    SeedRSVP("Plant-Based Cooking Workshop", _MEMBER, RSVPStatus.ATTENDING, has_plus_one=True),
    SeedRSVP("Plant-Based Cooking Workshop", _JAMIE, RSVPStatus.ATTENDING),
    SeedRSVP("Plant-Based Cooking Workshop", _RIN, RSVPStatus.MAYBE),
    SeedRSVP("Plant-Based Cooking Workshop", _ASH, RSVPStatus.CANT_GO),
    # Past Potluck — attendance marked (attended / no_show) on attending RSVPs.
    SeedRSVP(
        "Past Potluck (seed)",
        _ADMIN,
        RSVPStatus.ATTENDING,
        has_plus_one=True,
        attendance=AttendanceStatus.ATTENDED,
    ),
    SeedRSVP(
        "Past Potluck (seed)",
        _MEMBER,
        RSVPStatus.ATTENDING,
        attendance=AttendanceStatus.ATTENDED,
    ),
    SeedRSVP(
        "Past Potluck (seed)",
        _JAMIE,
        RSVPStatus.ATTENDING,
        attendance=AttendanceStatus.NO_SHOW,
    ),
    SeedRSVP("Past Potluck (seed)", _RIN, RSVPStatus.MAYBE),
    SeedRSVP("Past Potluck (seed)", _ASH, RSVPStatus.CANT_GO),
    # Non-member applicants (see SEED_NON_MEMBERS, SEED_JOIN_REQUESTS) spread
    # across engagement states, so the join-requests list isn't uniformly blank:
    # Priya attended once (community); Riley attended a club meetup and has an
    # upcoming official rsvp; Taylor has only ever rsvp'd, never attended.
    SeedRSVP(
        "Past Potluck (seed)",
        _PRIYA_NON_MEMBER,
        RSVPStatus.ATTENDING,
        attendance=AttendanceStatus.ATTENDED,
    ),
    SeedRSVP(
        "Past Club Meetup (seed)",
        _RILEY_NON_MEMBER,
        RSVPStatus.ATTENDING,
        attendance=AttendanceStatus.ATTENDED,
    ),
    SeedRSVP("Plant-Based Cooking Workshop", _RILEY_NON_MEMBER, RSVPStatus.ATTENDING),
    SeedRSVP("Plant-Based Cooking Workshop", _TAYLOR_NON_MEMBER, RSVPStatus.ATTENDING),
]

SEED_HOME_PAGE = {
    "content_html": "<p>This is seed text for the home page.</p>",
}

SEED_GUIDELINES = {
    "content_html": "<p>This is seed text for the guidelines page.</p>",
}

SEED_FAQ = {
    "content_html": "<p>This is seed text for the FAQ page.</p>",
}

SEED_JOIN_REQUESTS = [
    SeedJoinRequest(
        first_name="Alex",
        last_name="Rivera",
        phone_number="+17025550010",
        answers={
            "Why do you want to join?": "I've been vegan for two years and want to connect with community.",
            "How did you hear about us?": "A friend told me about PDA.",
        },
        status=JoinRequestStatus.PENDING,
    ),
    SeedJoinRequest(
        first_name="Jordan",
        last_name="Chen",
        phone_number="+17025550011",
        answers={
            "Why do you want to join?": "Looking for local vegan friends and events.",
            "What are your pronouns?": "they/them",
        },
        status=JoinRequestStatus.APPROVED,
        decided_days_ago=5,
    ),
    SeedJoinRequest(
        first_name="Sam",
        last_name="Taylor",
        phone_number="+17025550012",
        answers={
            "Why do you want to join?": "Curious about veganism.",
        },
        status=JoinRequestStatus.REJECTED,
        decided_days_ago=3,
    ),
    SeedJoinRequest(
        first_name="Priya",
        last_name="Raghavendra-Nakamura",
        phone_number=_PRIYA_NON_MEMBER,
        answers={
            "Why do you want to join?": (
                "i've been plant-based for about six months and am finally ready to find my people. "
                "looking for folks to cook with, share resources, and organize around animal liberation "
                "and broader collective liberation work."
            ),
            "How did you hear about us?": "saw a flyer at the co-op on grand ave.",
            "What are your pronouns?": "she/they",
        },
        status=JoinRequestStatus.PENDING,
    ),
    SeedJoinRequest(
        first_name="Mo",
        phone_number="+442079460958",
        answers={
            "Why do you want to join?": "moving to the area next month and want to plug in before i arrive.",
            "What are your pronouns?": "he/him",
        },
        status=JoinRequestStatus.PENDING,
    ),
    SeedJoinRequest(
        first_name="Riley",
        last_name="Okonkwo-Vasquez",
        phone_number=_RILEY_NON_MEMBER,
        answers={
            "Why do you want to join?": "food not bombs volunteer, interested in mutual aid + vegan outreach.",
            "How did you hear about us?": "instagram — pda showed up in a story reshare.",
        },
        status=JoinRequestStatus.PENDING,
    ),
    SeedJoinRequest(
        first_name="Taylor",
        last_name="Kim",
        phone_number=_TAYLOR_NON_MEMBER,
        answers={
            "Why do you want to join?": "just curious — not vegan yet but open to learning.",
        },
        status=JoinRequestStatus.PENDING,
    ),
    SeedJoinRequest(
        first_name="Devon",
        last_name="Alvarez",
        phone_number="+17025550017",
        answers={
            "Why do you want to join?": "longtime abolitionist looking for aligned community.",
            "How did you hear about us?": "word of mouth at a local protest.",
            "What are your pronouns?": "they/them",
        },
        status=JoinRequestStatus.APPROVED,
        decided_days_ago=1,
    ),
]
