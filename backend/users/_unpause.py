from functools import partial

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from notifications.email_sender import get_email_sender, send_best_effort
from notifications.unpaused_email import send_unpaused_email

from users.models import User


def has_pause(user: User) -> bool:
    return user.is_paused or user.attendance_paused_at is not None


def mark_unpaused(user: User) -> None:
    """Stamp the unpause, mark them out of the WhatsApp until they attend, and email after commit."""
    user.unpaused_at = timezone.now()
    user.has_joined_whatsapp = False
    user.save(update_fields=["unpaused_at", "has_joined_whatsapp"])
    if user.email and not user.archived_at:
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
