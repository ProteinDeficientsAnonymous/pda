from collections.abc import Iterable

from community.events.helpers import broadcast_capacity_change
from community.models import (
    CoHostInviteStatus,
    Event,
    EventCoHostInvite,
    EventRSVP,
    EventStatus,
    RSVPStatus,
)
from community.models.event import is_past_q
from community.rsvps.status_emails import email_promoted_users
from community.rsvps.waitlist import promote_from_waitlist
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from notifications.service import broadcast_cohost_change

from users.helpers import strip_elevated_roles
from users.models import MembershipStatus, User

HELD_RSVP_STATUSES = (RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.WAITLISTED)
_LIVE_EVENT_STATUSES = (EventStatus.DRAFT, EventStatus.ACTIVE)


def upcoming_events_q(prefix: str = "") -> Q:
    return Q(**{f"{prefix}status__in": _LIVE_EVENT_STATUSES}) & ~is_past_q(timezone.now(), prefix)


def archive_user(request, user: User) -> list[str]:
    """Archive user and release what they hold on upcoming events.

    param(request): the triggering request, for promoted-member email logging
    param(user): the member to archive
    return(list[str]): ids of the elevated roles that were stripped
    """
    with transaction.atomic():
        actor = getattr(request, "auth", None)
        user.archived_at = timezone.now()
        user.status_before_archive = user.membership_status
        user.calendar_token = ""
        user.save(
            update_fields=[
                "archived_at",
                "status_before_archive",
                "calendar_token",
                *user.set_membership_status(MembershipStatus.ARCHIVED, by=actor),
            ]
        )
        removed_role_ids = strip_elevated_roles(user)
        release_upcoming_rsvps(request, user)
        step_down_as_cohost(user)
    return removed_role_ids


def release_upcoming_rsvps(request, user: User, event_filter: Q | None = None) -> None:
    event_ids = EventRSVP.objects.filter(
        upcoming_events_q("event__"), user=user, status__in=HELD_RSVP_STATUSES
    ).values_list("event_id", flat=True)
    events = Event.objects.select_for_update().filter(event_filter or Q(), id__in=list(event_ids))
    for event in events:
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
            lambda e=event, ids=promoted_user_ids: email_promoted_users(request, e, ids)
        )


def upcoming_hosted_events(user: User):
    return Event.objects.filter(
        upcoming_events_q(), pk__in=user.co_hosted_events.values("pk")
    ).annotate(host_count=Count("co_hosts"))


def step_down_as_cohost(user: User, events: Iterable[Event] | None = None) -> None:
    """Leave the given events, by default every upcoming one that has another host."""
    if events is None:
        events = upcoming_hosted_events(user).filter(host_count__gt=1)
    for event in events:
        leave_cohost(event, user)
        broadcast_cohost_change(event)


def leave_cohost(event: Event, user: User) -> None:
    event.co_hosts.remove(user)
    EventCoHostInvite.objects.filter(
        event=event, user=user, status=CoHostInviteStatus.ACCEPTED
    ).update(status=CoHostInviteStatus.REMOVED, decided_at=timezone.now())
