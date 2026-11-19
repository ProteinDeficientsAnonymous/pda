from datetime import datetime, timedelta

from django.db.models import F, Q, QuerySet
from django.utils import timezone
from notifications.email_helpers import format_eastern_datetime
from notifications.email_sender import EmailSender, send_best_effort
from notifications.rsvp_deadline_email import (
    RsvpDeadlineReminderEmailDetails,
    send_rsvp_deadline_reminder_email,
)
from users.models import HAS_EMAIL, SIGN_IN_STATUSES, MembershipStatus, PublicRsvpToken, User

from community.models import EventRSVP, EventStatus, RSVPStatus
from community.rsvps.public_shared import event_page_url, manage_rsvp_url

REMINDER_LEAD = timedelta(hours=24)


def _reachable_users() -> QuerySet[User]:
    # Archived and guidelines-paused people keep rsvps on cancelled events, which can be uncancelled.
    return User.objects.filter(HAS_EMAIL, is_active=True, archived_at__isnull=True).exclude(
        membership_status=MembershipStatus.GUIDELINES_PAUSED
    )


def _not_reminded_for_current_deadline() -> Q:
    # A reminder sent before this deadline's window was for an earlier deadline, so a moved one re-sends.
    window_start = F("event__rsvp_deadline") - REMINDER_LEAD
    return Q(rsvp_deadline_reminder_sent_at__isnull=True) | Q(
        rsvp_deadline_reminder_sent_at__lt=window_start
    )


def due_deadline_reminders(now: datetime) -> QuerySet[EventRSVP]:
    return EventRSVP.objects.filter(
        _not_reminded_for_current_deadline(),
        status=RSVPStatus.MAYBE,
        event__status=EventStatus.ACTIVE,
        event__rsvp_enabled=True,
        event__rsvp_deadline__gt=now,
        event__rsvp_deadline__lte=now + REMINDER_LEAD,
        user__in=_reachable_users(),
    ).select_related("event", "user")


def _claim(rsvp: EventRSVP, now: datetime) -> bool:
    """The conditional update lets exactly one overlapping cron run claim each rsvp."""
    claimed = EventRSVP.objects.filter(
        _not_reminded_for_current_deadline(), pk=rsvp.pk, status=RSVPStatus.MAYBE
    ).update(rsvp_deadline_reminder_sent_at=now)
    return claimed == 1


def _rsvp_url(rsvp: EventRSVP) -> str:
    if rsvp.user.membership_status in SIGN_IN_STATUSES:
        return event_page_url(rsvp.event)
    return manage_rsvp_url(PublicRsvpToken.issue_or_extend(rsvp.user).token)


def _send(sender: EmailSender, rsvp: EventRSVP, deadline: datetime) -> bool:
    return send_best_effort(
        lambda: send_rsvp_deadline_reminder_email(
            sender=sender,
            details=RsvpDeadlineReminderEmailDetails(
                to=rsvp.user.email or "",
                display_name=rsvp.user.first_name,
                event_title=rsvp.event.title,
                deadline=format_eastern_datetime(deadline),
                rsvp_url=_rsvp_url(rsvp),
            ),
        ),
        "rsvp_deadline_reminder",
    )


def send_due_deadline_reminders(sender: EmailSender) -> int:
    """Email every maybe whose event's rsvp deadline is within a day, once per rsvp; returns sends."""
    now = timezone.now()
    sent = 0
    for rsvp in due_deadline_reminders(now):
        deadline = rsvp.event.rsvp_deadline
        if deadline is not None and _claim(rsvp, now):
            sent += _send(sender, rsvp, deadline)
    return sent
