import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from asgiref.sync import async_to_sync
from community.models import EventType, Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.server import BASE_URL, pda_mcp
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests.test_mcp_server import _signed_in

pytestmark = pytest.mark.django_db


@pytest.fixture
def surveys_admin(db):
    user = User.objects.create_user(
        phone_number="+12025557100", password="x", first_name="Surveys", last_name="Admin"
    )
    user.roles.add(Role.objects.create(name="surveys", permissions=[PermissionKey.MANAGE_SURVEYS]))
    return user


def _survey(slug, days_ago=0, **fields):
    survey = Survey.objects.create(title=slug, slug=slug, **fields)
    created = datetime(2026, 10, 1, tzinfo=UTC) - timedelta(days=days_ago)
    Survey.objects.filter(pk=survey.pk).update(created_at=created)
    return survey


def _call(user, name, **arguments):
    token = _signed_in(user)
    try:
        return async_to_sync(pda_mcp.call_tool)(name, arguments).structured_content  # type: ignore[union-attr]
    finally:
        auth_context_var.reset(token)


def _tool_names(user) -> set[str]:
    token = _signed_in(user)
    try:
        return {tool.name for tool in async_to_sync(pda_mcp.list_tools)()}
    finally:
        auth_context_var.reset(token)


def test_survey_tools_need_manage_surveys(test_user, surveys_admin):
    survey = _survey("feedback")
    assert {"list_surveys", "get_survey"} & _tool_names(test_user) == set()
    assert {"list_surveys", "get_survey"} <= _tool_names(surveys_admin)
    for name, arguments in (("list_surveys", {}), ("get_survey", {"survey": survey.slug})):
        with pytest.raises(ToolError, match="permission"):
            _call(test_user, name, **arguments)


def test_list_surveys_newest_first_in_new_york_time(surveys_admin):
    old = _survey("old", days_ago=5, is_active=False, max_responses=10)
    _survey("new", opens_at=datetime(2026, 11, 7, 16, tzinfo=UTC))
    SurveyResponse.objects.create(survey=old)
    body = _call(surveys_admin, "list_surveys")
    assert [r["slug"] for r in body["surveys"]] == ["new", "old"]
    assert body["next_offset"] is None
    new_row, old_row = body["surveys"]
    assert new_row["opens_at"] == "2026-11-07T11:00:00-05:00"
    assert new_row["closes_at"] is None
    assert old_row == {
        "id": str(old.id),
        "slug": "old",
        "title": "old",
        "is_active": False,
        "status": "closed",
        "visibility": "public",
        "max_responses": 10,
        "response_count": 1,
        "linked_event_id": None,
        "opens_at": None,
        "closes_at": None,
        "edit_url": f"{BASE_URL}/admin/surveys/{old.id}",
    }


def test_list_surveys_pages(surveys_admin):
    for day in range(5):
        _survey(f"s{day}", days_ago=day)
    first = _call(surveys_admin, "list_surveys", limit=2)
    assert ([r["slug"] for r in first["surveys"]], first["next_offset"]) == (["s0", "s1"], 2)
    last = _call(surveys_admin, "list_surveys", limit=2, offset=4)
    assert ([r["slug"] for r in last["surveys"]], last["next_offset"]) == (["s4"], None)


def test_get_survey_by_id_or_slug(surveys_admin):
    survey = _survey(
        "feedback",
        description="tell us",
        anonymous=True,
        confirmation_message="thanks",
        closes_at=datetime(2026, 7, 4, 4, tzinfo=UTC),
    )
    by_slug = _call(surveys_admin, "get_survey", survey="feedback")
    assert _call(surveys_admin, "get_survey", survey=str(survey.id)) == by_slug
    assert by_slug["id"] == str(survey.id)
    assert (by_slug["description"], by_slug["anonymous"]) == ("tell us", True)
    assert by_slug["confirmation_message"] == "thanks"
    assert by_slug["closes_at"] == "2026-07-04T00:00:00-04:00"
    assert by_slug["url"] == f"{BASE_URL}/surveys/feedback"
    assert by_slug["questions"] == []


def _error(user, **arguments) -> dict:
    with pytest.raises(ToolError) as exc_info:
        _call(user, "get_survey", **arguments)
    return json.loads(str(exc_info.value).split(": ", 1)[1])


def test_get_survey_unknown_ref(surveys_admin):
    _survey("feedback")
    assert _error(surveys_admin, survey="nope") == {
        "status": 404,
        "detail": "no survey with id or slug nope",
    }
    assert _error(surveys_admin, survey=str(uuid.uuid4()))["status"] == 404


def test_get_survey_by_uppercase_uuid(surveys_admin):
    survey = _survey("feedback")
    assert _call(surveys_admin, "get_survey", survey=str(survey.id).upper())["id"] == str(survey.id)


def test_get_survey_hex_slug_is_not_a_uuid(surveys_admin):
    hex_slug = uuid.uuid4().hex
    survey = _survey(hex_slug)
    assert _call(surveys_admin, "get_survey", survey=hex_slug)["id"] == str(survey.id)


def test_feedback_survey_has_no_public_url(surveys_admin):
    _survey("feedback", feedback_event_type=EventType.OFFICIAL)
    body = _call(surveys_admin, "get_survey", survey="feedback")
    assert body["url"] is None
    assert body["edit_url"] == f"{BASE_URL}/admin/surveys/{body['id']}"


def test_survey_status_precedence(surveys_admin):
    now = datetime.now(UTC)
    _survey("off", is_active=False, opens_at=now + timedelta(days=1))
    _survey("ended", closes_at=now - timedelta(hours=1), max_responses=1)
    _survey("later", opens_at=now + timedelta(days=1), max_responses=1)
    SurveyResponse.objects.create(survey=_survey("full", max_responses=1))
    _survey("open", opens_at=now - timedelta(days=1), max_responses=2)
    rows = _call(surveys_admin, "list_surveys")["surveys"]
    assert {r["slug"]: r["status"] for r in rows} == {
        "off": "closed",
        "ended": "closed",
        "later": "scheduled",
        "full": "capped",
        "open": "active",
    }
    assert _call(surveys_admin, "get_survey", survey="full")["status"] == "capped"


def test_datetime_poll_options_stay_raw_with_new_york_times(surveys_admin):
    survey = _survey("when")
    options = ["2026-11-07T16:00:00.000Z", "2026-07-04T22:30:00.000Z"]
    SurveyQuestion.objects.create(
        survey=survey, label="when?", field_type=SurveyQuestionType.DATETIME_POLL, options=options
    )
    [question] = _call(surveys_admin, "get_survey", survey="when")["questions"]
    assert question["options"] == options
    assert question["option_times"] == ["2026-11-07T11:00:00-05:00", "2026-07-04T18:30:00-04:00"]


def test_datetime_poll_options_without_an_offset_have_no_time(surveys_admin):
    survey = _survey("when")
    options = ["saturday brunch", "2026-11-07T11:00", "2026-11-07T16:00:00Z"]
    SurveyQuestion.objects.create(
        survey=survey, label="when?", field_type=SurveyQuestionType.DATETIME_POLL, options=options
    )
    [question] = _call(surveys_admin, "get_survey", survey="when")["questions"]
    assert question["option_times"] == [None, None, "2026-11-07T11:00:00-05:00"]


def test_get_survey_questions_in_order_with_show_if_source(surveys_admin):
    survey = _survey("feedback")
    radio = SurveyQuestionType.RADIO
    later = SurveyQuestion.objects.create(survey=survey, label="why?", display_order=5)
    first = SurveyQuestion.objects.create(
        survey=survey, label="came?", field_type=radio, options=["yes", "no"], display_order=2
    )
    later.show_if = {"question_id": str(first.id), "operator": "equals", "value": "no"}
    later.save()
    questions = _call(surveys_admin, "get_survey", survey="feedback")["questions"]
    assert questions == [
        {
            "id": str(first.id),
            "label": "came?",
            "field_type": "radio",
            "options": ["yes", "no"],
            "description": "",
            "required": False,
            "position": 1,
            "show_if": None,
        },
        {
            "id": str(later.id),
            "label": "why?",
            "field_type": "text",
            "options": [],
            "description": "",
            "required": False,
            "position": 2,
            "show_if": {
                "question_id": str(first.id),
                "operator": "equals",
                "value": "no",
                "question_position": 1,
                "question": "came?",
            },
        },
    ]
