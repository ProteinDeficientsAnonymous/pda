import logging
from datetime import date

from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef
from django.utils import timezone
from notifications.attendance_reminder_email import send_attendance_reminder_email
from notifications.email_sender import get_email_sender
from users.member_search import with_second_last_qualifying_at
from users.models import User

from community.attendance.analytics import qualifying_event_q
from community.attendance.clock import anchor_from, latest_due_milestone, milestone_due_date
from community.models import AttendanceMilestone, AttendanceReminder, EventRSVP, RSVPStatus

logger = logging.getLogger(__name__)


def _anchor(user: User) -> date:
    """Clock runs from the 2nd-latest counting event, so m12 lands when they drop under 2."""
    second_last = user.second_last_qualifying_at
    return anchor_from(
        user.date_joined.date(),
        second_last.date() if second_last else None,
        user.attendance_grace_until,
    )


def _without_upcoming_rsvp(members):
    upcoming = EventRSVP.objects.filter(
        qualifying_event_q(),
        user=OuterRef("pk"),
        status=RSVPStatus.ATTENDING,
        event__start_datetime__gte=timezone.now(),
    )
    return members.exclude(Exists(upcoming))


class Command(BaseCommand):
    help = "Send 2-event attendance-reminder emails at 10/11/11.5/12 months on each member's clock."

    def handle(self, *args, **options):
        today = timezone.now().date()
        sender = get_email_sender()
        sent_count = 0
        failed_count = 0

        members = _without_upcoming_rsvp(
            User.objects.active_members().filter(email__isnull=False).exclude(email="")
        )
        already_sent = set(
            AttendanceReminder.objects.filter(user__in=members).values_list(
                "user_id", "milestone", "anchor_date"
            )
        )
        for user in with_second_last_qualifying_at(members):
            due = latest_due_milestone(_anchor(user), today)
            if due is None or (user.pk, due.milestone, due.anchor_date) in already_sent:
                continue

            result = send_attendance_reminder_email(
                sender=sender,
                to=user.email,
                display_name=user.first_name,
                milestone=due.milestone,
                deadline=milestone_due_date(due.anchor_date, AttendanceMilestone.M12),
            )
            if not result.success:
                failed_count += 1
                continue
            AttendanceReminder.objects.create(
                user=user, milestone=due.milestone, anchor_date=due.anchor_date
            )
            sent_count += 1

        logger.info(
            "send_attendance_reminders: sent %d reminder(s), %d failed", sent_count, failed_count
        )
        summary = f"Sent {sent_count} reminder(s); {failed_count} failed."
        style = self.style.WARNING if failed_count else self.style.SUCCESS
        self.stdout.write(style(summary))
