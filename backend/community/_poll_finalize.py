from notifications.service import create_waitlist_promoted_notifications

from community._event_rsvps import _apply_rsvp_in_transaction
from community._validation import Code, ValidationException
from community.models import Event, EventRSVP, PollAvailability, PollOption, RSVPStatus


def _yes_votes(winning_option: PollOption) -> list:
    """Winning option's yes-votes, oldest first.

    Ordering makes who gets a seat under capacity deterministic rather than
    arbitrary row order. voted_at is auto_now, so this is really "least recently
    changed their vote" — the only ordering signal PollVote records.
    """
    return list(
        winning_option.votes.filter(availability=PollAvailability.YES)
        .select_related("user")
        .order_by("voted_at")
    )


def _seat_voter(event: Event, user, existing: EventRSVP | None) -> bool:
    """Seat one yes-voter through the shared RSVP write path.

    return(bool): True if they were waitlisted for non-payment on a gated event.
    """
    # Polls carry no +1 concept; only an existing row's standing +1 survives.
    has_plus_one = existing is not None and existing.has_plus_one
    try:
        _apply_rsvp_in_transaction(event.id, user, RSVPStatus.ATTENDING, has_plus_one)
        return False
    except ValidationException as exc:
        if exc.code != Code.Event.PAYMENT_CONFIRMATION_REQUIRED:
            raise
    # Unpaid on a gated event: waitlist rather than seat unconfirmed or drop them,
    # so confirming payment promotes them through the normal path.
    _apply_rsvp_in_transaction(event.id, user, RSVPStatus.WAITLISTED, has_plus_one)
    return True


def _seat_or_skip(event: Event, user, existing: EventRSVP | None) -> bool:
    """Seat a voter, absorbing the reasons a single voter can't be seated.

    return(bool): True if they were waitlisted for non-payment on a gated event.
    """
    # A member who explicitly said they can't go must not be resurrected by finalize.
    if existing is not None and existing.status == RSVPStatus.CANT_GO:
        return False
    try:
        return _seat_voter(event, user, existing)
    except ValidationException:
        # RSVPs disabled/closed for this event, or this voter can no longer see
        # it — one unseatable voter must not fail the whole finalize.
        return False


def seat_yes_voters(event: Event, winning_option: PollOption) -> None:
    """Seat the winning option's yes-voters via the shared RSVP write path.

    Routing through _apply_rsvp_in_transaction is what makes finalize honor
    capacity/waitlist, the payment gate, plus-ones and rsvp_enabled instead of
    re-implementing (and drifting from) each one.
    """
    votes = _yes_votes(winning_option)
    if not votes:
        return
    existing_rsvps = {
        r.user_id: r
        for r in EventRSVP.objects.filter(event=event, user_id__in=[v.user_id for v in votes])
    }
    unpaid_user_ids = [
        str(vote.user_id)
        for vote in votes
        if _seat_or_skip(event, vote.user, existing_rsvps.get(vote.user_id))
    ]
    if unpaid_user_ids:
        create_waitlist_promoted_notifications(event, unpaid_user_ids, unpaid_user_ids)
