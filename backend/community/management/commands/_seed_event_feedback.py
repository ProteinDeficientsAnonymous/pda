from datetime import datetime, time, timedelta

from django.conf import settings
from django.utils import timezone
from users.models import User

from community.models import (
    Event,
    EventRSVP,
    EventType,
    PageVisibility,
    RSVPStatus,
    Survey,
    SurveyQuestion,
)
from community.models.choices import AttendanceStatus, SurveyQuestionType

from ._seed_shared import apply_rsvp

FEEDBACK_SURVEY_SLUG = "event-feedback"
FEEDBACK_EVENT_TITLE = "Past Official Gathering (seed · feedback)"
FEEDBACK_ATTENDEE_PHONES = ("+17025550001", "+17025550002", "+17025550003")

FEEDBACK_QUESTIONS = [
    (
        "how was the event?",
        SurveyQuestionType.RADIO,
        ["loved it", "it was good", "it was okay", "not for me"],
        True,
    ),
    ("what did you love?", SurveyQuestionType.TEXT, [], False),
    ("what's your constructive feedback?", SurveyQuestionType.TEXT, [], False),
]


def seed_feedback_survey(stdout, created_by: User | None) -> Survey:
    survey, created = Survey.objects.get_or_create(
        feedback_event_type=EventType.OFFICIAL,
        defaults={
            "title": "event feedback",
            "slug": FEEDBACK_SURVEY_SLUG,
            "anonymous": True,
            "created_by": created_by,
        },
    )
    for order, (label, field_type, options, required) in enumerate(FEEDBACK_QUESTIONS):
        SurveyQuestion.objects.get_or_create(
            survey=survey,
            label=label,
            defaults={
                "field_type": field_type,
                "options": options,
                "required": required,
                "display_order": order,
            },
        )
    stdout.write(f"  {'created' if created else 'exists'} feedback survey: {survey.title}")
    return survey


def _yesterday_evening() -> tuple[datetime, datetime]:
    """Yesterday 17:00-19:00 local, so the day-after cron always picks the event up."""
    yesterday = timezone.localtime(timezone.now(), settings.COMMUNITY_TZ).date() - timedelta(days=1)
    start = datetime.combine(yesterday, time(17), tzinfo=settings.COMMUNITY_TZ)
    return start, start + timedelta(hours=2)


def seed_feedback_event(stdout, created_by: User | None) -> Event:
    start, end = _yesterday_evening()
    event, created = Event.objects.get_or_create(
        title=FEEDBACK_EVENT_TITLE,
        defaults={
            "description": "past official event with checked-in attendees for feedback emails.",
            "start_datetime": start,
            "end_datetime": end,
            "location": "Community Garden",
            "event_type": EventType.OFFICIAL,
            "visibility": PageVisibility.PUBLIC,
            "rsvp_enabled": True,
            "created_by": created_by,
        },
    )
    stdout.write(f"  {'created' if created else 'exists'} event: {event.title}")
    for user in User.objects.filter(phone_number__in=FEEDBACK_ATTENDEE_PHONES):
        apply_rsvp(
            event,
            user,
            {
                "status": RSVPStatus.ATTENDING,
                "attendance": AttendanceStatus.ATTENDED,
                "checked_in_at": end,
            },
        )
    stdout.write(f"  checked-in attendees: {EventRSVP.objects.filter(event=event).count()}")
    return event


def seed_event_feedback(stdout, created_by: User | None) -> None:
    seed_feedback_survey(stdout, created_by)
    seed_feedback_event(stdout, created_by)
