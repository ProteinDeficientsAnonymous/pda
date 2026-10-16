from django.conf import settings
from django.db.models import Q
from notifications._login_reminder_email import send_login_reminder_email
from notifications.email_sender import EmailSender
from users._helpers import _create_magic_token
from users.models import User

# onboarded_at also excludes members mid password reset, which re-flags needs_onboarding.
_NOT_SET_UP = Q(needs_onboarding=True, onboarded_at__isnull=True, email__isnull=False) & ~Q(
    email=""
)


def login_reminder_recipients() -> list[User]:
    return [
        *User.objects.active_members().filter(_NOT_SET_UP),
        *User.objects.active_tentative_members().filter(_NOT_SET_UP),
    ]


def send_login_reminders(sender: EmailSender) -> tuple[int, int]:
    """Email each member who hasn't finished first login a fresh magic link.

    return(tuple[int, int]): (sent, failed) counts
    """
    sent = failed = 0
    for user in login_reminder_recipients():
        token = _create_magic_token(user)
        result = send_login_reminder_email(
            sender=sender,
            to=user.email,
            display_name=user.first_name,
            magic_link_url=f"{settings.FRONTEND_BASE_URL}/magic-login/{token}",
        )
        if result.success:
            sent += 1
        else:
            failed += 1
    return sent, failed
