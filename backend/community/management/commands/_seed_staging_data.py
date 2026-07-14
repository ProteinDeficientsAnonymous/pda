"""Static data + pure helpers for the `seed_staging` command."""

from dataclasses import dataclass

from community.models.choices import AttendanceStatus, EventType, RSVPStatus

PASSWORD = "testPassword1@"


@dataclass
class SeedStagingEvent:
    title: str
    description: str
    delta_days: int
    duration_hours: float
    location: str
    event_type: str = EventType.COMMUNITY
    rsvp_enabled: bool = False
    max_attendees: int | None = None


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
    SeedStagingEvent(
        title="[staging] past potluck",
        description="a wrapped-up community potluck from last month.",
        delta_days=-30,
        duration_hours=3,
        location="community center",
    ),
    SeedStagingEvent(
        title="[staging] last week's film night",
        description="documentary screening and discussion.",
        delta_days=-7,
        duration_hours=2,
        location="the annex",
    ),
    SeedStagingEvent(
        title="[staging] yesterday's kitchen social",
        description="casual cook-and-hang.",
        delta_days=-1,
        duration_hours=2.5,
        location="shared kitchen",
    ),
    SeedStagingEvent(
        title="[staging] happening today",
        description="drop-in tabling and outreach.",
        delta_days=0,
        duration_hours=4,
        location="market square",
        event_type=EventType.OFFICIAL,
    ),
    SeedStagingEvent(
        title="[staging] tomorrow's cooking workshop",
        description="plant-based basics, hands-on.",
        delta_days=1,
        duration_hours=2,
        location="teaching kitchen",
    ),
    SeedStagingEvent(
        title="[staging] weekend park cleanup",
        description="gloves and bags provided.",
        delta_days=3,
        duration_hours=3,
        location="riverside park",
    ),
    SeedStagingEvent(
        title="[staging] next week's book club",
        description="this month's read: collective liberation.",
        delta_days=7,
        duration_hours=1.5,
        location="library room b",
    ),
    SeedStagingEvent(
        title="[staging] monthly official meeting",
        description="agenda, updates, and open floor.",
        delta_days=14,
        duration_hours=2,
        location="main hall",
        event_type=EventType.OFFICIAL,
    ),
    SeedStagingEvent(
        title="[staging] future festival",
        description="all-day tabling, food, and music.",
        delta_days=45,
        duration_hours=8,
        location="fairgrounds",
    ),
    SeedStagingEvent(
        title="[staging] far-future retreat",
        description="weekend planning retreat.",
        delta_days=90,
        duration_hours=48,
        location="the lodge",
    ),
    SeedStagingEvent(
        title=NON_MEMBER_EVENT_TITLE,
        description="official public event for testing non-member rsvp.",
        delta_days=5,
        duration_hours=3,
        location="downtown hub",
        event_type=EventType.OFFICIAL,
        rsvp_enabled=True,
        max_attendees=20,
    ),
    SeedStagingEvent(
        title=OFFICIAL_PAST_TITLE,
        description="past official event with attendance marked for the report.",
        delta_days=-10,
        duration_hours=3,
        location="main hall",
        event_type=EventType.OFFICIAL,
        rsvp_enabled=True,
        max_attendees=8,
    ),
    SeedStagingEvent(
        title=OFFICIAL_TODAY_TITLE,
        description="official event happening today with rsvp open, well under capacity.",
        delta_days=0,
        duration_hours=4,
        location="market square",
        event_type=EventType.OFFICIAL,
        rsvp_enabled=True,
        max_attendees=50,
    ),
    SeedStagingEvent(
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
