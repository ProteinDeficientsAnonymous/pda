from community.events.helpers import can_edit_event
from community.models import Event, EventRSVP, RSVPStatus
from community.validation import Code, raise_validation

# Statuses someone may still step down from after the deadline (waitlisted is a "going" request).
_STEP_DOWN_FROM = frozenset({RSVPStatus.ATTENDING, RSVPStatus.WAITLISTED, RSVPStatus.CANT_GO})


def enforce_rsvp_deadline(user, event: Event, existing: EventRSVP | None, status: str) -> None:
    """After the deadline, only going -> can't go is allowed; hosts are exempt."""
    if not event.rsvp_deadline_passed or can_edit_event(user, event):
        return
    stepping_down = (
        status == RSVPStatus.CANT_GO and existing is not None and existing.status in _STEP_DOWN_FROM
    )
    if not stepping_down:
        raise_validation(Code.Event.RSVPS_CLOSED_DEADLINE, status_code=400)
