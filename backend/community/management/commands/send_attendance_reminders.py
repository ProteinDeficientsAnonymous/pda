import logging
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications._attendance_reminder_email import send_attendance_reminder_email
from notifications.email_sender import get_email_sender
from users._member_search import with_last_qualifying_at
from users.models import User

from community._attendance_clock import anchor_from, latest_due_milestone
from community.models import AttendanceReminder

logger = logging.getLogger(__name__)


def _anchor(user: User) -> date:
    last = user.last_qualifying_at
    return anchor_from(user.date_joined.date(), last.date() if last else None)


class Command(BaseCommand):
    help = "Send 10/11/11.5/12-month attendance-reminder emails to active members."

    def handle(self, *args, **options):
        today = timezone.now().date()
        calendar_url = f"{settings.FRONTEND_BASE_URL}/calendar"
        sender = get_email_sender()
        sent_count = 0
        failed_count = 0

        members = User.objects.active_members().filter(email__isnull=False).exclude(email="")
        already_sent = set(
            AttendanceReminder.objects.filter(user__in=members).values_list(
                "user_id", "milestone", "anchor_date"
            )
        )
        for user in with_last_qualifying_at(members):
            due = latest_due_milestone(_anchor(user), today)
            if due is None or (user.pk, due.milestone, due.anchor_date) in already_sent:
                continue

            result = send_attendance_reminder_email(
                sender=sender,
                to=user.email,
                display_name=user.first_name,
                calendar_url=calendar_url,
                milestone=due.milestone,
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
