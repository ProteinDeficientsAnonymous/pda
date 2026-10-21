import logging
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from notifications._email_helpers import format_eastern_datetime, send_weekly_digest_email
from notifications.email_sender import EmailStream, get_email_sender
from users.models import HAS_EMAIL, User

from community._login_reminder import send_login_reminders
from community.models import Event, EventStatus, EventType

logger = logging.getLogger(__name__)


def _format_event_when(event: Event) -> str:
    if event.datetime_tbd or event.start_datetime is None:
        return "to be decided"
    return format_eastern_datetime(event.start_datetime)


def veganniversary_groups(*, now, users) -> list[dict]:
    today = timezone.localtime(now).date()
    if today.day > 7:
        return []
    grouped: dict[int, list[dict]] = defaultdict(list)
    for user in users:
        if user.veganniversary_month != today.month:
            continue
        years = today.year - user.veganniversary_year
        if years < 1:
            continue
        grouped[years].append(
            {
                "name": user.first_name,
                "url": f"{settings.FRONTEND_BASE_URL}/members/{user.pk}",
            }
        )
    return [
        {"label": "1 year" if y == 1 else f"{y} years", "people": people}
        for y, people in sorted(grouped.items(), reverse=True)
    ]


def _with_email(users):
    return users.filter(HAS_EMAIL, weekly_digest_opt_out=False)


class Command(BaseCommand):
    help = (
        "Remind anyone who hasn't finished first login, then email active and "
        "tentative members a digest of upcoming events and this month's veganniversaries."
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

    def _send_all(self, sender, recipients, payload: dict) -> tuple[int, int]:
        sent = failed = 0
        for user in recipients:
            result = send_weekly_digest_email(
                sender=sender,
                to=user.email,
                display_name=user.first_name,
                **payload,
            )
            if result.success:
                sent += 1
            else:
                failed += 1
        return sent, failed

    def handle(self, *args, **options):
        # Reminders go first so a digest failure can't skip them.
        if not options["to"]:
            self._send_login_reminders()
        self._send_digest(options)

    def _send_login_reminders(self) -> None:
        sent, failed = send_login_reminders(get_email_sender())
        logger.info("send_weekly_digest: sent %d login reminder(s), %d failed", sent, failed)
        style = self.style.WARNING if failed else self.style.SUCCESS
        self.stdout.write(style(f"Sent {sent} login reminder(s); {failed} failed."))

    def _send_digest(self, options) -> None:
        now = timezone.now()
        upcoming = Event.objects.filter(
            status=EventStatus.ACTIVE,
            event_type__in=(EventType.OFFICIAL, EventType.CLUB),
            deleted_at__isnull=True,
            start_datetime__gte=now,
            start_datetime__lt=now + timedelta(days=7),
        ).order_by("start_datetime")

        events = [
            {
                "title": event.title,
                "when": _format_event_when(event),
                "url": f"{settings.FRONTEND_BASE_URL}/events/{event.slug or event.pk}",
            }
            for event in upcoming
        ]
        groups = veganniversary_groups(
            now=now,
            users=User.objects.active_members()
            .filter(
                veganniversary_month__isnull=False,
                veganniversary_year__isnull=False,
                veganniversary_shoutout_opt_in=True,
            )
            .exclude(first_name=""),
        )
        if not events and not groups:
            logger.info("send_weekly_digest: no upcoming events or veganniversaries, skipped")
            self.stdout.write(self.style.SUCCESS("Nothing to send; sent 0 digest(s)."))
            return

        payload = {
            "events": events,
            "urls": {
                "calendar_url": f"{settings.FRONTEND_BASE_URL}/calendar",
                "settings_url": f"{settings.FRONTEND_BASE_URL}/settings",
            },
            "veganniversaries": groups,
        }
        sender = get_email_sender(EmailStream.BULK)
        if options["to"]:
            self._send_test(sender, options["to"], payload)
            return

        sent_count, failed_count = self._send_all(
            sender, _with_email(User.objects.active_members()), payload
        )
        if events:
            # Shoutouts link to member profiles, which tentative members can't open.
            tentative_sent, tentative_failed = self._send_all(
                sender,
                _with_email(User.objects.active_tentative_members()),
                {**payload, "veganniversaries": []},
            )
            sent_count += tentative_sent
            failed_count += tentative_failed

        logger.info("send_weekly_digest: sent %d digest(s), %d failed", sent_count, failed_count)
        summary = f"Sent {sent_count} digest(s); {failed_count} failed."
        style = self.style.WARNING if failed_count else self.style.SUCCESS
        self.stdout.write(style(summary))
