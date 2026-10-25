import importlib

import pytest
from community.models import (
    Event,
    EventRSVP,
    EventRsvpQuestion,
    RsvpQuestionType,
    RSVPStatus,
    Survey,
    SurveyQuestionType,
    SurveyResponse,
)
from django.apps import apps

from tests._survey_condition_helpers import make_question
from tests.conftest import future_iso

migration = importlib.import_module("community.migrations.0117_checkbox_answers_to_lists")


@pytest.mark.django_db
def test_checkbox_strings_become_lists_and_back(test_user):
    survey = Survey.objects.create(title="Interests", slug="interests")
    tags = make_question(survey, "Tags", SurveyQuestionType.CHECKBOX, options=["a", "b"])
    notes = make_question(survey, "Notes", SurveyQuestionType.TEXT, order=1)
    response = SurveyResponse.objects.create(
        survey=survey,
        answers={
            str(tags.id): {"label": "Tags", "answer": "a, b"},
            str(notes.id): {"label": "Notes", "answer": "x, y"},
        },
    )
    event = Event.objects.create(
        title="Potluck",
        start_datetime=future_iso(days=3),
        end_datetime=future_iso(days=3, hours=2),
        created_by=test_user,
    )
    bringing = EventRsvpQuestion.objects.create(
        event=event, label="bringing", field_type=RsvpQuestionType.CHECKBOX, options=["a", "b"]
    )
    rsvp = EventRSVP.objects.create(
        event=event,
        user=test_user,
        status=RSVPStatus.ATTENDING,
        questionnaire_responses={str(bringing.id): {"label": "bringing", "answer": "b"}},
    )

    migration.forwards(apps, None)
    response.refresh_from_db()
    rsvp.refresh_from_db()
    assert response.answers[str(tags.id)]["answer"] == ["a", "b"]
    assert response.answers[str(notes.id)]["answer"] == "x, y"
    assert rsvp.questionnaire_responses[str(bringing.id)]["answer"] == ["b"]

    migration.backwards(apps, None)
    response.refresh_from_db()
    assert response.answers[str(tags.id)]["answer"] == "a,b"
