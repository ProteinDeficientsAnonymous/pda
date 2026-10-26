from notifications.service import create_poll_seated_unpaid_notifications

from community._event_rsvps import _apply_rsvp_in_transaction, _RsvpApply
from community._rsvp_payment import payment_enforced_for_event
from community._validation import ValidationException
from community.models import Event, EventRSVP, PollAvailability, PollOption, RSVPStatus


def _yes_votes(winning_option: PollOption) -> list:
    # voted_at is auto_now, so this orders by last vote change, not first vote cast.
    return list(
        winning_option.votes.filter(availability=PollAvailability.YES)
        .select_related("user")
        .order_by("voted_at")
    )


def _seat_or_skip(event: Event, user, existing: EventRSVP | None) -> bool:
    """return(bool): whether the voter was newly seated without a payment confirmation."""
    if existing is not None and existing.status == RSVPStatus.CANT_GO:
        return False
    # The host is seating voters, not the voter claiming a spot, so seat them and ask them to pay after.
    try:
        final_status, _, previous_status = _apply_rsvp_in_transaction(
            event.id,
            user,
            _RsvpApply(status=RSVPStatus.ATTENDING, enforce_payment_gate=False),
        )
    except ValidationException:
        return False
    return (
        final_status == RSVPStatus.ATTENDING
        and previous_status != RSVPStatus.ATTENDING
        and (existing is None or existing.paid_confirmed_at is None)
    )


def seat_yes_voters(event: Event, winning_option: PollOption) -> None:
    votes = _yes_votes(winning_option)
    if not votes:
        return
    existing_rsvps = {
        r.user_id: r
        for r in EventRSVP.objects.filter(event=event, user_id__in=[v.user_id for v in votes])
    }
    seated_unpaid = [
        str(vote.user_id)
        for vote in votes
        if _seat_or_skip(event, vote.user, existing_rsvps.get(vote.user_id))
    ]
    if seated_unpaid and payment_enforced_for_event(event):
        create_poll_seated_unpaid_notifications(event, seated_unpaid)
