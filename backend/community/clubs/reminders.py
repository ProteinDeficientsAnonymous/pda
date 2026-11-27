import calendar
from datetime import date, datetime

from django.conf import settings
from django.db.models import Exists, OuterRef, QuerySet

from community.models import Club, ClubReminderStage, Event, EventStatus, EventType

_EARLY_DAY = 10
_WEEK_OFFSET = 7


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
