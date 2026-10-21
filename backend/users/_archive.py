from community._event_helpers import broadcast_capacity_change
from community._public_rsvp_shared import _email_promoted_non_members
from community._waitlist import promote_from_waitlist
from community.models import (
    CoHostInviteStatus,
    Event,
    EventCoHostInvite,
    EventRSVP,
    EventStatus,
    RSVPStatus,
)
from community.models.event import _is_past_q
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from notifications.service import broadcast_cohost_change

from users._helpers import _strip_non_member_roles
from users.models import User

_HELD_RSVP_STATUSES = (RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.WAITLISTED)
_LIVE_EVENT_STATUSES = (EventStatus.DRAFT, EventStatus.ACTIVE)


def upcoming_events_q(prefix: str = "") -> Q:
    return Q(**{f"{prefix}status__in": _LIVE_EVENT_STATUSES}) & ~_is_past_q(timezone.now(), prefix)


def archive_user(request, user: User) -> list[str]:
    """Archive user and release what they hold on upcoming events.

    param(request): the triggering request, for promoted-member email logging
    param(user): the member to archive
    return(list[str]): ids of the elevated roles that were stripped
    """
    with transaction.atomic():
        user.archived_at = timezone.now()
        user.calendar_token = ""
        user.save(update_fields=["archived_at", "calendar_token"])
        removed_role_ids = _strip_non_member_roles(user)
        _release_upcoming_rsvps(request, user)
        _step_down_as_cohost(user)
    return removed_role_ids


def _release_upcoming_rsvps(request, user: User) -> None:
    event_ids = EventRSVP.objects.filter(
        upcoming_events_q("event__"), user=user, status__in=_HELD_RSVP_STATUSES
    ).values_list("event_id", flat=True)
    for event in Event.objects.select_for_update().filter(id__in=list(event_ids)):
        rsvp = EventRSVP.objects.get(event=event, user=user)
        was_attending = rsvp.status == RSVPStatus.ATTENDING
        rsvp.status = RSVPStatus.CANT_GO
        rsvp.cancelled_at = timezone.now()
        rsvp.save(update_fields=["status", "cancelled_at", "updated_at"])
        if not was_attending:
            continue
        promoted_user_ids = promote_from_waitlist(event)
        broadcast_capacity_change(event.id)
        transaction.on_commit(
            lambda e=event, ids=promoted_user_ids: _email_promoted_non_members(request, e, ids)
        )


def _step_down_as_cohost(user: User) -> None:
    """Leave every upcoming event that has another host; sole-hosted events are left as-is."""
    events = (
        Event.objects.filter(upcoming_events_q(), pk__in=user.co_hosted_events.values("pk"))
        .annotate(host_count=Count("co_hosts"))
        .filter(host_count__gt=1)
    )
    for event in events:
        event.co_hosts.remove(user)
        EventCoHostInvite.objects.filter(
            event=event, user=user, status=CoHostInviteStatus.ACCEPTED
        ).update(status=CoHostInviteStatus.REMOVED, decided_at=timezone.now())
        broadcast_cohost_change(event)
