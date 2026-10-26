import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from notifications._digest_emails import send_weekly_digest_email
from notifications.email_sender import EmailStream, get_email_sender
from users.models import User

from community._digest import (
    digest_events,
    digest_urls,
    send_digest_to_all,
    weekly_digest_recipients,
)
from community._login_reminder import send_login_reminders
from community._tentative_attendance_nudge import send_attendance_nudges

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Remind anyone who hasn't finished first login, nudge tentative members to come "
        "in person, then email active and tentative members a digest of upcoming events "
        "(on the 1st, only to monthly digest opt-outs)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            help="send one digest to this address instead of the membership (provider smoke test)",
        )

    def _send_test(self, sender, to: str, payload: dict) -> None:
        """Send one real digest to an explicit address so a provider swap can be verified live."""
        user = User.objects.filter(email__iexact=to).first()
        result = send_weekly_digest_email(
            sender=sender,
            to=to,
            display_name=user.first_name if user else "",
            **payload,
        )
        if not result.success:
            raise CommandError(f"test digest failed: {result.error}")
        logger.info("send_weekly_digest: test send succeeded id=%s", result.provider_message_id)
        self.stdout.write(
            self.style.SUCCESS(f"Sent 1 test digest (message id: {result.provider_message_id}).")
        )

    def handle(self, *args, **options):
        # Reminders go first so a digest failure can't skip them.
        if not options["to"]:
            self._send_login_reminders()
            self._send_attendance_nudges()
        self._send_digest(options)

    def _send_login_reminders(self) -> None:
        try:
            sent, failed = send_login_reminders(get_email_sender())
        except Exception:
            logger.exception("send_weekly_digest: login reminders failed")
            self.stderr.write(self.style.ERROR("Login reminders failed; sending digest anyway."))
            return
        logger.info("send_weekly_digest: sent %d login reminder(s), %d failed", sent, failed)
        style = self.style.WARNING if failed else self.style.SUCCESS
        self.stdout.write(style(f"Sent {sent} login reminder(s); {failed} failed."))

    def _send_attendance_nudges(self) -> None:
        try:
            sent, failed = send_attendance_nudges(get_email_sender(EmailStream.BULK))
        except Exception:
            logger.exception("send_weekly_digest: attendance nudges failed")
            self.stderr.write(self.style.ERROR("Attendance nudges failed; sending digest anyway."))
            return
        logger.info("send_weekly_digest: sent %d attendance nudge(s), %d failed", sent, failed)
        style = self.style.WARNING if failed else self.style.SUCCESS
        self.stdout.write(style(f"Sent {sent} attendance nudge(s); {failed} failed."))

    def _send_digest(self, options) -> None:
        now = timezone.now()
        events = digest_events(start=now, end=now + timedelta(days=7))
        if not events:
            logger.info("send_weekly_digest: no upcoming events, skipped")
            self.stdout.write(self.style.SUCCESS("Nothing to send; sent 0 digest(s)."))
            return

        payload = {"events": events, "urls": digest_urls()}
        sender = get_email_sender(EmailStream.BULK)
        if options["to"]:
            self._send_test(sender, options["to"], payload)
            return

        # On the 1st the monthly digest covers this week, so only its opt-outs get the weekly.
        first_of_month = timezone.localtime(now, settings.COMMUNITY_TZ).day == 1

        def recipients(users):
            users = weekly_digest_recipients(users)
            return users.filter(monthly_digest_opt_out=True) if first_of_month else users

        sent_count, failed_count = send_digest_to_all(
            send_weekly_digest_email,
            sender,
            recipients(User.objects.active_members()),
            payload,
        )
        tentative_sent, tentative_failed = send_digest_to_all(
            send_weekly_digest_email,
            sender,
            recipients(User.objects.active_tentative_members()),
            payload,
        )
        sent_count += tentative_sent
        failed_count += tentative_failed

        logger.info("send_weekly_digest: sent %d digest(s), %d failed", sent_count, failed_count)
        summary = f"Sent {sent_count} digest(s); {failed_count} failed."
        style = self.style.WARNING if failed_count else self.style.SUCCESS
        self.stdout.write(style(summary))
