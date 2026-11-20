from dataclasses import dataclass

from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


@dataclass(frozen=True)
class DigestMail:
    display_name: str
    events: list[dict]
    urls: dict[str, str]


@dataclass(frozen=True)
class MonthlyDigestMail(DigestMail):
    month: str
    veganniversaries: list[dict] | None = None


def send_weekly_digest_email(
    *,
    sender: EmailSender,
    to: str,
    mail: DigestMail,
) -> SendResult:
    """Render and send the weekly "what's coming up" digest to one member."""
    context = {"display_name": mail.display_name or "", "events": mail.events, **mail.urls}
    html = render_to_string("emails/weekly_digest.html", context)
    text = render_to_string("emails/weekly_digest.txt", context)
    return sender.send(
        to=to,
        subject="what's coming up this week at pda",
        html=html,
        text=text,
    )


def send_monthly_digest_email(
    *,
    sender: EmailSender,
    to: str,
    mail: MonthlyDigestMail,
) -> SendResult:
    """Render and send the monthly "what's coming up" digest to one member."""
    month = mail.month.lower()
    context = {
        "display_name": mail.display_name or "",
        "month": month,
        "events": mail.events,
        "veganniversaries": mail.veganniversaries or [],
        **mail.urls,
    }
    html = render_to_string("emails/monthly_digest.html", context)
    text = render_to_string("emails/monthly_digest.txt", context)
    return sender.send(
        to=to,
        subject=f"what's coming up in {month} at pda",
        html=html,
        text=text,
    )
