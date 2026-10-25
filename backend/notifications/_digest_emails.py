from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


def send_weekly_digest_email(  # noqa: PLR0913
    *,
    sender: EmailSender,
    to: str,
    display_name: str,
    events: list[dict],
    urls: dict[str, str],
    veganniversaries: list[dict] | None = None,
) -> SendResult:
    """Render and send the weekly "what's coming up" digest to one member.

    param events(list[dict]): upcoming events, each with title/when/url keys
    param urls: calendar_url and settings_url
    param veganniversaries: year-grouped shout-out people, or empty
    """
    context = {
        "display_name": display_name or "",
        "events": events,
        "veganniversaries": veganniversaries or [],
        **urls,
    }
    html = render_to_string("emails/weekly_digest.html", context)
    text = render_to_string("emails/weekly_digest.txt", context)
    return sender.send(
        to=to,
        subject="what's coming up this week at pda",
        html=html,
        text=text,
    )
