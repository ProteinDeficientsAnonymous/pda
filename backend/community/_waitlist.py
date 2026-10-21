from django.db.models import F
from notifications.service import create_waitlist_promoted_notifications

from community._rsvp_counts import _attending_headcount_db
from community._rsvp_payment import payment_enforced_for_event
from community.models import Event, EventRSVP, RSVPStatus

WAITLIST_ORDER = (F("waitlist_position").asc(nulls_last=True), "created_at", "pk")


def waitlist_sort_key(rsvp: EventRSVP) -> tuple:
    """Python mirror of WAITLIST_ORDER for already-fetched rows."""
    pos = rsvp.waitlist_position
    return (pos is None, pos or 0, rsvp.created_at, str(rsvp.pk))


def _next_promotable_waitlist_rsvp(event: Event, headcount: int) -> EventRSVP | None:
    """Return the first waitlisted RSVP in line if it still fits under max_attendees."""
    oldest = (
        EventRSVP.objects.filter(event=event, status=RSVPStatus.WAITLISTED)
        .order_by(*WAITLIST_ORDER)
        .first()
    )
    if not oldest:
        return None
    if headcount + (2 if oldest.has_plus_one else 1) > event.max_attendees:
        return None
    return oldest


def promote_from_waitlist(event: Event) -> list[str]:
    """Promote waitlisted users to attending in line order (host-set position, then FIFO).

    Must be called inside a transaction.atomic() block with the event row locked.
    Returns the list of promoted user ids so callers that need to follow up per
    promoted user (e.g. emailing promoted non-members) can do so after commit.
    """
    if event.max_attendees is None:
        return []
    promoted_user_ids: list[str] = []
    unpaid_user_ids: list[str] = []
    needs_payment = payment_enforced_for_event(event)
    while True:
        headcount = _attending_headcount_db(event)
        if headcount >= event.max_attendees:
            break
        oldest = _next_promotable_waitlist_rsvp(event, headcount)
        if oldest is None:
            break
        oldest.status = RSVPStatus.ATTENDING
        oldest.save(update_fields=["status", "updated_at"])
        promoted_user_ids.append(str(oldest.user_id))
        if needs_payment and oldest.paid_confirmed_at is None:
            unpaid_user_ids.append(str(oldest.user_id))
    if promoted_user_ids:
        create_waitlist_promoted_notifications(event, promoted_user_ids, unpaid_user_ids)
    return promoted_user_ids
