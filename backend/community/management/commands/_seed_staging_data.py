"""Static data + pure helpers for the `seed_staging` command."""

from dataclasses import dataclass

from community.models.choices import EventType

PASSWORD = "testPassword1@"


@dataclass
class SeedStagingEvent:
    title: str
    description: str
    delta_days: int
    duration_hours: float
    location: str
    event_type: str = EventType.COMMUNITY


def perm_phone(index: int) -> str:
    return f"+170255501{index:02d}"


def cond_phone(index: int) -> str:
    return f"+170255502{index:02d}"


def perm_email(key: str) -> str:
    return f"perm.{key}@staging.example"


def cond_email(index: int) -> str:
    return f"cond{index:02d}@staging.example"


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
]
