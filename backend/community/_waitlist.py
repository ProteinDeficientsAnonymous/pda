from django.db.models import F
from django.utils import timezone
from notifications.service import create_waitlist_promoted_notifications

from community._rsvp_counts import _attending_headcount_db
from community._rsvp_payment import payment_enforced_for_event
from community.models import Event, EventRSVP, RSVPStatus

WAITLIST_ORDER = (F("waitlist_position").asc(nulls_last=True), "created_at", "pk")


def waitlist_sort_key(rsvp: EventRSVP) -> tuple:
    """Python mirror of WAITLIST_ORDER for already-fetched rows."""
    pos = rsvp.waitlist_position
    return (pos is None, pos or 0, rsvp.created_at, str(rsvp.pk))


def _promotable_waitlist_rsvps(event: Event) -> list[EventRSVP]:
    """Waitlisted RSVPs that fit under max_attendees, in line order; stops at the first that doesn't."""
    headcount = _attending_headcount_db(event)
    promotable: list[EventRSVP] = []
    line = EventRSVP.objects.filter(event=event, status=RSVPStatus.WAITLISTED).order_by(
        *WAITLIST_ORDER
    )
    for rsvp in line:
        spots = 2 if rsvp.has_plus_one else 1
        if headcount + spots > event.max_attendees:
            break
        headcount += spots
        promotable.append(rsvp)
    return promotable


def _mark_attending(rsvps: list[EventRSVP]) -> None:
    # bulk_update skips EventRSVP.save(), so apply what it would: clear the position, stamp the change.
    now = timezone.now()
    for rsvp in rsvps:
        rsvp.status = RSVPStatus.ATTENDING
        rsvp.waitlist_position = None
        rsvp.status_changed_at = now
        rsvp.updated_at = now
    EventRSVP.objects.bulk_update(
        rsvps, ["status", "waitlist_position", "status_changed_at", "updated_at"]
    )


def _waitlist_closed(event: Event) -> bool:
    return event.max_attendees is None or event.is_past


def promote_from_waitlist(event: Event) -> list[str]:
    """Promote waitlisted users to attending in line order (host-set position, then FIFO).

    Must be called inside a transaction.atomic() block with the event row locked.
    Returns the list of promoted user ids so callers that need to follow up per
    promoted user (e.g. emailing promoted non-members) can do so after commit.
    """
    if _waitlist_closed(event):
        return []
    promoted = _promotable_waitlist_rsvps(event)
    if not promoted:
        return []
    _mark_attending(promoted)
    promoted_user_ids = [str(r.user_id) for r in promoted]
    unpaid_user_ids = (
        [str(r.user_id) for r in promoted if r.paid_confirmed_at is None]
        if payment_enforced_for_event(event)
        else []
    )
    create_waitlist_promoted_notifications(event, promoted_user_ids, unpaid_user_ids)
    return promoted_user_ids
