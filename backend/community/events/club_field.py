"""Which club a club event belongs to; other event types never have one."""

from uuid import UUID

from community.models import Club, Event, EventType
from community.validation import Code, raise_validation


def resolve_event_club(event_type: str, club_id: UUID | None) -> Club | None:
    if event_type != EventType.CLUB:
        return None
    club = Club.objects.filter(id=club_id).first() if club_id else None
    if club_id and club is None:
        raise_validation(Code.Club.NOT_FOUND, field="club_id")
    if club is None:
        raise_validation(Code.Event.CLUB_REQUIRED, field="club_id")
    return club


def apply_club_update(event: Event, updates: dict) -> None:
    """Swap a patch's `club_id` for `club`, and drop the club when the event stops being a club event."""
    effective_type = updates.get("event_type") or event.event_type
    if "club_id" in updates:
        updates["club"] = resolve_event_club(effective_type, updates.pop("club_id"))
    elif effective_type != EventType.CLUB:
        if event.club_id is not None:
            updates["club"] = None
    elif event.event_type != EventType.CLUB:
        raise_validation(Code.Event.CLUB_REQUIRED, field="club_id")
