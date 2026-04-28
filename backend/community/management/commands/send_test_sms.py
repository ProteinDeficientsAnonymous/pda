"""Dev-only management command to verify Twilio is wired up.

Usage:
    uv run python manage.py send_test_sms +15555550100 "hello from pda"

Trial Twilio accounts can only send to verified phone numbers — verify the
recipient in the Twilio console before running this. The command prints the
returned MessageSid on success and the API error on failure (no DB writes).
"""

from django.core.management.base import BaseCommand, CommandError

from community._sms import send_sms


class Command(BaseCommand):
    help = "Send a one-off SMS via Twilio to verify configuration."

    def add_arguments(self, parser) -> None:
        parser.add_argument("to", help="Recipient phone in E.164 (e.g. +15555550100).")
        parser.add_argument("body", help="Message body.")

    def handle(self, *args, to: str, body: str, **options) -> None:
        try:
            sid = send_sms(to, body)
        except RuntimeError as e:
            raise CommandError(str(e)) from e
        except Exception as e:  # noqa: BLE001 — surface any Twilio API error verbatim
            raise CommandError(f"Twilio send failed: {e}") from e
        self.stdout.write(f"sent ✓ MessageSid={sid}")
