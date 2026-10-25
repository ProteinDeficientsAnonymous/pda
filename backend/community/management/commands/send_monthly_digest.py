import logging
from datetime import datetime, time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from notifications._digest_emails import send_monthly_digest_email
from notifications.email_sender import EmailStream, get_email_sender
from users.models import User

from community._digest import (
    digest_events,
    digest_recipients,
    digest_urls,
    send_digest_to_all,
    shoutout_members,
    veganniversary_groups,
)

logger = logging.getLogger(__name__)


def _start_of_next_month(today) -> datetime:
    year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    return datetime.combine(
        today.replace(year=year, month=month, day=1), time.min, tzinfo=settings.COMMUNITY_TZ
    )


class Command(BaseCommand):
    help = (
        "On the 1st of the month, email active and tentative members this month's "
        "upcoming events and members this month's veganniversaries. Runs from the daily cron."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            help="send one digest to this address now, whatever the date (provider smoke test)",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        today = timezone.localtime(now, settings.COMMUNITY_TZ).date()
        if today.day != 1 and not options["to"]:
            self.stdout.write(self.style.SUCCESS("Not the 1st; sent 0 monthly digest(s)."))
            return

        events = digest_events(start=now, end=_start_of_next_month(today))
        groups = veganniversary_groups(today=today, users=shoutout_members())
        if not events and not groups:
            logger.info("send_monthly_digest: no events or veganniversaries, skipped")
            self.stdout.write(self.style.SUCCESS("Nothing to send; sent 0 monthly digest(s)."))
            return

        payload = {
            "month": today.strftime("%B"),
            "events": events,
            "urls": digest_urls(),
            "veganniversaries": groups,
        }
        sender = get_email_sender(EmailStream.BULK)
        if options["to"]:
            self._send_test(sender, options["to"], payload)
            return

        sent_count, failed_count = send_digest_to_all(
            send_monthly_digest_email,
            sender,
            digest_recipients(User.objects.active_members()),
            payload,
        )
        if events:
            # Shoutouts link to member profiles, which tentative members can't open.
            tentative_sent, tentative_failed = send_digest_to_all(
                send_monthly_digest_email,
                sender,
                digest_recipients(User.objects.active_tentative_members()),
                {**payload, "veganniversaries": []},
            )
            sent_count += tentative_sent
            failed_count += tentative_failed

        logger.info("send_monthly_digest: sent %d digest(s), %d failed", sent_count, failed_count)
        style = self.style.WARNING if failed_count else self.style.SUCCESS
        self.stdout.write(style(f"Sent {sent_count} monthly digest(s); {failed_count} failed."))

    def _send_test(self, sender, to: str, payload: dict) -> None:
        user = User.objects.filter(email__iexact=to).first()
        result = send_monthly_digest_email(
            sender=sender,
            to=to,
            display_name=user.first_name if user else "",
            **payload,
        )
        if not result.success:
            raise CommandError(f"test monthly digest failed: {result.error}")
        self.stdout.write(
            self.style.SUCCESS(
                f"Sent 1 test monthly digest (message id: {result.provider_message_id})."
            )
        )
