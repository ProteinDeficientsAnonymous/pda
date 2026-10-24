from datetime import datetime, timedelta

import pytest
from community._event_feedback_send import due_feedback_events, feedback_url
from community.models import Event, EventStatus, EventType, Survey
from django.conf import settings

TZ = settings.COMMUNITY_TZ
NOW = datetime(2026, 10, 15, 14, 0, tzinfo=TZ)
YESTERDAY_EVENING = datetime(2026, 10, 14, 20, 0, tzinfo=TZ)


@pytest.fixture
def feedback_survey(db):
    return Survey.objects.create(
        title="official feedback", slug="official-feedback", feedback_event_type=EventType.OFFICIAL
    )


def _event(*, end=YESTERDAY_EVENING, event_type=EventType.OFFICIAL, **extra) -> Event:
    return Event.objects.create(
        title="Vegan Potluck",
        event_type=event_type,
        status=extra.pop("status", EventStatus.ACTIVE),
        start_datetime=end - timedelta(hours=2),
        end_datetime=end,
        **extra,
    )


@pytest.mark.django_db
class TestDueFeedbackEvents:
    def test_event_ended_yesterday_included(self, feedback_survey):
        event = _event()
        assert list(due_feedback_events(NOW)) == [event]

    def test_event_ended_earlier_today_excluded(self, feedback_survey):
        _event(end=datetime(2026, 10, 15, 10, 0, tzinfo=TZ))
        assert not due_feedback_events(NOW).exists()

    def test_event_older_than_lookback_excluded(self, feedback_survey):
        _event(end=NOW - timedelta(days=8))
        assert not due_feedback_events(NOW).exists()

    def test_cancelled_event_excluded(self, feedback_survey):
        _event(status=EventStatus.CANCELLED)
        assert not due_feedback_events(NOW).exists()

    def test_type_without_feedback_survey_excluded(self, feedback_survey):
        _event(event_type=EventType.CLUB)
        assert not due_feedback_events(NOW).exists()

    def test_inactive_feedback_survey_excluded(self, feedback_survey):
        Survey.objects.filter(pk=feedback_survey.pk).update(is_active=False)
        _event()
        assert not due_feedback_events(NOW).exists()


def test_feedback_url_format():
    assert feedback_url("abc123") == f"{settings.FRONTEND_BASE_URL}/feedback/abc123"
