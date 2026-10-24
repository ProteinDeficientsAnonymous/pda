from django.db import transaction

from community._event_rsvps import _apply_rsvp_in_transaction, _RsvpApply
from community._validation import ValidationException
from community.models import Event, EventRSVP, RSVPStatus, is_official_or_club


def auto_rsvp_host(event: Event, user) -> bool:
    """Silently rsvp an official/club host as going unless they already have an rsvp."""
    if not is_official_or_club(event.event_type):
        return False
    try:
        with transaction.atomic():
            # Lock before the existence check so a concurrent member rsvp can't be overwritten.
            Event.objects.select_for_update().only("id").get(id=event.id)
            if EventRSVP.objects.filter(event_id=event.id, user=user).exists():
                return False
            # Not paid_confirmed: gated events skip rather than recording a payment nobody made.
            _apply_rsvp_in_transaction(event.id, user, _RsvpApply(status=RSVPStatus.ATTENDING))
    except ValidationException:
        return False
    return True
