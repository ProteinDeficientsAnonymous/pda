"""Static data + pure helpers for the `seed_staging` command."""

from dataclasses import dataclass

from community.models.choices import EventType, JoinRequestStatus, PageVisibility

from ._seed_shared import SeedEvent

PASSWORD = "testPassword1@"


def perm_phone(index: int) -> str:
    return f"+170255501{index:02d}"


def cond_phone(index: int) -> str:
    return f"+170255502{index:02d}"


def privacy_phone(index: int) -> str:
    return f"+170255505{index:02d}"


def reset_member_phone() -> str:
    return "+17025550600"


def reset_member_email() -> str:
    return "reset.member@staging.example"


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


@dataclass
class PrivacySpec:
    """Members covering the pronouns/birthday/contact-privacy fields (Issue 923)."""

    label: str
    pronouns: str
    birthday_month: int | None
    birthday_day: int | None
    show_phone: bool = True
    show_email: bool = True
    show_birthday: bool = True
    hide_last_name: bool = False


PRIVACY_SPECS = [
    PrivacySpec("privacy: fully public", "they/them", 6, 15),
    PrivacySpec(
        "privacy: hides everything",
        "she/her",
        11,
        3,
        show_phone=False,
        show_email=False,
        show_birthday=False,
        hide_last_name=True,
    ),
    PrivacySpec("privacy: no pronouns or birthday set", "", None, None),
]


STAGING_EVENTS = [
    SeedEvent(
        title="[staging] past potluck",
        description="a wrapped-up community potluck from last month.",
        delta_days=-30,
        duration_hours=3,
        location="community center",
        visibility=PageVisibility.MEMBERS_ONLY,
    ),
    SeedEvent(
        title="[staging] last week's film night",
        description="documentary screening and discussion.",
        delta_days=-7,
        duration_hours=2,
        location="the annex",
        visibility=PageVisibility.MEMBERS_ONLY,
    ),
    SeedEvent(
        title="[staging] yesterday's kitchen social",
        description="casual cook-and-hang.",
        delta_days=-1,
        duration_hours=2.5,
        location="shared kitchen",
        visibility=PageVisibility.MEMBERS_ONLY,
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
        visibility=PageVisibility.MEMBERS_ONLY,
    ),
    SeedEvent(
        title="[staging] weekend park cleanup",
        description="gloves and bags provided.",
        delta_days=3,
        duration_hours=3,
        location="riverside park",
        visibility=PageVisibility.MEMBERS_ONLY,
    ),
    SeedEvent(
        title="[staging] next week's book club",
        description="this month's read: collective liberation.",
        delta_days=7,
        duration_hours=1.5,
        location="library room b",
        visibility=PageVisibility.MEMBERS_ONLY,
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
        visibility=PageVisibility.MEMBERS_ONLY,
    ),
    SeedEvent(
        title="[staging] far-future retreat",
        description="weekend planning retreat.",
        delta_days=90,
        duration_hours=48,
        location="the lodge",
        visibility=PageVisibility.MEMBERS_ONLY,
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


@dataclass
class JoinRequestSpec:
    first_name: str
    last_name: str
    has_email: bool
    status: str
    days_ago: int
    answers: dict[str, str]


JOIN_REQUEST_SPECS = [
    JoinRequestSpec(
        first_name="Sage",
        last_name="Blackwood",
        has_email=True,
        status=JoinRequestStatus.PENDING,
        days_ago=0,
        answers={
            "Why do you want to join?": (
                "I've been vegan for three years and want to connect with a local community."
            ),
            "How did you hear about us?": "Instagram",
            "What are your pronouns?": "they/them",
        },
    ),
    JoinRequestSpec(
        first_name="Rowan",
        last_name="Ashfield",
        has_email=True,
        status=JoinRequestStatus.PENDING,
        days_ago=1,
        answers={
            "Why do you want to join?": (
                "Looking for like-minded folks to organize with on animal liberation."
            ),
            "How did you hear about us?": "A friend",
            "What are your pronouns?": "she/her",
        },
    ),
    JoinRequestSpec(
        first_name="Fern",
        last_name="Whitaker",
        has_email=False,
        status=JoinRequestStatus.PENDING,
        days_ago=2,
        answers={
            "Why do you want to join?": (
                "A friend recommended this group after I went vegan last month."
            ),
            "How did you hear about us?": "A friend",
            "What are your pronouns?": "he/him",
        },
    ),
    JoinRequestSpec(
        first_name="River",
        last_name="Okafor",
        has_email=True,
        status=JoinRequestStatus.PENDING,
        days_ago=3,
        answers={
            "Why do you want to join?": "I want to volunteer at events and help with outreach.",
            "How did you hear about us?": "Flyer",
            "What are your pronouns?": "they/them",
        },
    ),
    JoinRequestSpec(
        first_name="Wren",
        last_name="Castellano",
        has_email=True,
        status=JoinRequestStatus.PENDING,
        days_ago=5,
        answers={
            "Why do you want to join?": (
                "Interested in the intersection of veganism and collective liberation."
            ),
            "How did you hear about us?": "Instagram",
            "What are your pronouns?": "she/her",
        },
    ),
    JoinRequestSpec(
        first_name="Ash",
        last_name="Delgado",
        has_email=False,
        status=JoinRequestStatus.PENDING,
        days_ago=8,
        answers={
            "Why do you want to join?": "New to the area and looking for community.",
            "How did you hear about us?": "Meetup",
            "What are your pronouns?": "he/him",
        },
    ),
    JoinRequestSpec(
        first_name="Juniper",
        last_name="Osei",
        has_email=True,
        status=JoinRequestStatus.APPROVED,
        days_ago=14,
        answers={
            "Why do you want to join?": (
                "Been following the group's work for a while and finally ready to join."
            ),
            "How did you hear about us?": "Instagram",
            "What are your pronouns?": "they/them",
        },
    ),
    JoinRequestSpec(
        first_name="Marlowe",
        last_name="Fontaine",
        has_email=True,
        status=JoinRequestStatus.APPROVED,
        days_ago=20,
        answers={
            "Why do you want to join?": "A member invited me after a potluck.",
            "How did you hear about us?": "A member",
            "What are your pronouns?": "she/her",
        },
    ),
    JoinRequestSpec(
        first_name="Briar",
        last_name="Nakamura",
        has_email=True,
        status=JoinRequestStatus.APPROVED,
        days_ago=30,
        answers={
            "Why do you want to join?": (
                "I run a plant-based cooking blog and want to get more involved locally."
            ),
            "How did you hear about us?": "Website",
            "What are your pronouns?": "he/him",
        },
    ),
    JoinRequestSpec(
        first_name="Sparrow",
        last_name="Reyes",
        has_email=False,
        status=JoinRequestStatus.REJECTED,
        days_ago=12,
        answers={
            "Why do you want to join?": "Just filling out the form to see what happens.",
            "How did you hear about us?": "Google",
            "What are your pronouns?": "they/them",
        },
    ),
    JoinRequestSpec(
        first_name="Indigo",
        last_name="Marchetti",
        has_email=True,
        status=JoinRequestStatus.REJECTED,
        days_ago=25,
        answers={
            "Why do you want to join?": "not really sure what this group does but sure",
            "How did you hear about us?": "TikTok",
            "What are your pronouns?": "she/her",
        },
    ),
]
