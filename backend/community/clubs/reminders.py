import calendar
import logging
from datetime import date, datetime

from django.conf import settings
from django.db.models import Exists, OuterRef, QuerySet
from notifications.club_reminder_email import ClubReminderEmailDetails, send_club_reminder_email
from notifications.email_sender import get_email_sender, send_best_effort
from users.models import HAS_EMAIL, User

from community.models import (
    Club,
    ClubEventReminder,
    ClubReminderStage,
    Event,
    EventStatus,
    EventType,
)

logger = logging.getLogger(__name__)

_EARLY_DAY = 10
_WEEK_OFFSET = 7
_SHARE_DAY = 15


def target_month(today: date) -> date:
    return date(today.year + (today.month == 12), today.month % 12 + 1, 1)


def due_stage(today: date) -> ClubReminderStage | None:
    last = calendar.monthrange(today.year, today.month)[1]
    stages = (
        (last, ClubReminderStage.FINAL),
        (last - _WEEK_OFFSET, ClubReminderStage.WEEK),
        (_EARLY_DAY, ClubReminderStage.EARLY),
    )
    return next((stage for day, stage in stages if day <= today.day), None)


def uncovered_clubs(month: date) -> QuerySet[Club]:
    start = datetime(month.year, month.month, 1, tzinfo=settings.COMMUNITY_TZ)
    end_month = target_month(month)
    end = datetime(end_month.year, end_month.month, 1, tzinfo=settings.COMMUNITY_TZ)
    covering = Event.objects.filter(
        club=OuterRef("pk"),
        event_type=EventType.CLUB,
        status=EventStatus.ACTIVE,
        start_datetime__gte=start,
        start_datetime__lt=end,
    )
    return Club.objects.filter(~Exists(covering))


def _deadline_label(today: date) -> str:
    last = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    return f"{last:%b} {last.day}".lower()


def send_club_event_reminders(now: datetime) -> int:
    """return(int): number of reminder emails sent"""
    today = now.astimezone(settings.COMMUNITY_TZ).date()
    stage = due_stage(today)
    if stage is None:
        return 0
    month = target_month(today)
    month_label = f"{month:%B}".lower()
    deadline_label = _deadline_label(today)
    create_url = f"{settings.FRONTEND_BASE_URL}/events/add"
    sent = 0
    for club in uncovered_clubs(month):
        _, created = ClubEventReminder.objects.get_or_create(club=club, month=month, stage=stage)
        if not created:
            continue
        reps = club.reps.filter(pk__in=User.objects.active_members().values("pk")).filter(HAS_EMAIL)
        if not reps:
            logger.info("club_event_reminder_no_recipients", extra={"club_id": str(club.pk)})
            continue
        for rep in reps:
            details = ClubReminderEmailDetails(
                to=rep.email,
                display_name=rep.full_name or "",
                club_name=club.name,
                month_label=month_label,
                deadline_label=deadline_label,
                stage=stage,
                create_url=create_url,
                share_passed=today.day > _SHARE_DAY,
            )
            sent += send_best_effort(
                lambda details=details: send_club_reminder_email(
                    sender=get_email_sender(), details=details
                ),
                f"club_event_reminder_{stage}_email",
            )
    return sent
