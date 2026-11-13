import pytest
from community.models import Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests._query_counts import assert_constant_queries


@pytest.mark.django_db
def test_admin_list_is_constant(api_client, surveys_admin_headers, surveys_admin):
    def add_surveys(n: int) -> None:
        start = Survey.objects.count()
        for i in range(start, start + n):
            survey = Survey.objects.create(title="s", slug=f"s-{i}", created_by=surveys_admin)
            for _ in range(i % 3):
                SurveyResponse.objects.create(survey=survey, answers={})

    url = "/api/community/surveys/admin/"
    assert_constant_queries(api_client, url, add_surveys, surveys_admin_headers)
    counts = {
        row["slug"]: row["response_count"]
        for row in api_client.get(url, **surveys_admin_headers).json()
    }
    assert counts == {f"s-{i}": i % 3 for i in range(8)}


@pytest.mark.django_db
def test_question_reorder_is_constant(api_client, surveys_admin_headers, surveys_admin):
    survey = Survey.objects.create(title="q", slug="q", created_by=surveys_admin)

    def add_questions(n: int) -> None:
        start = survey.questions.count()
        for i in range(start, start + n):
            SurveyQuestion.objects.create(
                survey=survey, label=f"q{i}", field_type=SurveyQuestionType.TEXT, display_order=i
            )

    def reorder() -> int:
        ids = [str(q) for q in survey.questions.values_list("id", flat=True)]
        url = f"/api/community/surveys/{survey.id}/questions/order/"
        with CaptureQueriesContext(connection) as ctx:
            response = api_client.put(
                url,
                {"question_ids": ids[::-1]},
                content_type="application/json",
                **surveys_admin_headers,
            )
        assert response.status_code == 200
        return len(ctx.captured_queries)

    add_questions(2)
    small = reorder()
    add_questions(6)
    before = [q.label for q in survey.questions.order_by("display_order")]
    assert reorder() == small
    assert [q.label for q in survey.questions.order_by("display_order")] == before[::-1]
