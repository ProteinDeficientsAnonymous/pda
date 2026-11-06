import logging
from dataclasses import dataclass, field

from community.events.tentative_member_access import (
    TENTATIVE_MEMBER_EVENT_TYPES as KEPT_EVENT_TYPES,
)
from community.models import CoHostInviteStatus, Event, EventCoHostInvite
from config.audit import AuditTarget, AuditTargetType, audit_log
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from users._archive import (
    HELD_RSVP_STATUSES,
    release_upcoming_rsvps,
    step_down_as_cohost,
    upcoming_events_q,
    upcoming_hosted_events,
)
from users.models import User

KEPT_EVENT_Q = Q(event_type__in=KEPT_EVENT_TYPES)


@dataclass
class PauseImpact:
    kept_rsvps: list[Event] = field(default_factory=list)
    removed_rsvps: list[Event] = field(default_factory=list)
    kept_hosting: list[Event] = field(default_factory=list)
    removed_hosting: list[Event] = field(default_factory=list)
    drafted_events: list[Event] = field(default_factory=list)


def attendance_pause_impact(user: User) -> PauseImpact:
    """Sort the user's upcoming RSVPs and host spots into what a pause keeps, removes or drafts.

    param(user): the member who would be attendance-paused
    return(PauseImpact): events per bucket, soonest first
    """
    impact = PauseImpact()
    for event in upcoming_hosted_events(user).order_by("start_datetime"):
        if event.event_type in KEPT_EVENT_TYPES:
            impact.kept_hosting.append(event)
        elif event.host_count > 1:
            impact.removed_hosting.append(event)
        else:
            impact.drafted_events.append(event)

    # A drafted event loses all its RSVPs, so the user's own isn't listed as removed too.
    rsvped = (
        Event.objects.filter(
            upcoming_events_q(),
            rsvps__user=user,
            rsvps__status__in=HELD_RSVP_STATUSES,
        )
        .exclude(pk__in=[e.pk for e in impact.drafted_events])
        .order_by("start_datetime")
    )
    for event in rsvped:
        bucket = impact.kept_rsvps if event.event_type in KEPT_EVENT_TYPES else impact.removed_rsvps
        bucket.append(event)
    return impact


def apply_attendance_pause(request, user: User) -> PauseImpact:
    """Attendance-pause the user and release what they hold on upcoming events of other types.

    param(request): the triggering request, for audit and promoted-member email logging
    param(user): the member to pause
    return(PauseImpact): the impact as it stood when the pause was applied
    """
    with transaction.atomic():
        impact = attendance_pause_impact(user)
        release_upcoming_rsvps(request, user, ~KEPT_EVENT_Q)
        step_down_as_cohost(user, ~KEPT_EVENT_Q)
        EventCoHostInvite.objects.filter(
            upcoming_events_q("event__"), user=user, status=CoHostInviteStatus.PENDING
        ).exclude(event__event_type__in=KEPT_EVENT_TYPES).update(
            status=CoHostInviteStatus.RESCINDED, decided_at=timezone.now()
        )
        removed_role_ids = _strip_membership(user)
        user.attendance_paused_at = timezone.now()
        user.is_member = False
        user.has_joined_whatsapp = False
        user.save(update_fields=["attendance_paused_at", "is_member", "has_joined_whatsapp"])
        _audit_pause(request, user, impact, removed_role_ids)
    return impact


def _strip_membership(user: User) -> list[str]:
    removed_role_ids = [str(pk) for pk in user.roles.values_list("pk", flat=True)]
    user.roles.clear()
    return removed_role_ids


def _audit_pause(request, user: User, impact: PauseImpact, removed_role_ids: list[str]) -> None:
    details = {
        "removed_role_ids": removed_role_ids,
        "removed_rsvp_event_ids": [str(e.pk) for e in impact.removed_rsvps],
        "removed_hosting_event_ids": [str(e.pk) for e in impact.removed_hosting],
        "drafted_event_ids": [str(e.pk) for e in impact.drafted_events],
    }
    audit_log(
        logging.WARNING,
        "user_attendance_paused",
        request,
        target=AuditTarget(type=AuditTargetType.USER, id=str(user.pk), details=details),
    )
