from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.utils import timezone

from community.models import Event, EventStatus, Survey
from community.models.event import _is_past_q

if TYPE_CHECKING:
    from django.db.models import QuerySet

FEEDBACK_LOOKBACK = timedelta(days=7)


def _local_midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=settings.COMMUNITY_TZ)


def feedback_cutoff(now: datetime) -> datetime:
    return _local_midnight(timezone.localtime(now, settings.COMMUNITY_TZ).date())


def feedback_url(token: str) -> str:
    return f"{settings.FRONTEND_BASE_URL}/feedback/{token}"


def _active_feedback_event_types() -> list[str]:
    return list(
        Survey.objects.filter(is_active=True)
        .exclude(feedback_event_type="")
        .values_list("feedback_event_type", flat=True)
    )


def due_feedback_events(now: datetime) -> QuerySet[Event]:
    cutoff = feedback_cutoff(now)
    return Event.objects.filter(
        _is_past_q(cutoff),
        ~_is_past_q(cutoff - FEEDBACK_LOOKBACK),
        status=EventStatus.ACTIVE,
        event_type__in=_active_feedback_event_types(),
    )
