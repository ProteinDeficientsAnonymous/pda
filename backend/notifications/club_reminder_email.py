from dataclasses import asdict, dataclass

from community.models import ClubReminderStage
from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult

_SUBJECTS = {
    ClubReminderStage.EARLY: "{month} {club} events get shared on the 15th",
    ClubReminderStage.WEEK: "{club}: {month} events due by {deadline}",
    ClubReminderStage.FINAL: "{club}: {month} events due today",
}


@dataclass(frozen=True)
class ClubReminderEmailDetails:
    to: str
    display_name: str
    club_name: str
    month_label: str
    deadline_label: str
    stage: ClubReminderStage
    create_url: str
    share_passed: bool = False


def _early_after_share(details: ClubReminderEmailDetails) -> bool:
    return details.stage == ClubReminderStage.EARLY and details.share_passed


def send_club_reminder_email(
    *, sender: EmailSender, details: ClubReminderEmailDetails
) -> SendResult:
    context = {
        **asdict(details),
        "week_style": details.stage == ClubReminderStage.WEEK or _early_after_share(details),
    }
    stage = ClubReminderStage.WEEK if _early_after_share(details) else details.stage
    subject = _SUBJECTS[stage].format(
        month=details.month_label, club=details.club_name.lower(), deadline=details.deadline_label
    )
    return sender.send(
        to=details.to,
        subject=subject,
        html=render_to_string("emails/club_event_reminder.html", context),
        text=render_to_string("emails/club_event_reminder.txt", context),
    )
