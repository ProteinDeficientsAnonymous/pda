from django.db import transaction

from community.models import Event, EventRSVP, RSVPStatus, is_official_or_club
from community.rsvps.member import RsvpApply, apply_rsvp_in_transaction
from community.validation import ValidationException


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
            apply_rsvp_in_transaction(
                event.id, user, RsvpApply(status=RSVPStatus.ATTENDING, skip_host_gates=True)
            )
    except ValidationException:
        return False
    return True


def auto_rsvp_hosts(event: Event) -> bool:
    """Auto-rsvp every current host; returns whether any rsvp was added."""
    added = [auto_rsvp_host(event, host) for host in event.co_hosts.all()]
    return any(added)
