from datetime import datetime, timedelta

import pytest
from community._event_feedback_send import (
    due_feedback_events,
    feedback_cutoff,
    feedback_url,
)
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

    @pytest.mark.parametrize("status", [EventStatus.DRAFT, EventStatus.DELETED])
    def test_draft_and_deleted_events_excluded(self, feedback_survey, status):
        _event(status=status)
        assert not due_feedback_events(NOW).exists()

    def test_datetime_tbd_event_excluded(self, feedback_survey):
        _event(datetime_tbd=True)
        assert not due_feedback_events(NOW).exists()

    @pytest.mark.parametrize(("hours_before_cutoff", "included"), [(3, True), (1, False)])
    def test_event_without_end_uses_two_hour_default(
        self, feedback_survey, hours_before_cutoff, included
    ):
        cutoff = feedback_cutoff(NOW)
        Event.objects.create(
            title="No End",
            event_type=EventType.OFFICIAL,
            status=EventStatus.ACTIVE,
            start_datetime=cutoff - timedelta(hours=hours_before_cutoff),
        )
        assert due_feedback_events(NOW).exists() is included

    @pytest.mark.parametrize(
        ("now", "end", "included"),
        [
            (
                datetime(2026, 11, 1, 14, 0, tzinfo=TZ),
                datetime(2026, 10, 31, 23, 30, tzinfo=TZ),
                True,
            ),
            (
                datetime(2026, 11, 1, 14, 0, tzinfo=TZ),
                datetime(2026, 11, 1, 0, 30, tzinfo=TZ),
                False,
            ),
            (
                datetime(2026, 11, 2, 14, 0, tzinfo=TZ),
                datetime(2026, 11, 1, 23, 30, tzinfo=TZ),
                True,
            ),
            (
                datetime(2026, 11, 2, 14, 0, tzinfo=TZ),
                datetime(2026, 10, 26, 0, 30, tzinfo=TZ),
                True,
            ),
            (
                datetime(2026, 11, 2, 14, 0, tzinfo=TZ),
                datetime(2026, 10, 25, 23, 30, tzinfo=TZ),
                False,
            ),
        ],
    )
    def test_local_midnight_boundary_across_dst_fall_back(
        self, feedback_survey, now, end, included
    ):
        _event(end=end)
        assert due_feedback_events(now).exists() is included


def test_feedback_url_format():
    assert feedback_url("abc123") == f"{settings.FRONTEND_BASE_URL}/feedback/abc123"
