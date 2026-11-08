from functools import partial

from community.models import WhatsAppLinkConfig
from django.db import transaction
from notifications.email_sender import get_email_sender, send_best_effort
from notifications.unpaused_email import send_unpaused_email

from users.models import User


def email_whatsapp_link_on_unpause(user: User) -> None:
    """Send once the unpause commits, so a failed send can't undo it."""
    if user.archived_at or user.attendance_paused_at or user.whatsapp_reminder_opt_out:
        return
    if user.email:
        transaction.on_commit(partial(_send, user.email, user.first_name), robust=True)


def _send(to: str, display_name: str) -> None:
    whatsapp_url = WhatsAppLinkConfig.get().link
    if not whatsapp_url:
        return
    send_best_effort(
        lambda: send_unpaused_email(
            sender=get_email_sender(), to=to, display_name=display_name, whatsapp_url=whatsapp_url
        ),
        "unpaused_email",
    )
