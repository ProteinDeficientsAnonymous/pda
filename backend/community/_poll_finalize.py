from community._event_rsvps import _apply_rsvp_in_transaction, _RsvpApply
from community._validation import ValidationException
from community.models import Event, EventRSVP, PollAvailability, PollOption, RSVPStatus


def _yes_votes(winning_option: PollOption) -> list:
    # voted_at is auto_now, so this orders by last change, not first vote —
    # the only ordering signal PollVote records.
    return list(
        winning_option.votes.filter(availability=PollAvailability.YES)
        .select_related("user")
        .order_by("voted_at")
    )


def _seat_or_skip(event: Event, user, existing: EventRSVP | None) -> None:
    if existing is not None and existing.status == RSVPStatus.CANT_GO:
        return
    try:
        _apply_rsvp_in_transaction(event.id, user, _RsvpApply(status=RSVPStatus.ATTENDING))
    except ValidationException:
        pass


def seat_yes_voters(event: Event, winning_option: PollOption) -> None:
    votes = _yes_votes(winning_option)
    if not votes:
        return
    existing_rsvps = {
        r.user_id: r
        for r in EventRSVP.objects.filter(event=event, user_id__in=[v.user_id for v in votes])
    }
    for vote in votes:
        _seat_or_skip(event, vote.user, existing_rsvps.get(vote.user_id))
