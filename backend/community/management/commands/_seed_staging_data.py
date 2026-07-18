"""Static data + pure helpers for the `seed_staging` command."""

from dataclasses import dataclass

from community.models.choices import AttendanceStatus, EventType, JoinRequestStatus, RSVPStatus

from ._seed_shared import SeedEvent

PASSWORD = "testPassword1@"


def perm_phone(index: int) -> str:
    return f"+170255501{index:02d}"


def cond_phone(index: int) -> str:
    return f"+170255502{index:02d}"


def perm_email(key: str) -> str:
    return f"perm.{key}@staging.example"


def cond_email(index: int) -> str:
    return f"cond{index:02d}@staging.example"


def nonmember_phone(index: int) -> str:
    return f"+170255503{index:02d}"


def nonmember_email(index: int) -> str:
    return f"nonmember{index:02d}@staging.example"


def joinreq_phone(index: int) -> str:
    return f"+170255504{index:02d}"


def joinreq_email(index: int) -> str:
    return f"joinreq{index:02d}@staging.example"


NON_MEMBER_EVENT_TITLE = "[staging] official public rsvp demo"

# Official, RSVP-enabled events the attendance + public-RSVP surfaces read from.
OFFICIAL_PAST_TITLE = "[staging] official past attendance-marked"
OFFICIAL_TODAY_TITLE = "[staging] official today rsvp open"
OFFICIAL_FULL_TITLE = "[staging] official over-capacity waitlist"


def condition_combinations() -> list[tuple[bool, bool, bool]]:
    """All 8 (has_email, guidelines_done, sms_done) patterns, fixed order."""
    return [
        (has_email, guidelines_done, sms_done)
        for has_email in (True, False)
        for guidelines_done in (True, False)
        for sms_done in (True, False)
    ]


def condition_label(combo: tuple[bool, bool, bool]) -> str:
    has_email, guidelines_done, sms_done = combo
    parts: list[str] = []
    if not has_email:
        parts.append("no-email")
    if not guidelines_done:
        parts.append("needs-guidelines")
    if not sms_done:
        parts.append("needs-sms")
    return "cond: " + ("complete" if not parts else "+".join(parts))


def is_seed_allowed(env_name: str | None, force: bool) -> bool:
    """Allow local/unset and staging; refuse any other env unless forced."""
    if not env_name or env_name == "staging":
        return True
    return force


STAGING_EVENTS = [
    SeedEvent(
        title="[staging] past potluck",
        description="a wrapped-up community potluck from last month.",
        delta_days=-30,
        duration_hours=3,
        location="community center",
    ),
    SeedEvent(
        title="[staging] last week's film night",
        description="documentary screening and discussion.",
        delta_days=-7,
        duration_hours=2,
        location="the annex",
    ),
    SeedEvent(
        title="[staging] yesterday's kitchen social",
        description="casual cook-and-hang.",
        delta_days=-1,
        duration_hours=2.5,
        location="shared kitchen",
    ),
    SeedEvent(
        title="[staging] happening today",
        description="drop-in tabling and outreach.",
        delta_days=0,
        duration_hours=4,
        location="market square",
        event_type=EventType.OFFICIAL,
    ),
    SeedEvent(
        title="[staging] tomorrow's cooking workshop",
        description="plant-based basics, hands-on.",
        delta_days=1,
        duration_hours=2,
        location="teaching kitchen",
    ),
    SeedEvent(
        title="[staging] weekend park cleanup",
        description="gloves and bags provided.",
        delta_days=3,
        duration_hours=3,
        location="riverside park",
    ),
    SeedEvent(
        title="[staging] next week's book club",
        description="this month's read: collective liberation.",
        delta_days=7,
        duration_hours=1.5,
        location="library room b",
    ),
    SeedEvent(
        title="[staging] monthly official meeting",
        description="agenda, updates, and open floor.",
        delta_days=14,
        duration_hours=2,
        location="main hall",
        event_type=EventType.OFFICIAL,
    ),
    SeedEvent(
        title="[staging] future festival",
        description="all-day tabling, food, and music.",
        delta_days=45,
        duration_hours=8,
        location="fairgrounds",
    ),
    SeedEvent(
        title="[staging] far-future retreat",
        description="weekend planning retreat.",
        delta_days=90,
        duration_hours=48,
        location="the lodge",
    ),
    SeedEvent(
        title=NON_MEMBER_EVENT_TITLE,
        description="official public event for testing non-member rsvp.",
        delta_days=5,
        duration_hours=3,
        location="downtown hub",
        event_type=EventType.OFFICIAL,
        rsvp_enabled=True,
        max_attendees=20,
    ),
    SeedEvent(
        title=OFFICIAL_PAST_TITLE,
        description="past official event with attendance marked for the report.",
        delta_days=-10,
        duration_hours=3,
        location="main hall",
        event_type=EventType.OFFICIAL,
        rsvp_enabled=True,
        max_attendees=8,
    ),
    SeedEvent(
        title=OFFICIAL_TODAY_TITLE,
        description="official event happening today with rsvp open, well under capacity.",
        delta_days=0,
        duration_hours=4,
        location="market square",
        event_type=EventType.OFFICIAL,
        rsvp_enabled=True,
        max_attendees=50,
    ),
    SeedEvent(
        title=OFFICIAL_FULL_TITLE,
        description="official event at/over capacity to exercise waitlist + promotion.",
        delta_days=9,
        duration_hours=3,
        location="teaching kitchen",
        event_type=EventType.OFFICIAL,
        rsvp_enabled=True,
        max_attendees=2,
    ),
]


# Non-member manage-token lifecycle states, controlling what the seed leaves behind.
TOKEN_VALID = "valid"
TOKEN_EXPIRED = "expired"
TOKEN_NONE = "none"


_ATTENDED = AttendanceStatus.ATTENDED
_NO_SHOW = AttendanceStatus.NO_SHOW


@dataclass
class RsvpOnEvent:
    """One RSVP row a seeded user should hold on a named event."""

    event_title: str
    status: str
    attendance: str = AttendanceStatus.UNKNOWN


def _rsvps(*rows: tuple) -> list[RsvpOnEvent]:
    """Build RsvpOnEvent rows from compact (title, status[, attendance]) tuples."""
    return [RsvpOnEvent(*row) for row in rows]


_A, _M, _C, _W = RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.CANT_GO, RSVPStatus.WAITLISTED


@dataclass
class MemberRsvpSpec:
    """RSVPs to attach to the condition member at ``cond_index``."""

    cond_index: int
    rsvps: list[RsvpOnEvent]


# Members across every RSVP state on the official events; the past event carries
# attendance marks so the attendance report shows a non-trivial member/non-member mix.
MEMBER_RSVP_SPECS = [
    MemberRsvpSpec(0, _rsvps((OFFICIAL_PAST_TITLE, _A, _ATTENDED), (OFFICIAL_TODAY_TITLE, _A))),
    MemberRsvpSpec(1, _rsvps((OFFICIAL_PAST_TITLE, _A, _NO_SHOW), (OFFICIAL_TODAY_TITLE, _M))),
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


@dataclass
class JoinRequestSpec:
    first_name: str
    last_name: str
    pronouns: str
    has_email: bool
    status: str
    days_ago: int
    answer: str


JOIN_REQUEST_SPECS = [
    JoinRequestSpec(
        "Sage",
        "Blackwood",
        "they/them",
        True,
        JoinRequestStatus.PENDING,
        0,
        "I've been vegan for three years and want to connect with a local community.",
    ),
    JoinRequestSpec(
        "Rowan",
        "Ashfield",
        "she/her",
        True,
        JoinRequestStatus.PENDING,
        1,
        "Looking for like-minded folks to organize with on animal liberation.",
    ),
    JoinRequestSpec(
        "Fern",
        "Whitaker",
        "he/him",
        False,
        JoinRequestStatus.PENDING,
        2,
        "A friend recommended this group after I went vegan last month.",
    ),
    JoinRequestSpec(
        "River",
        "Okafor",
        "they/them",
        True,
        JoinRequestStatus.PENDING,
        3,
        "I want to volunteer at events and help with outreach.",
    ),
    JoinRequestSpec(
        "Wren",
        "Castellano",
        "she/her",
        True,
        JoinRequestStatus.PENDING,
        5,
        "Interested in the intersection of veganism and collective liberation.",
    ),
    JoinRequestSpec(
        "Ash",
        "Delgado",
        "he/him",
        False,
        JoinRequestStatus.PENDING,
        8,
        "New to the area and looking for community.",
    ),
    JoinRequestSpec(
        "Juniper",
        "Osei",
        "they/them",
        True,
        JoinRequestStatus.APPROVED,
        14,
        "Been following the group's work for a while and finally ready to join.",
    ),
    JoinRequestSpec(
        "Marlowe",
        "Fontaine",
        "she/her",
        True,
        JoinRequestStatus.APPROVED,
        20,
        "A member invited me after a potluck.",
    ),
    JoinRequestSpec(
        "Briar",
        "Nakamura",
        "he/him",
        True,
        JoinRequestStatus.APPROVED,
        30,
        "I run a plant-based cooking blog and want to get more involved locally.",
    ),
    JoinRequestSpec(
        "Sparrow",
        "Reyes",
        "they/them",
        False,
        JoinRequestStatus.REJECTED,
        12,
        "Just filling out the form to see what happens.",
    ),
    JoinRequestSpec(
        "Indigo",
        "Marchetti",
        "she/her",
        True,
        JoinRequestStatus.REJECTED,
        25,
        "not really sure what this group does but sure",
    ),
]
