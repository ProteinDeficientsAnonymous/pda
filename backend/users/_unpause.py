from functools import partial

from django.conf import settings
from django.db import transaction
from notifications.email_sender import get_email_sender, send_best_effort
from notifications.unpaused_email import send_unpaused_email

from users.models import User


def email_unpaused(user: User) -> None:
    if user.email and not user.is_archived:
        transaction.on_commit(partial(_send, user.email, user.first_name), robust=True)


def _send(to: str, display_name: str) -> None:
    send_best_effort(
        lambda: send_unpaused_email(
            sender=get_email_sender(),
            to=to,
            display_name=display_name,
            calendar_url=f"{settings.FRONTEND_BASE_URL}/calendar",
        ),
        "unpaused_email",
    )
