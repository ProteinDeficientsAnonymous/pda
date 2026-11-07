from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


def send_unpaused_email(
    *, sender: EmailSender, to: str, display_name: str, whatsapp_url: str
) -> SendResult:
    context = {"display_name": display_name or "", "whatsapp_url": whatsapp_url}
    html = render_to_string("emails/unpaused.html", context)
    text = render_to_string("emails/unpaused.txt", context)
    return sender.send(to=to, subject="you're back in at pda", html=html, text=text)
