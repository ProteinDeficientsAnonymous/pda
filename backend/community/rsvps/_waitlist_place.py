from community.models import Event, EventRSVP, RSVPStatus
from community.rsvps.waitlist import WAITLIST_ORDER


def keep_waitlist_place(event: Event, existing: EventRSVP | None, final_status: str) -> str:
    """Keep a waitlisted row waitlisted when it re-saves "going" (e.g. to add a +1).

    Only promote_from_waitlist seats people, in line order, so an edit can't
    skip whoever is ahead.
    """
    if (
        event.max_attendees is not None
        and existing is not None
        and existing.status == RSVPStatus.WAITLISTED
        and final_status == RSVPStatus.ATTENDING
    ):
        return RSVPStatus.WAITLISTED
    return final_status


def save_would_seat_waitlister(
    event: Event, existing: EventRSVP | None, resolved_status: str
) -> bool:
    """Whether a waitlisted row's re-save fits an open seat with nobody ahead, so promotion seats it now."""
    if existing is None or existing.status != RSVPStatus.WAITLISTED:
        return False
    if resolved_status != RSVPStatus.ATTENDING:
        return False
    head = (
        EventRSVP.objects.filter(event=event, status=RSVPStatus.WAITLISTED)
        .order_by(*WAITLIST_ORDER)
        .values_list("pk", flat=True)
        .first()
    )
    return head == existing.pk
