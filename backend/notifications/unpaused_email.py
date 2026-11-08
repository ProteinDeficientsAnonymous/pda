from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


def send_unpaused_email(
    *, sender: EmailSender, to: str, display_name: str, calendar_url: str
) -> SendResult:
    context = {"display_name": display_name or "", "calendar_url": calendar_url}
    html = render_to_string("emails/unpaused.html", context)
    text = render_to_string("emails/unpaused.txt", context)
    return sender.send(to=to, subject="your pda account is unpaused", html=html, text=text)
