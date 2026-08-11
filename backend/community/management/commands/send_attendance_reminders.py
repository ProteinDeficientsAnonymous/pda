import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications._attendance_reminder_email import send_attendance_reminder_email
from notifications.email_sender import get_email_sender
from users.models import User

from community._attendance_clock import compute_anchor, latest_due_milestone
from community.models import AttendanceReminder, FeatureFlag, flag_enabled

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send 10/11/11.5/12-month attendance-reminder emails to active members."

    def handle(self, *args, **options):
        if not flag_enabled(FeatureFlag.ADMIN_ATTENDANCE_ANALYTICS):
            return

        today = timezone.now().date()
        calendar_url = f"{settings.FRONTEND_BASE_URL}/calendar"
        sender = get_email_sender()
        sent_count = 0
        failed_count = 0

        for user in User.objects.active_members().filter(email__isnull=False).exclude(email=""):
            anchor = compute_anchor(user, today)
            due = latest_due_milestone(anchor, today)
            if due is None:
                continue
            if AttendanceReminder.objects.filter(
                user=user, milestone=due.milestone, anchor_date=due.anchor_date
            ).exists():
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
