from datetime import date, timedelta

# Give a new member a few days to join on their own before the first nudge.
GRACE_DAYS = 3
INTERVAL_DAYS = 14
MAX_REMINDERS = 3


def due_reminder_number(
    *,
    joined_on: date,
    sent_count: int,
    last_sent_on: date | None,
    today: date,
) -> int | None:
    """Which reminder number is due today for one member, or None if none is.

    param joined_on(date): when the member's account was created
    param sent_count(int): reminders already sent to them
    param last_sent_on(date | None): when the most recent one went out
    param today(date): the date the run is evaluating against
    return(int | None): the 1-based reminder number to send, or None
    """
    if sent_count >= MAX_REMINDERS:
        return None
    if last_sent_on is None:
        return 1 if today >= joined_on + timedelta(days=GRACE_DAYS) else None
    if today >= last_sent_on + timedelta(days=INTERVAL_DAYS):
        return sent_count + 1
    return None
