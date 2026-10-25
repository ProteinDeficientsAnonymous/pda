import csv
import io
from uuid import uuid4

import pytest
from community._survey_validators import _build_survey_answers, _validate_survey_answers
from community.models import Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._survey_condition_helpers import make_question


def _question(field_type, **fields):
    return SurveyQuestion(id=uuid4(), label="q", field_type=field_type, **fields)


class TestSectionAnswers:
    def test_required_section_is_not_enforced(self):
        section = _question(SurveyQuestionType.SECTION, required=True)
        _validate_survey_answers({}, {str(section.id): section})

    def test_answers_to_sections_are_dropped(self):
        section = _question(SurveyQuestionType.SECTION)
        text = _question(SurveyQuestionType.TEXT)
        questions = {str(section.id): section, str(text.id): text}
        answers: dict[str, str | dict[str, str]] = {str(section.id): "sneaky", str(text.id): "hi"}
        _validate_survey_answers(answers, questions)
        assert _build_survey_answers(answers, questions) == {
            str(text.id): {"label": "q", "answer": "hi"}
        }


@pytest.mark.django_db
def test_csv_leaves_out_sections(api_client):
    admin = User.objects.create_user(phone_number="+12025557302", password="x")
    admin.roles.add(Role.objects.create(name="csv_mgr", permissions=[PermissionKey.MANAGE_SURVEYS]))
    token = RefreshToken.for_user(admin).access_token  # type: ignore
    survey = Survey.objects.create(title="Sections", slug="sections")
    make_question(survey, "about you", SurveyQuestionType.SECTION, order=0)
    text = make_question(survey, "name", SurveyQuestionType.TEXT, order=1)
    SurveyResponse.objects.create(
        survey=survey, answers={str(text.id): {"label": "name", "answer": "ada"}}
    )
    response = api_client.get(
        f"/api/community/surveys/{survey.id}/responses.csv",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 200
    header, row = list(csv.reader(io.StringIO(response.content.decode())))
    assert "about you" not in header
    assert row[-1] == "ada"
