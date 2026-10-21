"""Tests for conditional survey questions (`show_if`)."""

import json

import pytest
from community._validation import Code
from community.models import (
    ShowIfOperator,
    Survey,
    SurveyQuestionType,
)
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code
from tests._survey_condition_helpers import equals, make_question


@pytest.fixture
def surveys_admin(db):
    admin = User.objects.create_user(
        phone_number="+12025557101", password="x", first_name="Cond", last_name="Admin"
    )
    role = Role.objects.create(name="cond_mgr", permissions=[PermissionKey.MANAGE_SURVEYS])
    admin.roles.add(role)
    return admin


@pytest.fixture
def admin_headers(surveys_admin):
    return {
        "HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(surveys_admin).access_token}"  # type: ignore
    }


@pytest.fixture
def survey(db):
    return Survey.objects.create(title="Conditions", slug="conditions")


# ---------------------------------------------------------------------------
# Save-time validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestShowIfSaveValidation:
    def _create(self, api_client, admin_headers, survey, payload):
        return api_client.post(
            f"/api/community/surveys/{survey.id}/questions/",
            data=json.dumps(payload),
            content_type="application/json",
            **admin_headers,
        )

    def test_accepts_condition_on_earlier_choice_question(self, api_client, admin_headers, survey):
        source = make_question(
            survey, "Diet", SurveyQuestionType.RADIO, options=["vegan", "veg"], order=0
        )
        response = self._create(
            api_client,
            admin_headers,
            survey,
            {
                "label": "How long?",
                "field_type": SurveyQuestionType.TEXT,
                "options": [],
                "required": False,
                "show_if": equals(source, "vegan"),
            },
        )
        assert response.status_code == 201
        assert response.json()["show_if"] == {
            "question_id": str(source.id),
            "operator": ShowIfOperator.EQUALS.value,
            "value": "vegan",
        }

    def test_rejects_question_from_another_survey(self, api_client, admin_headers, survey, db):
        other = Survey.objects.create(title="Other", slug="other")
        foreign = make_question(other, "Diet", SurveyQuestionType.RADIO, options=["vegan"], order=0)
        response = self._create(
            api_client,
            admin_headers,
            survey,
            {
                "label": "Dependent",
                "field_type": SurveyQuestionType.TEXT,
                "options": [],
                "required": False,
                "show_if": equals(foreign, "vegan"),
            },
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.CONDITION_QUESTION_NOT_FOUND, "show_if")

    def test_rejects_later_question(self, api_client, admin_headers, survey):
        first = make_question(
            survey, "First", SurveyQuestionType.RADIO, options=["a", "b"], order=0
        )
        later = make_question(
            survey, "Later", SurveyQuestionType.RADIO, options=["a", "b"], order=5
        )
        response = api_client.patch(
            f"/api/community/surveys/{survey.id}/questions/{first.id}/",
            data=json.dumps(
                {
                    "label": "First",
                    "field_type": SurveyQuestionType.RADIO,
                    "options": ["a", "b"],
                    "required": False,
                    "show_if": equals(later, "a"),
                }
            ),
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.CONDITION_QUESTION_NOT_EARLIER, "show_if")

    def test_rejects_non_choice_source_type(self, api_client, admin_headers, survey):
        source = make_question(survey, "Name", SurveyQuestionType.TEXT, order=0)
        response = self._create(
            api_client,
            admin_headers,
            survey,
            {
                "label": "Dependent",
                "field_type": SurveyQuestionType.TEXT,
                "options": [],
                "required": False,
                "show_if": equals(source, "anything"),
            },
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.CONDITION_TYPE_NOT_SUPPORTED, "show_if")

    def test_rejects_value_outside_options(self, api_client, admin_headers, survey):
        source = make_question(
            survey, "Diet", SurveyQuestionType.SELECT, options=["vegan", "veg"], order=0
        )
        response = self._create(
            api_client,
            admin_headers,
            survey,
            {
                "label": "Dependent",
                "field_type": SurveyQuestionType.TEXT,
                "options": [],
                "required": False,
                "show_if": equals(source, "carnivore"),
            },
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.CONDITION_VALUE_INVALID, "show_if")

    def test_boolean_source_accepts_yes(self, api_client, admin_headers, survey):
        source = make_question(survey, "Member?", SurveyQuestionType.BOOLEAN, order=0)
        response = self._create(
            api_client,
            admin_headers,
            survey,
            {
                "label": "Dependent",
                "field_type": SurveyQuestionType.TEXT,
                "options": [],
                "required": False,
                "show_if": equals(source, "yes"),
            },
        )
        assert response.status_code == 201

    def test_contains_requires_checkbox_source(self, api_client, admin_headers, survey):
        source = make_question(survey, "Diet", SurveyQuestionType.RADIO, options=["vegan"], order=0)
        response = self._create(
            api_client,
            admin_headers,
            survey,
            {
                "label": "Dependent",
                "field_type": SurveyQuestionType.TEXT,
                "options": [],
                "required": False,
                "show_if": {
                    "question_id": str(source.id),
                    "operator": ShowIfOperator.CONTAINS.value,
                    "value": "vegan",
                },
            },
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.CONDITION_OPERATOR_NOT_SUPPORTED, "show_if")

    def test_clearing_condition_persists_null(self, api_client, admin_headers, survey):
        source = make_question(survey, "Diet", SurveyQuestionType.RADIO, options=["vegan"], order=0)
        dependent = make_question(
            survey, "Dependent", SurveyQuestionType.TEXT, order=1, show_if=equals(source, "vegan")
        )
        response = api_client.patch(
            f"/api/community/surveys/{survey.id}/questions/{dependent.id}/",
            data=json.dumps(
                {
                    "label": "Dependent",
                    "field_type": SurveyQuestionType.TEXT,
                    "options": [],
                    "required": False,
                    "show_if": None,
                }
            ),
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["show_if"] is None
        dependent.refresh_from_db()
        assert dependent.show_if is None


# ---------------------------------------------------------------------------
# Reorder + delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConditionOrdering:
    def test_reorder_rejects_moving_question_above_dependency(
        self, api_client, admin_headers, survey
    ):
        source = make_question(survey, "Diet", SurveyQuestionType.RADIO, options=["vegan"], order=0)
        dependent = make_question(
            survey, "Dependent", SurveyQuestionType.TEXT, order=1, show_if=equals(source, "vegan")
        )
        response = api_client.put(
            f"/api/community/surveys/{survey.id}/questions/order/",
            data=json.dumps({"question_ids": [str(dependent.id), str(source.id)]}),
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.CONDITION_ORDER_CONFLICT, "question_ids")
        source.refresh_from_db()
        assert source.display_order == 0

    def test_reorder_allows_order_that_keeps_dependency_first(
        self, api_client, admin_headers, survey
    ):
        source = make_question(survey, "Diet", SurveyQuestionType.RADIO, options=["vegan"], order=0)
        dependent = make_question(
            survey, "Dependent", SurveyQuestionType.TEXT, order=1, show_if=equals(source, "vegan")
        )
        spare = make_question(survey, "Spare", SurveyQuestionType.TEXT, order=2)
        response = api_client.put(
            f"/api/community/surveys/{survey.id}/questions/order/",
            data=json.dumps({"question_ids": [str(spare.id), str(source.id), str(dependent.id)]}),
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 200
        dependent.refresh_from_db()
        assert dependent.display_order == 2

    def test_partial_reorder_payload_cannot_bypass_the_dependency_check(
        self, api_client, admin_headers, survey
    ):
        source = make_question(survey, "Diet", SurveyQuestionType.RADIO, options=["vegan"], order=0)
        spare = make_question(survey, "Spare", SurveyQuestionType.TEXT, order=1)
        dependent = make_question(
            survey, "Dependent", SurveyQuestionType.TEXT, order=2, show_if=equals(source, "vegan")
        )
        response = api_client.put(
            f"/api/community/surveys/{survey.id}/questions/order/",
            data=json.dumps({"question_ids": [str(dependent.id), str(spare.id)]}),
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.CONDITION_ORDER_CONFLICT, "question_ids")
        source.refresh_from_db()
        dependent.refresh_from_db()
        assert source.display_order == 0
        assert dependent.display_order == 2

    def test_question_created_after_a_delete_gets_a_free_display_order(
        self, api_client, admin_headers, survey
    ):
        make_question(survey, "First", SurveyQuestionType.TEXT, order=0)
        middle = make_question(survey, "Middle", SurveyQuestionType.TEXT, order=1)
        last = make_question(survey, "Diet", SurveyQuestionType.RADIO, options=["vegan"], order=2)
        api_client.delete(
            f"/api/community/surveys/{survey.id}/questions/{middle.id}/", **admin_headers
        )
        response = api_client.post(
            f"/api/community/surveys/{survey.id}/questions/",
            data=json.dumps(
                {
                    "label": "How long?",
                    "field_type": SurveyQuestionType.TEXT,
                    "options": [],
                    "required": False,
                    "show_if": equals(last, "vegan"),
                }
            ),
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 201
        assert response.json()["display_order"] == 3

    def test_retyping_a_source_is_rejected_while_dependents_use_it(
        self, api_client, admin_headers, survey
    ):
        source = make_question(survey, "Diet", SurveyQuestionType.RADIO, options=["vegan"], order=0)
        dependent = make_question(
            survey, "Dependent", SurveyQuestionType.TEXT, order=1, show_if=equals(source, "vegan")
        )
        response = api_client.patch(
            f"/api/community/surveys/{survey.id}/questions/{source.id}/",
            data=json.dumps(
                {
                    "label": "Diet",
                    "field_type": SurveyQuestionType.TEXT,
                    "options": [],
                    "required": False,
                    "show_if": None,
                }
            ),
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.CONDITION_SOURCE_IN_USE, "show_if")
        source.refresh_from_db()
        dependent.refresh_from_db()
        assert source.field_type == SurveyQuestionType.RADIO
        assert dependent.show_if is not None

    def test_renaming_a_source_option_a_dependent_uses_is_rejected(
        self, api_client, admin_headers, survey
    ):
        source = make_question(
            survey, "Diet", SurveyQuestionType.RADIO, options=["vegan", "veg"], order=0
        )
        stale = make_question(
            survey, "Stale", SurveyQuestionType.TEXT, order=1, show_if=equals(source, "vegan")
        )
        kept = make_question(
            survey, "Kept", SurveyQuestionType.TEXT, order=2, show_if=equals(source, "veg")
        )
        response = api_client.patch(
            f"/api/community/surveys/{survey.id}/questions/{source.id}/",
            data=json.dumps(
                {
                    "label": "Diet",
                    "field_type": SurveyQuestionType.RADIO,
                    "options": ["plant-based", "veg"],
                    "required": False,
                    "show_if": None,
                }
            ),
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.CONDITION_SOURCE_IN_USE, "show_if")
        assert response.json()["detail"][0]["params"]["label"] == "Stale"
        stale.refresh_from_db()
        kept.refresh_from_db()
        assert stale.show_if is not None
        assert kept.show_if is not None

    def test_renaming_an_unused_source_option_is_allowed(self, api_client, admin_headers, survey):
        source = make_question(
            survey, "Diet", SurveyQuestionType.RADIO, options=["vegan", "veg"], order=0
        )
        dependent = make_question(
            survey, "Dependent", SurveyQuestionType.TEXT, order=1, show_if=equals(source, "veg")
        )
        response = api_client.patch(
            f"/api/community/surveys/{survey.id}/questions/{source.id}/",
            data=json.dumps(
                {
                    "label": "Diet",
                    "field_type": SurveyQuestionType.RADIO,
                    "options": ["plant-based", "veg"],
                    "required": False,
                    "show_if": None,
                }
            ),
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 200
        dependent.refresh_from_db()
        assert dependent.show_if == equals(source, "veg")

    def test_update_rejects_a_condition_on_itself(self, api_client, admin_headers, survey):
        question = make_question(
            survey, "Diet", SurveyQuestionType.RADIO, options=["vegan"], order=0
        )
        response = api_client.patch(
            f"/api/community/surveys/{survey.id}/questions/{question.id}/",
            data=json.dumps(
                {
                    "label": "Diet",
                    "field_type": SurveyQuestionType.RADIO,
                    "options": ["vegan"],
                    "required": False,
                    "show_if": equals(question, "vegan"),
                }
            ),
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.CONDITION_QUESTION_NOT_EARLIER, "show_if")

    def test_deleting_source_clears_dependent_condition(self, api_client, admin_headers, survey):
        source = make_question(survey, "Diet", SurveyQuestionType.RADIO, options=["vegan"], order=0)
        dependent = make_question(
            survey, "Dependent", SurveyQuestionType.TEXT, order=1, show_if=equals(source, "vegan")
        )
        response = api_client.delete(
            f"/api/community/surveys/{survey.id}/questions/{source.id}/", **admin_headers
        )
        assert response.status_code == 204
        dependent.refresh_from_db()
        assert dependent.show_if is None
