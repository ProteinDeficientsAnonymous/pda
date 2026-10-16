import logging
from datetime import datetime, timedelta

from django.db.models import Count, Max, Q, QuerySet
from django.utils import timezone
from notifications._email_helpers import LoginLinkEmail, send_magic_login_email
from notifications.email_sender import EmailSender
from users._helpers import _create_magic_token, _magic_login_url
from users.models import HAS_EMAIL, MagicLoginToken, MagicLoginTokenSource, User

from community.models import LoginReminder

logger = logging.getLogger(__name__)

MAX_REMINDERS = 4
# Under a week so a drifting weekly cron still sends, but a same-week rerun doesn't.
_REMINDER_GAP = timedelta(days=6)

# onboarded_at also excludes members mid password reset, which re-flags needs_onboarding.
_NOT_SET_UP = Q(needs_onboarding=True, onboarded_at__isnull=True)

_REMINDER_EMAIL = LoginLinkEmail("login_reminder", "finish setting up your pda account")
_FINAL_EMAIL = LoginLinkEmail(
    "login_reminder_final", "last reminder: set up your pda account or lose your membership"
)


def _not_reminded_since(qs: QuerySet, cutoff: datetime) -> QuerySet:
    return (
        qs.filter(_NOT_SET_UP)
        .annotate(
            reminders_sent=Count("login_reminders", distinct=True),
            last_reminded_at=Max("login_reminders__sent_at"),
        )
        .filter(Q(last_reminded_at__isnull=True) | Q(last_reminded_at__lt=cutoff))
    )


def _not_set_up_users(cutoff: datetime, *conditions: Q) -> list[User]:
    return [
        *_not_reminded_since(User.objects.active_members(), cutoff).filter(*conditions),
        *_not_reminded_since(User.objects.active_tentative_members(), cutoff).filter(*conditions),
    ]


def _is_final(user: User) -> bool:
    return user.reminders_sent == MAX_REMINDERS - 1 and not user.has_joined_whatsapp


def _send_reminder(sender: EmailSender, user: User) -> bool:
    token = _create_magic_token(user, source=MagicLoginTokenSource.REMINDER)
    result = send_magic_login_email(
        sender=sender,
        to=user.email,
        display_name=user.first_name,
        magic_link_url=_magic_login_url(token),
        email=_FINAL_EMAIL if _is_final(user) else _REMINDER_EMAIL,
    )
    unused = MagicLoginToken.objects.filter(user=user, used=False)
    if not result.success:
        unused.filter(token=token).update(used=True)
        return False
    unused.exclude(token=token).update(used=True)
    LoginReminder.objects.create(user=user)
    return True


def _archive_unresponsive(cutoff: datetime) -> int:
    users = _not_set_up_users(
        cutoff, Q(reminders_sent__gte=MAX_REMINDERS), Q(has_joined_whatsapp=False)
    )
    for user in users:
        user.archived_at = timezone.now()
        user.save(update_fields=["archived_at"])
        # A re-approved member starts a fresh reminder cycle.
        LoginReminder.objects.filter(user=user).delete()
        logger.info("login_reminder: archived user=%s after %d reminders", user.pk, MAX_REMINDERS)
    return len(users)


def send_login_reminders(sender: EmailSender) -> tuple[int, int, int]:
    """Archive members whose reminders ran out, then remind everyone else not set up.

    return(tuple[int, int, int]): (sent, failed, archived) counts
    """
    cutoff = timezone.now() - _REMINDER_GAP
    archived = _archive_unresponsive(cutoff)
    sent = failed = 0
    for user in _not_set_up_users(cutoff, HAS_EMAIL, Q(reminders_sent__lt=MAX_REMINDERS)):
        if _send_reminder(sender, user):
            sent += 1
        else:
            failed += 1
    return sent, failed, archived
