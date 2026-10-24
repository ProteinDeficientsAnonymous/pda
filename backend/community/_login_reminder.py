from datetime import UTC, datetime, timedelta

from django.db import transaction
from django.db.models import Count, Exists, Max, OuterRef, Q, QuerySet
from django.utils import timezone
from notifications._email_helpers import LoginLinkEmail, send_magic_login_email
from notifications.email_sender import EmailSender
from users._helpers import _magic_login_url
from users.models import HAS_EMAIL, MagicLoginToken, MagicLoginTokenSource, User

from community.models import LoginReminder

# Gaps sit just under a week / four weeks so a drifting weekly cron still sends, but a rerun doesn't.
_WEEKLY_GAP = timedelta(days=6)
_MONTHLY_GAP = timedelta(days=27)
_WEEKLY_REMINDERS = 4

# Members created before onboarded_at existed never got it set, so their resets re-flag needs_onboarding.
_ONBOARDED_AT_TRACKED_SINCE = datetime(2026, 4, 26, tzinfo=UTC)
NOT_SET_UP = Q(needs_onboarding=True, onboarded_at__isnull=True) & (
    Q(last_login__isnull=True) | Q(created_at__gte=_ONBOARDED_AT_TRACKED_SINCE)
)

_REMINDER_EMAIL = LoginLinkEmail("login_reminder", "finish setting up your pda account")


def _due_for_reminder(qs: QuerySet, now: datetime) -> QuerySet:
    recent_admin_link = MagicLoginToken.objects.filter(
        user=OuterRef("pk"), used=False, created_at__gte=now - _WEEKLY_GAP
    ).exclude(source=MagicLoginTokenSource.REMINDER)
    return (
        qs.filter(NOT_SET_UP, HAS_EMAIL)
        .exclude(Exists(recent_admin_link))
        .annotate(
            reminder_count=Count("login_reminders", distinct=True),
            last_reminded_at=Max("login_reminders__sent_at"),
        )
        .filter(
            Q(last_reminded_at__isnull=True)
            | Q(reminder_count__lt=_WEEKLY_REMINDERS, last_reminded_at__lt=now - _WEEKLY_GAP)
            | Q(last_reminded_at__lt=now - _MONTHLY_GAP)
        )
    )


def _users_to_remind(now: datetime) -> list[User]:
    return [
        user
        for qs in (User.objects.active_members(), User.objects.active_tentative_members())
        for user in _due_for_reminder(qs, now)
    ]


def _claim(user: User, now: datetime) -> LoginReminder | None:
    # Recording before sending, under a row lock, stops an overlapping run from double-sending.
    with transaction.atomic():
        User.objects.select_for_update().filter(pk=user.pk).first()
        if not _due_for_reminder(User.objects.filter(pk=user.pk), now).exists():
            return None
        return LoginReminder.objects.create(user=user)


def _send_reminder(sender: EmailSender, user: User, reminder: LoginReminder) -> bool:
    link = MagicLoginToken.create_for_user(user, source=MagicLoginTokenSource.REMINDER)
    result = send_magic_login_email(
        sender=sender,
        to=user.email,
        display_name=user.first_name,
        magic_link_url=_magic_login_url(str(link.token)),
        email=_REMINDER_EMAIL,
    )
    if not result.success:
        link.used = True
        link.save(update_fields=["used"])
        reminder.delete()
        return False
    # Only earlier reminder links: admin-texted links must keep working.
    MagicLoginToken.objects.filter(
        user=user, used=False, source=MagicLoginTokenSource.REMINDER
    ).exclude(pk=link.pk).update(used=True)
    return True


def send_login_reminders(sender: EmailSender) -> tuple[int, int]:
    """Email a fresh login link to every member who hasn't finished first login.

    return(tuple[int, int]): (sent, failed) counts
    """
    now = timezone.now()
    sent = failed = 0
    for user in _users_to_remind(now):
        reminder = _claim(user, now)
        if reminder is None:
            continue
        if _send_reminder(sender, user, reminder):
            sent += 1
        else:
            failed += 1
    return sent, failed
