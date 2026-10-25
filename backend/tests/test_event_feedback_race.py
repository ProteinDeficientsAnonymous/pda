import threading
from datetime import timedelta

import pytest
from community.models import (
    Event,
    EventFeedbackRequest,
    EventType,
    Survey,
    SurveyQuestion,
    SurveyQuestionType,
    SurveyResponse,
)
from django import db
from django.test import Client
from django.utils import timezone
from users.models import User

THREADS = 8


def _setup(max_responses: int | None = None):
    survey = Survey.objects.create(
        title="race feedback",
        slug="race-feedback",
        anonymous=True,
        feedback_event_type=EventType.OFFICIAL,
        max_responses=max_responses,
    )
    question = SurveyQuestion.objects.create(
        survey=survey, label="how was it?", field_type=SurveyQuestionType.TEXT
    )
    start = timezone.now() - timedelta(days=1)
    event = Event.objects.create(
        title="race potluck",
        event_type=EventType.OFFICIAL,
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
    )
    return survey, question, event


def _request(event, i: int) -> EventFeedbackRequest:
    user = User.objects.create_user(phone_number=f"+1415557{9300 + i}", first_name=f"Racer{i}")
    return EventFeedbackRequest.objects.create(
        event=event, user=user, token=EventFeedbackRequest.new_token()
    )


def _race(tokens: list[str], question) -> list[int | None]:
    results: list[int | None] = [None] * len(tokens)

    def submit(i):
        try:
            resp = Client().post(
                "/api/community/event-feedback/respond/",
                {"answers": {str(question.id): f"answer {i}"}},
                content_type="application/json",
                HTTP_X_FEEDBACK_TOKEN=tokens[i],
            )
            results[i] = resp.status_code
        finally:
            db.connections.close_all()

    threads = [threading.Thread(target=submit, args=(i,)) for i in range(len(tokens))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
class TestEventFeedbackRace:
    def test_concurrent_submits_with_one_token_create_one_response(self):
        survey, question, event = _setup()
        token = _request(event, 0).token
        results = _race([token] * THREADS, question)
        assert results.count(201) == 1, results
        assert results.count(400) == THREADS - 1, results
        assert SurveyResponse.objects.filter(survey=survey).count() == 1

    def test_concurrent_submits_never_exceed_max_responses(self):
        survey, question, event = _setup(max_responses=1)
        tokens = [_request(event, i).token for i in range(THREADS)]
        results = _race(tokens, question)
        assert results.count(201) == 1, results
        assert SurveyResponse.objects.filter(survey=survey).count() == 1
