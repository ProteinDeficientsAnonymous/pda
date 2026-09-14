import threading

import pytest
from community.models import Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from django import db
from django.test import Client
from ninja_jwt.tokens import RefreshToken
from users.models import User


def _make_user(i):
    return User.objects.create_user(
        phone_number=f"+1415556{9200 + i}",
        password="Testpass123!",
        first_name=f"Racer{i}",
        last_name="",
    )


def _jwt_headers(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db(transaction=True)
class TestSurveyCapacityRace:
    def test_concurrent_submits_never_exceed_max_responses(self):
        """N threads submit to a 1-response survey at once; select_for_update() on the
        Survey row must serialize them so exactly 1 response is ever created (issue #1465)."""
        survey = Survey.objects.create(title="Race Survey", slug="race-survey", max_responses=1)
        question = SurveyQuestion.objects.create(
            survey=survey,
            label="Thoughts?",
            field_type=SurveyQuestionType.TEXT,
        )
        thread_count = 8
        users = [_make_user(i) for i in range(thread_count)]
        results = [None] * thread_count

        def submit(i):
            try:
                client = Client()
                resp = client.post(
                    f"/api/community/surveys/view/{survey.slug}/respond/",
                    {"answers": {str(question.id): f"answer {i}"}},
                    content_type="application/json",
                    **_jwt_headers(users[i]),
                )
                results[i] = resp.status_code
            finally:
                db.connections.close_all()

        threads = [threading.Thread(target=submit, args=(i,)) for i in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results.count(201) == 1, results
        assert results.count(404) == thread_count - 1, results
        assert SurveyResponse.objects.filter(survey=survey).count() == 1
