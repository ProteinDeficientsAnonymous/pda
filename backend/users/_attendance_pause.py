import logging
from dataclasses import dataclass, field

from community.events.limited_access import (
    LIMITED_ACCESS_EVENT_TYPES as KEPT_RSVP_EVENT_TYPES,
)
from community.events.unpublish import clear_unpublished_side_effects
from community.models import (
    AttendanceStatus,
    CancelReason,
    CoHostInviteStatus,
    Event,
    EventCoHostInvite,
    EventRSVP,
    EventStatus,
)
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
from users.helpers import elevated_roles, strip_elevated_roles
from users.models import HAS_EMAIL, MembershipStatus, User

logger = logging.getLogger(__name__)

KEPT_RSVP_EVENT_Q = Q(event_type__in=KEPT_RSVP_EVENT_TYPES)
# Payment and attendance records outlive a draft, so these RSVPs survive it.
_PAID_OR_MARKED_RSVP_Q = (
    Q(paid_confirmed_at__isnull=False)
    | Q(payment_verified_at__isnull=False)
    | Q(checked_in_at__isnull=False)
    | ~Q(attendance=AttendanceStatus.UNKNOWN)
)


@dataclass
class PauseImpact:
    kept_rsvps: list[Event] = field(default_factory=list)
    removed_rsvps: list[Event] = field(default_factory=list)
    removed_hosting: list[Event] = field(default_factory=list)
    drafted_events: list[Event] = field(default_factory=list)
    rescinded_invites: list[Event] = field(default_factory=list)
    stripped_roles: list[str] = field(default_factory=list)
    clears_whatsapp: bool = False


def _keeps_official_rsvps(pause: MembershipStatus) -> bool:
    return pause == MembershipStatus.ATTENDANCE_PAUSED


def pause_impact(user: User, pause: MembershipStatus) -> PauseImpact:
    """Sort the user's upcoming RSVPs and host spots into what a pause keeps, removes or drafts.

    param(user): the member who would be paused
    param(pause): ATTENDANCE_PAUSED keeps official/club RSVPs; GUIDELINES_PAUSED releases them too
    return(PauseImpact): events per bucket, soonest first; empty for an archived user
    """
    impact = PauseImpact()
    if user.is_archived:
        return impact
    impact.stripped_roles = list(elevated_roles(user).values_list("name", flat=True))
    impact.clears_whatsapp = user.has_joined_whatsapp
    impact.rescinded_invites = list(
        Event.objects.filter(cohost_invites__in=_pending_cohost_invites(user)).order_by(
            "start_datetime"
        )
    )
    for event in upcoming_hosted_events(user).order_by("start_datetime"):
        if event.host_count > 1:
            impact.removed_hosting.append(event)
        else:
            impact.drafted_events.append(event)

    # Drafting settles every RSVP on the event, so the user's own isn't listed as removed too.
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
        kept = _keeps_official_rsvps(pause) and event.event_type in KEPT_RSVP_EVENT_TYPES
        (impact.kept_rsvps if kept else impact.removed_rsvps).append(event)
    return impact


def apply_attendance_pause(request, user: User) -> PauseImpact:
    """Attendance-pause the user, drop their other-type RSVPs and release every host spot.

    param(request): the triggering request, for audit and promoted-member email logging
    param(user): the member to pause
    return(PauseImpact): the impact as it stood when the pause was applied
    """
    with transaction.atomic():
        impact, details = release_held_events(request, user, MembershipStatus.ATTENDANCE_PAUSED)
        user.save(update_fields=user.apply_attendance_pause(by=getattr(request, "auth", None)))
        audit_log(
            logging.WARNING,
            "user_attendance_paused",
            request,
            target=AuditTarget(type=AuditTargetType.USER, id=str(user.pk), details=details),
        )
    return impact


@transaction.atomic
def release_held_events(request, user: User, pause: MembershipStatus) -> tuple[PauseImpact, dict]:
    """Release the user's upcoming RSVPs and host spots and strip their elevated roles.

    param(request): the triggering request, for promoted-member email logging
    param(user): the member being paused
    param(pause): the pause being applied, which decides whether official/club RSVPs stay
    return(tuple[PauseImpact, dict]): the impact and its audit details
    """
    if user.is_archived:
        # Archiving already released them; a pause now must not draft their solo-hosted events.
        return PauseImpact(), {}
    impact = pause_impact(user, pause)
    drafted_ids = [e.pk for e in impact.drafted_events]
    for event in impact.drafted_events:
        _move_to_draft(event, user)
    # A kept RSVP on a draft stays as-is; releasing it would promote that draft's waitlist.
    release_q = ~Q(pk__in=drafted_ids)
    if _keeps_official_rsvps(pause):
        release_q &= ~KEPT_RSVP_EVENT_Q
    release_upcoming_rsvps(request, user, CancelReason.PAUSE, release_q)
    step_down_as_cohost(user, impact.removed_hosting)
    _pending_cohost_invites(user).update(
        status=CoHostInviteStatus.RESCINDED, decided_at=timezone.now()
    )
    details = {
        "removed_role_ids": strip_elevated_roles(user),
        "removed_rsvp_event_ids": [str(e.pk) for e in impact.removed_rsvps],
        "removed_hosting_event_ids": [str(e.pk) for e in impact.removed_hosting],
        "drafted_event_ids": [str(e.pk) for e in impact.drafted_events],
    }
    return impact, details


def _pending_cohost_invites(user: User):
    return EventCoHostInvite.objects.filter(
        upcoming_events_q("event__"), user=user, status=CoHostInviteStatus.PENDING
    )


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
    rsvps.exclude(_PAID_OR_MARKED_RSVP_Q).delete()
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


def apply_attendance_pause_patch(request, user: User, attendance_paused: bool | None) -> bool:
    """Attendance-pause the user when the PATCH asks; returns True if it did."""
    if not attendance_paused or user.is_attendance_paused:
        return False
    apply_attendance_pause(request, user)
    return True
