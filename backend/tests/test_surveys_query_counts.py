import pytest
from community.models import Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests.test_surveys_admin import _put, admin_headers, surveys_admin  # noqa: F401

_seq = {"n": 0}


def _make_surveys(count: int, creator) -> None:
    for _ in range(count):
        _seq["n"] += 1
        survey = Survey.objects.create(title="s", slug=f"s-{_seq['n']}", created_by=creator)
        for _ in range(_seq["n"] % 3 + 1):
            SurveyResponse.objects.create(survey=survey, answers={})


def _count(call) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = call()
    assert response.status_code == 200
    return len(ctx.captured_queries)


@pytest.mark.django_db
class TestSurveysQueryCounts:
    def test_admin_list_is_constant(self, api_client, admin_headers, surveys_admin):  # noqa: F811
        def list_surveys():
            return api_client.get("/api/community/surveys/admin/", **admin_headers)

        _make_surveys(2, surveys_admin)
        small = _count(list_surveys)
        _make_surveys(6, surveys_admin)
        large = _count(list_surveys)
        assert large == small
        counts = {row["slug"]: row["response_count"] for row in list_surveys().json()}
        assert counts == {s.slug: s.responses.count() for s in Survey.objects.all()}

    def test_question_reorder_is_constant(self, api_client, admin_headers, surveys_admin):  # noqa: F811
        survey = Survey.objects.create(title="q", slug="q", created_by=surveys_admin)

        def reorder():
            ids = list(survey.questions.values_list("id", flat=True))
            payload = {"question_ids": [str(q) for q in reversed(ids)]}
            url = f"/api/community/surveys/{survey.id}/questions/order/"
            return _put(api_client, url, payload, admin_headers)

        def add_questions(n: int) -> None:
            start = survey.questions.count()
            for i in range(start, start + n):
                SurveyQuestion.objects.create(
                    survey=survey,
                    label=f"q{i}",
                    field_type=SurveyQuestionType.TEXT,
                    display_order=i,
                )

        add_questions(2)
        small = _count(reorder)
        add_questions(6)
        before = [q.label for q in survey.questions.order_by("display_order")]
        large = _count(reorder)
        assert large == small
        assert [q.label for q in survey.questions.order_by("display_order")] == before[::-1]
