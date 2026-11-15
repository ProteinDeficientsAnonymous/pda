from community.events.helpers import can_edit_event
from community.models import Event, EventRSVP, RSVPStatus
from community.validation import Code, raise_validation

# Waitlisted is a "going" request, so it can step down too.
_GOING = frozenset({RSVPStatus.ATTENDING, RSVPStatus.WAITLISTED})
_STEP_DOWN_FROM = _GOING | {RSVPStatus.CANT_GO}


def _steps_down(existing: EventRSVP | None, status: str, has_plus_one: bool) -> bool:
    if existing is None:
        return False
    if status == RSVPStatus.CANT_GO:
        return existing.status in _STEP_DOWN_FROM
    drops_plus_one = existing.has_plus_one and not has_plus_one
    return status == RSVPStatus.ATTENDING and existing.status in _GOING and drops_plus_one


def enforce_rsvp_deadline(
    user, event: Event, existing: EventRSVP | None, status: str, has_plus_one: bool = False
) -> None:
    """After the deadline, going guests may only switch to can't go or drop a +1; hosts are exempt."""
    if not event.rsvp_deadline_passed or can_edit_event(user, event):
        return
    if not _steps_down(existing, status, has_plus_one):
        raise_validation(Code.Event.RSVPS_CLOSED_DEADLINE, status_code=400)
