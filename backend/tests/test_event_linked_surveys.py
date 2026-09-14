from datetime import timedelta

import pytest
from community._event_helpers import _event_out
from community.models import Event, EventType, PageVisibility, Survey
from django.utils import timezone


@pytest.fixture
def event(db, test_user):
    return Event.objects.create(
        title="Potluck",
        start_datetime=timezone.now() + timedelta(days=10),
        event_type=EventType.OFFICIAL,
        visibility=PageVisibility.PUBLIC,
        created_by=test_user,
    )


@pytest.mark.django_db
class TestEventLinkedSurveys:
    def test_empty_when_no_linked_surveys(self, event):
        assert _event_out(event).linked_surveys == []

    def test_serializes_id_title_and_slug(self, event):
        survey = Survey.objects.create(
            title="Potluck Feedback", slug="potluck-feedback", linked_event=event
        )

        linked = _event_out(event).linked_surveys

        assert len(linked) == 1
        assert linked[0].id == str(survey.id)
        assert linked[0].title == "Potluck Feedback"
        assert linked[0].slug == "potluck-feedback"

    def test_excludes_inactive_surveys(self, event):
        Survey.objects.create(
            title="Closed", slug="closed-survey", linked_event=event, is_active=False
        )
        Survey.objects.create(title="Open", slug="open-survey", linked_event=event)

        assert [s.slug for s in _event_out(event).linked_surveys] == ["open-survey"]
