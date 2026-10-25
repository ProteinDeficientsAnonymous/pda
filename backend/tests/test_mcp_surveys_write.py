import json
import time
from datetime import timedelta
from unittest.mock import patch

import anyio
import pytest
from audit.models import AuditLogEntry
from community._surveys import create_survey_question as create_question_view
from community._validation import Code
from community.models import Event, Survey, SurveyQuestion
from django.utils import timezone
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from mcp_gateway.server import BASE_URL, pda_mcp
from mcp_gateway.tools import surveys_write
from users.permissions import PermissionKey
from users.roles import Role

from tests.test_mcp_events_write import _error, _run
from tests.test_mcp_server import _signed_in

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)
SETTINGS = {"title": "Retreat Planning!"}
NAME = {"label": "name", "required": True}
NOTES = {"label": "notes", "field_type": "textarea"}
FOOD = {"label": "food?", "field_type": "radio", "options": ["vegan", "very vegan"]}


@pytest.fixture
def surveys_admin(test_user):
    role = Role.objects.create(name="surveys", permissions=[PermissionKey.MANAGE_SURVEYS])
    test_user.roles.add(role)
    return test_user


def _create(user, questions=(NAME, NOTES), **settings) -> dict:
    return _run(user, "create_survey", settings={**SETTINGS, **settings}, questions=list(questions))


def _create_refused(user, questions=(NAME, NOTES), **settings) -> str:
    arguments = {"settings": {**SETTINGS, **settings}, "questions": list(questions)}
    return _error(user, "create_survey", **arguments)


def test_refused_without_manage_surveys(test_user):
    assert "permission" in _create_refused(test_user)
    assert not Survey.objects.exists()


def test_creates_switched_off_with_every_type(surveys_admin):
    settings = {"description": "help us plan", "slug": "Retreat 2099", "visibility": "members_only"}
    numbers = [
        {"label": "nights", "field_type": "number"},
        {"label": "car?", "field_type": "boolean"},
    ]
    questions = [NAME, NOTES, *numbers]
    summary = _create(surveys_admin, questions, **settings)
    expected = {**settings, "slug": "retreat-2099", "is_active": False, "status": "closed"}
    assert {key: summary[key] for key in expected} == expected
    saved = SurveyQuestion.objects.filter(survey_id=summary["id"]).order_by("display_order")
    assert [q.field_type for q in saved] == [q.get("field_type", "text") for q in questions]
    assert [q.required for q in saved] == [True, False, False, False]
    entries = AuditLogEntry.objects.filter(actor=surveys_admin)
    assert entries.count() == 5 and all(e.details["via"] == "mcp" for e in entries)


def test_creates_choice_questions_with_trimmed_options(surveys_admin):
    borough = {"label": "borough", "field_type": "select", "options": [" bk ", "", "qns"]}
    bring = {"label": "bring", "field_type": "checkbox", "options": ["tent"]}
    summary = _create(surveys_admin, (FOOD, borough, bring))
    saved = SurveyQuestion.objects.filter(survey_id=summary["id"]).order_by("display_order")
    assert [(q.field_type, q.options) for q in saved] == [
        ("radio", ["vegan", "very vegan"]),
        ("select", ["bk", "qns"]),
        ("checkbox", ["tent"]),
    ]


@pytest.mark.parametrize(
    ("questions", "changes", "message"),
    [
        (({"label": "pick", "field_type": "radio"},), {}, "radio questions need at least one"),
        (({"label": "name", "options": ["x"]},), {}, "text questions take no options"),
        (({"label": "rate", "field_type": "rating"},), {}, "field_type"),
        (({"label": "why", "show_if": {"position": 1, "value": "x"}},), {}, "show_if"),
        (({"label": "  "},), {}, "at least 1 character"),
        (({"label": "x" * 301},), {}, '"field": "label"'),
        ((NAME,), {"title": " "}, "at least 1 character"),
        ((NAME,), {"title": "🌱🌱"}, "give a slug"),
        ((NAME,), {"closes_on": "2099-07-04"}, "closes_on"),
        ((NAME,), {"feedback_event_type": "official"}, "feedback_event_type"),
    ],
)
def test_bad_input_refused_before_writing(surveys_admin, questions, changes, message):
    assert message in _create_refused(surveys_admin, questions, **changes)
    assert not Survey.objects.exists()


def test_duplicate_slug_refused(surveys_admin):
    Survey.objects.create(title="old", slug="retreat-planning")
    error = json.loads(_create_refused(surveys_admin))
    assert (error["status"], error["detail"][0]["code"]) == (400, Code.Survey.SLUG_ALREADY_EXISTS)


def _second_question_fails(error: BaseException):
    calls = []

    def view(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise error
        return create_question_view(*args, **kwargs)

    return patch("mcp_gateway.tools.surveys_write.create_question_view", view)


def test_failure_midway_leaves_no_survey(surveys_admin):
    with _second_question_fails(ToolError("bad question")):
        assert _create_refused(surveys_admin) == "nothing was saved: question 2: bad question"
    with _second_question_fails(RuntimeError("db went away")):
        with pytest.raises(UnexpectedToolError) as exc_info:
            _create(surveys_admin)
    assert str(exc_info.value.__cause__) == "db went away"
    assert not (Survey.objects.exists() or SurveyQuestion.objects.exists())


@pytest.mark.parametrize(
    ("view", "cancel_at"),
    [("create_survey_view", 0.1), ("create_question_view", 0.1), ("create_question_view", 0.45)],
    ids=["survey", "first_question", "last_question"],
)
def test_cancel_midway_leaves_no_survey(surveys_admin, view, cancel_at):
    real = getattr(surveys_write, view)

    def slow(*args, **kwargs):
        time.sleep(0.3)
        return real(*args, **kwargs)

    async def cancel_midway():
        with anyio.move_on_after(cancel_at):
            arguments = {"settings": SETTINGS, "questions": [NAME, NOTES]}
            await pda_mcp.call_tool("create_survey", arguments)
        await anyio.sleep(0.5)  # lets an unshielded view thread finish, as it would in production

    reset = _signed_in(surveys_admin)
    try:
        with patch(f"mcp_gateway.tools.surveys_write.{view}", slow):
            anyio.run(cancel_midway)
    finally:
        auth_context_var.reset(reset)
    assert not (Survey.objects.exists() or SurveyQuestion.objects.exists())


def _failing_delete():
    return patch("mcp_gateway.tools.surveys_write.delete_survey_view", side_effect=RuntimeError)


def test_failed_cleanup_points_at_the_partial_survey(surveys_admin, caplog):
    with _second_question_fails(ToolError("bad question")), _failing_delete():
        error = _create_refused(surveys_admin)
    survey_id = Survey.objects.get().pk
    assert error == (
        f"creating the survey failed (question 2: bad question) and the partial survey "
        f"{survey_id} couldn't be removed; delete it at {BASE_URL}/admin/surveys/{survey_id}"
    )
    record = next(r for r in caplog.records if r.name == surveys_write.__name__)
    assert (record.levelname, str(survey_id) in record.getMessage()) == ("ERROR", True)
    assert record.exc_info


def test_failed_cleanup_hides_internal_error_details(surveys_admin, caplog):
    with _second_question_fails(RuntimeError("relation secret_table is locked")), _failing_delete():
        error = _create_refused(surveys_admin)
    assert "creating the survey failed (an internal error)" in error
    assert "secret_table" not in error and "RuntimeError" not in error
    assert any("secret_table" in r.getMessage() for r in caplog.records if r.levelname == "ERROR")


def test_cancel_with_failed_cleanup_stays_cancelled_and_logs(surveys_admin, caplog):
    def slow(*args, **kwargs):
        time.sleep(0.3)
        return create_question_view(*args, **kwargs)

    async def cancel() -> bool:
        with anyio.move_on_after(0.1) as scope:
            arguments = {"settings": SETTINGS, "questions": [NAME, NOTES]}
            await pda_mcp.call_tool("create_survey", arguments)
        return scope.cancelled_caught

    reset = _signed_in(surveys_admin)
    try:
        with patch.object(surveys_write, "create_question_view", slow), _failing_delete():
            assert anyio.run(cancel)
    finally:
        auth_context_var.reset(reset)
    survey_id = str(Survey.objects.get().pk)
    assert any(survey_id in r.getMessage() for r in caplog.records if r.levelname == "ERROR")


def test_saves_every_setting_in_new_york_time(surveys_admin):
    event = Event.objects.create(title="x", start_datetime=timezone.now() + timedelta(7))
    settings = {
        **{"anonymous": True, "one_response_per_user": True, "max_responses": 40},
        **{"opens_at": "2099-07-04T09:00", "closes_at": "2099-12-05T17:00:00-05:00"},
        **{"linked_event_id": str(event.pk), "confirmation_message": "thanks!"},
    }
    summary = _create(surveys_admin, **settings)
    expected = {**settings, "opens_at": "2099-07-04T09:00:00-04:00"}
    assert {key: summary[key] for key in expected} == expected


def test_wrong_new_york_offset_refused(surveys_admin):
    error = _create_refused(surveys_admin, closes_at="2099-07-04T11:00:00-05:00")
    assert "new york is at -04:00 on 2099-07-04" in error
    assert not Survey.objects.exists()
