from community._event_rsvps import _apply_rsvp_in_transaction
from community._validation import ValidationException
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


def _seat_or_skip(event: Event, user, existing: EventRSVP | None) -> None:
    """Seat one yes-voter through the shared RSVP write path, absorbing the
    reasons a single voter can't be seated.
    """
    # A member who explicitly said they can't go must not be resurrected by finalize.
    if existing is not None and existing.status == RSVPStatus.CANT_GO:
        return
    try:
        _apply_rsvp_in_transaction(event.id, user, RSVPStatus.ATTENDING, has_plus_one=False)
    except ValidationException:
        # RSVPs disabled/closed for this event, the payment gate, or this voter
        # can no longer see it — one unseatable voter must not fail the whole finalize.
        pass


def seat_yes_voters(event: Event, winning_option: PollOption) -> None:
    """Seat the winning option's yes-voters via the shared RSVP write path.

    Routing through _apply_rsvp_in_transaction is what makes finalize honor
    capacity/waitlist/rsvp_enabled instead of re-implementing (and drifting
    from) that logic.
    """
    votes = _yes_votes(winning_option)
    if not votes:
        return
    existing_rsvps = {
        r.user_id: r
        for r in EventRSVP.objects.filter(event=event, user_id__in=[v.user_id for v in votes])
    }
    for vote in votes:
        _seat_or_skip(event, vote.user, existing_rsvps.get(vote.user_id))
