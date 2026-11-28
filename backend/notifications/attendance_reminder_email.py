from datetime import date

from community.models import AttendanceMilestone
from django.conf import settings
from django.template.loader import render_to_string

from notifications.email_sender import EmailSender, SendResult

_TEMPLATE_NAMES: dict[str, str] = {
    AttendanceMilestone.M10: "attendance_reminder_10mo",
    AttendanceMilestone.M11: "attendance_reminder_11mo",
    AttendanceMilestone.M11_5: "attendance_reminder_11_5mo",
    AttendanceMilestone.M12: "attendance_reminder_12mo",
}

_SUBJECTS: dict[str, str] = {
    AttendanceMilestone.M10: "a heads up about pda events",
    AttendanceMilestone.M11: "a friendly nudge from pda",
    AttendanceMilestone.M11_5: "two weeks left to make it to a pda event",
    AttendanceMilestone.M12: "your pda membership is up for review",
}


def send_attendance_reminder_email(
    *,
    sender: EmailSender,
    to: str,
    display_name: str,
    milestone: str,
    deadline: date,
) -> SendResult:
    """Render and send the milestone attendance-reminder email."""
    template_name = _TEMPLATE_NAMES[milestone]
    context = {
        "display_name": display_name or "",
        "calendar_url": f"{settings.FRONTEND_BASE_URL}/calendar",
        "deadline": f"{deadline:%B} {deadline.day}, {deadline.year}".lower(),
    }
    html = render_to_string(f"emails/{template_name}.html", context)
    text = render_to_string(f"emails/{template_name}.txt", context)
    return sender.send(to=to, subject=_SUBJECTS[milestone], html=html, text=text)
