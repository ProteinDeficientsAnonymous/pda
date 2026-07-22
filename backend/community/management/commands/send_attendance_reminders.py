"""Management command to send attendance-milestone reminder emails.

Schedule this via Railway cron (dashboard-configured) to run daily, e.g.:
  python manage.py send_attendance_reminders
"""

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

        for user in User.objects.active_members().filter(email__isnull=False).exclude(email=""):
            anchor = compute_anchor(user, today)
            due = latest_due_milestone(anchor, today)
            if due is None:
                continue
            if AttendanceReminder.objects.filter(
                user=user, milestone=due.milestone, anchor_date=due.anchor_date
            ).exists():
                continue

            send_attendance_reminder_email(
                sender=sender,
                to=user.email,
                display_name=user.first_name,
                calendar_url=calendar_url,
                milestone=due.milestone,
            )
            AttendanceReminder.objects.create(
                user=user, milestone=due.milestone, anchor_date=due.anchor_date
            )
            sent_count += 1

        logger.info("send_attendance_reminders: sent %d reminder(s)", sent_count)
        self.stdout.write(self.style.SUCCESS(f"Sent {sent_count} reminder(s)."))
