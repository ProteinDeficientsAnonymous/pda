import logging
from dataclasses import dataclass, field

from community.events.tentative_member_access import (
    TENTATIVE_MEMBER_EVENT_TYPES as KEPT_EVENT_TYPES,
)
from community.events.unpublish import clear_unpublished_side_effects
from community.models import CoHostInviteStatus, Event, EventCoHostInvite, EventRSVP, EventStatus
from config.audit import AuditTarget, AuditTargetType, audit_log
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from notifications.email_helpers import format_event_when
from notifications.email_sender import get_email_sender, send_best_effort
from notifications.event_unpublished_email import (
    EventUnpublishedEmailDetails,
    send_event_unpublished_email,
)
from notifications.service import create_event_unpublished_notifications

from users._archive import (
    HELD_RSVP_STATUSES,
    leave_cohost,
    release_upcoming_rsvps,
    step_down_as_cohost,
    upcoming_events_q,
    upcoming_hosted_events,
)
from users.helpers import grant_membership
from users.models import HAS_EMAIL, User

logger = logging.getLogger(__name__)

KEPT_EVENT_Q = Q(event_type__in=KEPT_EVENT_TYPES)


@dataclass
class PauseImpact:
    kept_rsvps: list[Event] = field(default_factory=list)
    removed_rsvps: list[Event] = field(default_factory=list)
    removed_hosting: list[Event] = field(default_factory=list)
    drafted_events: list[Event] = field(default_factory=list)


def attendance_pause_impact(user: User) -> PauseImpact:
    """Sort the user's upcoming RSVPs and host spots into what a pause keeps, removes or drafts.

    param(user): the member who would be attendance-paused
    return(PauseImpact): events per bucket, soonest first
    """
    impact = PauseImpact()
    for event in upcoming_hosted_events(user).order_by("start_datetime"):
        if event.host_count > 1:
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
    """Attendance-pause the user, drop their other-type RSVPs and release every host spot.

    param(request): the triggering request, for audit and promoted-member email logging
    param(user): the member to pause
    return(PauseImpact): the impact as it stood when the pause was applied
    """
    with transaction.atomic():
        impact = attendance_pause_impact(user)
        # Drafting first deletes the user's own RSVP there, so releasing can't promote its waitlist.
        for event in impact.drafted_events:
            _move_to_draft(event, user)
        release_upcoming_rsvps(request, user, ~KEPT_EVENT_Q)
        step_down_as_cohost(user)
        EventCoHostInvite.objects.filter(
            upcoming_events_q("event__"), user=user, status=CoHostInviteStatus.PENDING
        ).update(status=CoHostInviteStatus.RESCINDED, decided_at=timezone.now())
        removed_role_ids = _strip_membership(user)
        user.attendance_paused_at = timezone.now()
        user.is_member = False
        user.has_joined_whatsapp = False
        user.save(update_fields=["attendance_paused_at", "is_member", "has_joined_whatsapp"])
        _audit_pause(request, user, impact, removed_role_ids)
    return impact


def _move_to_draft(event: Event, user: User) -> None:
    leave_cohost(event, user)
    event.status = EventStatus.DRAFT
    event.save(update_fields=["status"])
    rsvps = EventRSVP.objects.filter(event=event)
    guest_ids = [
        str(uid)
        for uid in rsvps.filter(status__in=HELD_RSVP_STATUSES)
        .exclude(user=user)
        .values_list("user_id", flat=True)
    ]
    rsvps.delete()
    clear_unpublished_side_effects(event)
    transaction.on_commit(lambda: _notify_unpublished(event, guest_ids))


def _notify_unpublished(event: Event, guest_ids: list[str]) -> None:
    if not guest_ids:
        return
    try:
        create_event_unpublished_notifications(event, guest_ids)
    except Exception:  # noqa: BLE001 — the pause has committed; a failed notice must not undo it
        logger.warning("event_unpublished_notifications_failed", exc_info=True)
    sender = get_email_sender()
    event_when = format_event_when(event, tbd="")
    for guest in User.objects.filter(pk__in=guest_ids).filter(HAS_EMAIL):
        details = EventUnpublishedEmailDetails(
            to=guest.email or "",
            display_name=guest.first_name,
            event_title=event.title,
            event_when=event_when,
        )
        send_best_effort(
            lambda d=details: send_event_unpublished_email(sender=sender, details=d),
            "event_unpublished_email",
        )


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


def apply_attendance_pause_patch(request, user: User, attendance_paused: bool | None) -> bool:
    """Pause or silently unpause the user per the PATCH flag; returns True if anything changed."""
    is_paused = user.attendance_paused_at is not None
    if attendance_paused is None or attendance_paused == is_paused:
        return False
    if attendance_paused:
        apply_attendance_pause(request, user)
    else:
        _unpause(request, user)
    return True


def _unpause(request, user: User) -> None:
    with transaction.atomic():
        user.attendance_paused_at = None
        user.is_member = True
        user.save(update_fields=["attendance_paused_at", "is_member"])
        grant_membership(user)
        audit_log(
            logging.WARNING,
            "user_attendance_unpaused",
            request,
            target=AuditTarget(type=AuditTargetType.USER, id=str(user.pk)),
        )
