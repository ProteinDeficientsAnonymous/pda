from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


def send_login_reminder_email(
    *,
    sender: EmailSender,
    to: str,
    display_name: str,
    magic_link_url: str,
) -> SendResult:
    """Render and send the weekly "your account isn't set up yet" reminder."""
    context = {
        "display_name": display_name or "",
        "magic_link_url": magic_link_url,
    }
    html = render_to_string("emails/login_reminder.html", context)
    text = render_to_string("emails/login_reminder.txt", context)
    return sender.send(
        to=to,
        subject="finish setting up your pda account",
        html=html,
        text=text,
    )
