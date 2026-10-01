import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count, Max
from django.utils import timezone
from notifications._email_helpers import send_whatsapp_join_reminder_email
from notifications.email_sender import EmailStream, get_email_sender
from users.models import User

from community._whatsapp_join_reminder import due_reminder_number
from community.models import FeatureFlag, WhatsAppJoinReminder, WhatsAppLinkConfig, flag_enabled

logger = logging.getLogger(__name__)


def _recipients():
    return (
        User.objects.active_members()
        .filter(
            has_joined_whatsapp=False,
            whatsapp_reminder_opt_out=False,
            email__isnull=False,
        )
        .exclude(email="")
        .annotate(
            reminder_count=Count("whatsapp_join_reminders"),
            last_reminder_at=Max("whatsapp_join_reminders__sent_at"),
        )
    )


class Command(BaseCommand):
    help = "Nudge active members who haven't joined the WhatsApp group yet."

    def handle(self, *args, **options):
        if not flag_enabled(FeatureFlag.WHATSAPP_JOIN_REMINDERS):
            return

        whatsapp_url = WhatsAppLinkConfig.get().link
        if not whatsapp_url:
            logger.warning("send_whatsapp_join_reminders: no whatsapp link configured, skipped")
            self.stdout.write(
                self.style.WARNING("No WhatsApp link configured; sent 0 reminder(s).")
            )
            return

        today = timezone.now().date()
        settings_url = f"{settings.FRONTEND_BASE_URL}/settings"
        sender = get_email_sender(EmailStream.BULK)
        sent_count = 0
        failed_count = 0

        for user in _recipients():
            number = due_reminder_number(
                joined_on=user.created_at.date(),
                sent_count=user.reminder_count,
                last_sent_on=user.last_reminder_at.date() if user.last_reminder_at else None,
                today=today,
            )
            if number is None:
                continue

            result = send_whatsapp_join_reminder_email(
                sender=sender,
                to=user.email,
                display_name=user.first_name,
                whatsapp_url=whatsapp_url,
                settings_url=settings_url,
            )
            if not result.success:
                failed_count += 1
                continue
            WhatsAppJoinReminder.objects.create(user=user, reminder_number=number)
            sent_count += 1

        logger.info(
            "send_whatsapp_join_reminders: sent %d reminder(s), %d failed", sent_count, failed_count
        )
        summary = f"Sent {sent_count} reminder(s); {failed_count} failed."
        style = self.style.WARNING if failed_count else self.style.SUCCESS
        self.stdout.write(style(summary))
