import re
from datetime import timedelta

import pytest
from community.models import Event, EventFeedbackRequest, EventType, Survey
from community.models.event_feedback import feedback_survey_for
from django.db import IntegrityError, transaction
from django.utils import timezone


@pytest.fixture
def event(db):
    start = timezone.now() - timedelta(days=1)
    return Event.objects.create(
        title="potluck", start_datetime=start, end_datetime=start + timedelta(hours=2)
    )


def test_second_feedback_survey_for_same_type_rejected(db):
    Survey.objects.create(title="a", slug="a", feedback_event_type=EventType.OFFICIAL)
    with pytest.raises(IntegrityError), transaction.atomic():
        Survey.objects.create(title="b", slug="b", feedback_event_type=EventType.OFFICIAL)


def test_many_surveys_with_blank_feedback_type_allowed(db):
    Survey.objects.create(title="a", slug="a")
    Survey.objects.create(title="b", slug="b")
    assert Survey.objects.filter(feedback_event_type="").count() == 2


def test_feedback_request_unique_per_event_user(event, test_user):
    EventFeedbackRequest.objects.create(
        event=event, user=test_user, token=EventFeedbackRequest.new_token()
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        EventFeedbackRequest.objects.create(
            event=event, user=test_user, token=EventFeedbackRequest.new_token()
        )


def test_new_token_is_unique_and_urlsafe():
    a, b = EventFeedbackRequest.new_token(), EventFeedbackRequest.new_token()
    assert a != b
    assert len(a) <= 64
    assert re.fullmatch(r"[A-Za-z0-9_-]+", a)


def test_feedback_survey_for_returns_marked_survey_or_none(db):
    assert feedback_survey_for(EventType.OFFICIAL) is None
    survey = Survey.objects.create(title="a", slug="a", feedback_event_type=EventType.OFFICIAL)
    assert feedback_survey_for(EventType.OFFICIAL) == survey
    assert feedback_survey_for(EventType.CLUB) is None
