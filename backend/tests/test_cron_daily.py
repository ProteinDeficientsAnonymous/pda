import re

from django.conf import settings
from django.core.management import get_commands

# Each runs from its own Railway cron service, or (attendance reminders, #1380) is off on purpose.
SCHEDULED_ELSEWHERE = {
    "send_attendance_reminders",
    "send_checkin_nudges",
    "send_monthly_digest",
    "send_weekly_digest",
}


def test_every_send_command_is_scheduled():
    cron = (settings.BASE_DIR.parent / "scripts" / "cron_daily.sh").read_text()
    in_cron = set(re.findall(r"manage\.py (\w+)", cron))
    send_commands = {name for name in get_commands() if name.startswith("send_")}

    assert send_commands - SCHEDULED_ELSEWHERE <= in_cron
    assert SCHEDULED_ELSEWHERE <= send_commands
