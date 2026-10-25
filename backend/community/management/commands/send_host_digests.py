import logging
from collections import Counter
from enum import StrEnum

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications._host_digest_email import send_host_digest_email
from notifications.email_sender import EmailStream, get_email_sender, mask_recipient
from users.models import User

from community._host_digest import build_host_digest, digest_recipients

logger = logging.getLogger(__name__)


class _Outcome(StrEnum):
    SENT = "sent"
    FAILED = "failed"
    IDLE = "idle"


class Command(BaseCommand):
    help = "Email each event host a daily summary of new rsvps and comments on their events."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="list recipients and events only"
        )

    def handle(self, *args, **options):
        # Captured once so activity during the run lands in the next window.
        run_started_at = timezone.now()
        if options["dry_run"]:
            self._dry_run(run_started_at)
            return
        self._send_all(run_started_at)

    def _dry_run(self, run_started_at) -> None:
        for host in digest_recipients(run_started_at):
            digest = build_host_digest(host, run_started_at)
            if digest is not None:
                titles = ", ".join(event.title for event in digest.events)
                self.stdout.write(f"{mask_recipient(host.email)}: {titles}")

    def _send_one(self, host: User, sender, run_started_at, settings_url: str) -> _Outcome:
        digest = build_host_digest(host, run_started_at)
        if digest is not None:
            result = send_host_digest_email(
                sender=sender,
                to=host.email,
                display_name=host.first_name,
                events=digest.events,
                settings_url=settings_url,
            )
            if not result.success:
                return _Outcome.FAILED
        User.objects.filter(pk=host.pk).update(host_digest_last_sent_at=run_started_at)
        return _Outcome.IDLE if digest is None else _Outcome.SENT

    def _send_all(self, run_started_at) -> None:
        settings_url = f"{settings.FRONTEND_BASE_URL}/settings"
        sender = get_email_sender(EmailStream.BULK)
        counts: Counter[_Outcome] = Counter()
        for host in digest_recipients(run_started_at):
            try:
                counts[self._send_one(host, sender, run_started_at, settings_url)] += 1
            except Exception:
                # One bad host shouldn't block everyone after it, every day.
                logger.exception("send_host_digests: host %s failed", host.pk)
                counts[_Outcome.FAILED] += 1

        sent, failed, idle = (counts[o] for o in (_Outcome.SENT, _Outcome.FAILED, _Outcome.IDLE))
        logger.info("send_host_digests: sent %d, %d failed, %d idle", sent, failed, idle)
        summary = f"Sent {sent} host digest(s); {failed} failed; {idle} with no activity."
        style = self.style.WARNING if failed else self.style.SUCCESS
        self.stdout.write(style(summary))
