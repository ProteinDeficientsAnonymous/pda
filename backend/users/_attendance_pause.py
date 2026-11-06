import logging
from dataclasses import dataclass, field

from community.models import (
    CoHostInviteStatus,
    Event,
    EventCoHostInvite,
    EventRSVP,
    EventStatus,
    EventType,
)
from community.models.choices import is_official_or_club
from community.rsvps.public_shared import _format_event_when
from config.audit import AuditTarget, AuditTargetType, audit_log
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from notifications.email_sender import get_email_sender
from notifications.event_unpublished_email import (
    EventUnpublishedEmailDetails,
    send_event_unpublished_email,
)
from notifications.service import (
    broadcast_cohost_change,
    create_event_unpublished_notifications,
)

from users._archive import (
    _HELD_RSVP_STATUSES,
    _release_upcoming_rsvps,
    _step_down_as_cohost,
    upcoming_events_q,
)
from users.helpers import _strip_non_member_roles
from users.models import HAS_EMAIL, User

logger = logging.getLogger(__name__)

QUALIFYING_EVENT_TYPES = (EventType.OFFICIAL, EventType.CLUB)
QUALIFYING_EVENT_Q = Q(event_type__in=QUALIFYING_EVENT_TYPES)


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
    hosted = (
        Event.objects.filter(upcoming_events_q(), pk__in=user.co_hosted_events.values("pk"))
        .annotate(host_count=Count("co_hosts"))
        .order_by("start_datetime")
    )
    for event in hosted:
        if is_official_or_club(event.event_type):
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
            rsvps__status__in=_HELD_RSVP_STATUSES,
        )
        .exclude(pk__in=[e.pk for e in impact.drafted_events])
        .order_by("start_datetime")
    )
    for event in rsvped:
        bucket = (
            impact.kept_rsvps if is_official_or_club(event.event_type) else impact.removed_rsvps
        )
        bucket.append(event)
    return impact


def apply_attendance_pause(request, user: User) -> PauseImpact:
    """Attendance-pause the user and release what they hold on non-qualifying upcoming events.

    param(request): the triggering request, for audit and promoted-member email logging
    param(user): the member to pause
    return(PauseImpact): the impact as it stood when the pause was applied
    """
    with transaction.atomic():
        impact = attendance_pause_impact(user)
        # Drafting first deletes the user's own RSVP there, so releasing can't promote its waitlist.
        for event in impact.drafted_events:
            _move_to_draft(event, user)
        _release_upcoming_rsvps(request, user, ~QUALIFYING_EVENT_Q)
        _step_down_as_cohost(user, ~QUALIFYING_EVENT_Q)
        EventCoHostInvite.objects.filter(user=user, status=CoHostInviteStatus.PENDING).exclude(
            event__event_type__in=QUALIFYING_EVENT_TYPES
        ).update(status=CoHostInviteStatus.RESCINDED, decided_at=timezone.now())
        removed_role_ids = _strip_membership(user)
        user.attendance_paused_at = timezone.now()
        user.is_member = False
        user.has_joined_whatsapp = False
        user.save(update_fields=["attendance_paused_at", "is_member", "has_joined_whatsapp"])
        _audit_pause(request, user, impact, removed_role_ids)
    return impact


def _move_to_draft(event: Event, user: User) -> None:
    event.co_hosts.remove(user)
    EventCoHostInvite.objects.filter(
        event=event, user=user, status=CoHostInviteStatus.ACCEPTED
    ).update(status=CoHostInviteStatus.REMOVED, decided_at=timezone.now())
    event.status = EventStatus.DRAFT
    event.save(update_fields=["status"])
    rsvps = EventRSVP.objects.filter(event=event)
    guest_ids = [
        str(uid)
        for uid in rsvps.filter(status__in=_HELD_RSVP_STATUSES)
        .exclude(user=user)
        .values_list("user_id", flat=True)
    ]
    rsvps.delete()
    broadcast_cohost_change(event)
    transaction.on_commit(lambda: _notify_unpublished(event, guest_ids))


def _notify_unpublished(event: Event, guest_ids: list[str]) -> None:
    if not guest_ids:
        return
    try:
        create_event_unpublished_notifications(event, guest_ids)
    except Exception:  # noqa: BLE001 — the pause has committed; a failed notice must not undo it
        logger.warning("event_unpublished_notifications_failed", exc_info=True)
    sender = get_email_sender()
    for guest in User.objects.filter(pk__in=guest_ids).filter(HAS_EMAIL):
        try:
            result = send_event_unpublished_email(
                sender=sender,
                details=EventUnpublishedEmailDetails(
                    to=guest.email or "",
                    display_name=guest.first_name,
                    event_title=event.title,
                    event_when=_format_event_when(event),
                ),
            )
        except Exception:  # noqa: BLE001 — one bad send must not abort the batch
            logger.warning("event_unpublished_email_send_exception", exc_info=True)
            continue
        if not result.success:
            logger.warning("event_unpublished_email_failed", extra={"error": result.error})


def _strip_membership(user: User) -> list[str]:
    removed_role_ids = _strip_non_member_roles(user)
    member_role = user.roles.filter(name="member", is_default=True).first()
    if member_role:
        user.roles.remove(member_role)
        removed_role_ids.append(str(member_role.id))
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
