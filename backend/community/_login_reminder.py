from datetime import datetime, timedelta

from django.db.models import Exists, Max, OuterRef, Q, QuerySet
from django.utils import timezone
from notifications._email_helpers import LoginLinkEmail, send_magic_login_email
from notifications.email_sender import EmailSender
from users._helpers import _create_magic_token, _magic_login_url
from users.models import HAS_EMAIL, MagicLoginToken, MagicLoginTokenSource, User

from community.models import LoginReminder

# Under a week so a drifting weekly cron still sends, but a same-week rerun doesn't.
_REMINDER_GAP = timedelta(days=6)

# last_login covers members from before onboarded_at existed, whose resets re-flag needs_onboarding.
_NOT_SET_UP = Q(needs_onboarding=True, onboarded_at__isnull=True, last_login__isnull=True)

_REMINDER_EMAIL = LoginLinkEmail("login_reminder", "finish setting up your pda account")


def _not_reminded_since(qs: QuerySet, cutoff: datetime) -> QuerySet:
    recent_admin_link = MagicLoginToken.objects.filter(
        user=OuterRef("pk"), used=False, created_at__gte=cutoff
    ).exclude(source=MagicLoginTokenSource.REMINDER)
    return (
        qs.filter(_NOT_SET_UP)
        .exclude(Exists(recent_admin_link))
        .annotate(last_reminded_at=Max("login_reminders__sent_at"))
        .filter(Q(last_reminded_at__isnull=True) | Q(last_reminded_at__lt=cutoff))
    )


def _users_to_remind(cutoff: datetime) -> list[User]:
    return [
        *_not_reminded_since(User.objects.active_members(), cutoff).filter(HAS_EMAIL),
        *_not_reminded_since(User.objects.active_tentative_members(), cutoff).filter(HAS_EMAIL),
    ]


def _send_reminder(sender: EmailSender, user: User) -> bool:
    token = _create_magic_token(user, source=MagicLoginTokenSource.REMINDER)
    result = send_magic_login_email(
        sender=sender,
        to=user.email,
        display_name=user.first_name,
        magic_link_url=_magic_login_url(token),
        email=_REMINDER_EMAIL,
    )
    reminder_links = MagicLoginToken.objects.filter(
        user=user, used=False, source=MagicLoginTokenSource.REMINDER
    )
    if not result.success:
        reminder_links.filter(token=token).update(used=True)
        return False
    # Only earlier reminder links: admin-texted links must keep working.
    reminder_links.exclude(token=token).update(used=True)
    LoginReminder.objects.create(user=user)
    return True


def send_login_reminders(sender: EmailSender) -> tuple[int, int]:
    """Email a fresh login link to every member who hasn't finished first login.

    return(tuple[int, int]): (sent, failed) counts
    """
    cutoff = timezone.now() - _REMINDER_GAP
    sent = failed = 0
    for user in _users_to_remind(cutoff):
        if _send_reminder(sender, user):
            sent += 1
        else:
            failed += 1
    return sent, failed
