"""Helpers for sending specific transactional emails."""

from dataclasses import dataclass

from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult


@dataclass(frozen=True)
class RsvpEmailDetails:
    """Event + recipient details shared by the non-member RSVP emails."""

    to: str
    display_name: str
    event_title: str
    event_when: str
    event_location: str
    event_links: list[str]
    manage_url: str
    join_url: str

    def template_context(self) -> dict:
        return {
            "display_name": self.display_name or "",
            "event_title": self.event_title,
            "event_when": self.event_when,
            "event_location": self.event_location,
            "event_links": self.event_links,
            "manage_url": self.manage_url,
            "join_url": self.join_url,
        }


def send_rsvp_confirmation_email(
    *,
    sender: EmailSender,
    details: RsvpEmailDetails,
    waitlisted: bool,
) -> SendResult:
    """Render and send the non-member RSVP confirmation email."""
    context = {**details.template_context(), "waitlisted": waitlisted}
    html = render_to_string("emails/rsvp_confirmation.html", context)
    text = render_to_string("emails/rsvp_confirmation.txt", context)
    title = details.event_title.lower()
    subject = f"you're on the waitlist for {title}" if waitlisted else f"you're in for {title}"
    return sender.send(to=details.to, subject=subject, html=html, text=text)


def send_rsvp_waitlist_promoted_email(
    *,
    sender: EmailSender,
    details: RsvpEmailDetails,
) -> SendResult:
    """Render and send the non-member "you're off the waitlist" email."""
    context = details.template_context()
    html = render_to_string("emails/rsvp_waitlist_promoted.html", context)
    text = render_to_string("emails/rsvp_waitlist_promoted.txt", context)
    return sender.send(
        to=details.to,
        subject=f"you're off the waitlist for {details.event_title.lower()}",
        html=html,
        text=text,
    )


def send_magic_login_email(
    *,
    sender: EmailSender,
    to: str,
    display_name: str,
    magic_link_url: str,
) -> SendResult:
    """Render and send the magic-login email.

    Recipient validation (RFC-validity + header-injection guard) happens at the
    `EmailSender.send()` boundary, so every email type is protected uniformly.
    """
    context = {
        "display_name": display_name or "",
        "magic_link_url": magic_link_url,
    }
    html = render_to_string("emails/magic_login.html", context)
    text = render_to_string("emails/magic_login.txt", context)
    return sender.send(
        to=to,
        subject="your pda login link",
        html=html,
        text=text,
    )
