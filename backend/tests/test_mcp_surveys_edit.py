import asyncio
import json
from unittest.mock import DEFAULT, patch
from uuid import uuid4

import pytest
from audit.models import AuditLogEntry
from community._surveys import delete_survey_question, get_survey_admin
from community.models import Survey, SurveyQuestion
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from users.permissions import PermissionKey
from users.roles import Role

from tests.test_mcp_events_write import _error, _run
from tests.test_mcp_surveys_read import _tool_names

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)
LABELS = ["food?", "why?", "notes"]
REMOVE_VIEW = "mcp_gateway.survey_edit_questions.delete_question_view"
SETTINGS_VIEW = "mcp_gateway.survey_edit_plan.update_survey_view"
TOOL = "mcp_gateway.tools.surveys_edit"


@pytest.fixture
def surveys_admin(test_user):
    role = Role.objects.create(name="surveys", permissions=[PermissionKey.MANAGE_SURVEYS])
    test_user.roles.add(role)
    return test_user


def _survey(**fields) -> Survey:
    return Survey.objects.create(**{"title": "retreat", "slug": "retreat", **fields})


def _questions(survey) -> list[SurveyQuestion]:
    food = SurveyQuestion.objects.create(
        survey=survey, label="food?", field_type="radio", options=["vegan", "very"]
    )
    when = {"question_id": str(food.pk), "operator": "equals", "value": "very"}
    why = SurveyQuestion.objects.create(survey=survey, label="why?", display_order=1, show_if=when)
    return [food, why, SurveyQuestion.objects.create(survey=survey, label="notes", display_order=2)]


def _labels(survey) -> list[str]:
    return [q.label for q in SurveyQuestion.objects.filter(survey=survey)]


def _remove(ref) -> dict:
    return {"op": "remove", "question": ref}


def _edit(user, survey, **arguments) -> dict:
    return _run(user, "update_survey", survey=str(survey.pk), **arguments)


def _refused(user, survey, **arguments) -> str:
    return _error(user, "update_survey", survey=str(survey.pk), **arguments)


def test_hidden_and_refused_without_manage_surveys(test_user):
    survey = _survey(is_active=False)
    assert "update_survey" not in _tool_names(test_user)
    assert "permission" in _refused(test_user, survey, settings={"title": "x"})
    assert Survey.objects.get().title == "retreat"


def test_switched_off_saves_at_once_via_mcp(surveys_admin):
    survey = _survey(is_active=False, description="keep", max_responses=5)
    settings = {"title": "Retreat 2099", "slug": "", "opens_at": "2099-07-04T09:00"}
    result = _edit(surveys_admin, survey, settings={**settings, "max_responses": None})
    expected = {**settings, "slug": "retreat-2099", "opens_at": "2099-07-04T09:00:00-04:00"}
    assert {key: result[key] for key in expected} == expected
    assert (result["max_responses"], result["description"]) == (None, "keep")
    entry = AuditLogEntry.objects.get(action="survey_updated")
    assert sorted(entry.details["fields_changed"]) == ["max_responses", "opens_at", "slug", "title"]
    assert entry.details["via"] == "mcp"


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({}, "no changes given"),
        ({"title": " "}, "at least 1 character"),
        ({"slug": "🌱"}, "give a slug"),
        ({"is_active": True}, "Extra inputs are not permitted"),
    ],
)
def test_bad_settings_refused_before_saving(surveys_admin, changes, message):
    survey = _survey(is_active=False)
    assert message in _refused(surveys_admin, survey, settings=changes)
    assert not AuditLogEntry.objects.filter(action="survey_updated").exists()


def test_switched_on_refused(surveys_admin):
    survey = _survey()
    assert "switched on" in _refused(surveys_admin, survey, settings={"title": "new"})
    assert Survey.objects.get().title == "retreat"


def test_feedback_survey_keeps_its_forced_settings(surveys_admin):
    survey = _survey(is_active=False, feedback_event_type="official", anonymous=True)
    for settings in ({"anonymous": False}, {"linked_event_id": str(uuid4())}):
        assert "always anonymous" in _refused(surveys_admin, survey, settings=settings)
    assert _edit(surveys_admin, survey, settings={"anonymous": True, "title": "x"})["title"] == "x"


def test_failed_save_says_nothing_was_saved(surveys_admin):
    survey = _survey(is_active=False)
    with patch(SETTINGS_VIEW, side_effect=ToolError("bad")):
        error = _refused(surveys_admin, survey, settings={"title": "x"})
    assert error == "nothing was saved: settings failed: bad"
    with patch(SETTINGS_VIEW, side_effect=RuntimeError("db went away")):
        with pytest.raises(UnexpectedToolError) as exc_info:
            _edit(surveys_admin, survey, settings={"title": "x"})
    assert str(exc_info.value.__cause__) == "db went away"


def test_failed_reload_after_a_full_save_still_says_saved(surveys_admin):
    survey = _survey(is_active=False)
    reload_fails = [DEFAULT, RuntimeError("blip")]
    with patch(f"{TOOL}.get_survey_view", wraps=get_survey_admin, side_effect=reload_fails):
        result = _edit(surveys_admin, survey, settings={"title": "x"})
    assert result["saved"] and "call get_survey" in result["note"]
    assert "blip" not in result["note"] and Survey.objects.get().title == "x"


def test_cancel_between_steps_is_logged(surveys_admin, caplog):
    survey = _survey(is_active=False)
    with patch(f"{TOOL}.checkpoint", side_effect=asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):
            _edit(surveys_admin, survey, settings={"title": "x"})
    assert f"cancelled on survey {survey.pk} after ['settings']" in caplog.text


def test_remove_by_position_or_id_clears_conditions_via_mcp(surveys_admin):
    survey = _survey(is_active=False)
    _, why, _ = _questions(survey)
    result = _edit(surveys_admin, survey, questions=[_remove(1), _remove(str(why.pk))])
    assert [q["label"] for q in result["questions"]] == ["notes"] == _labels(survey)
    entries = AuditLogEntry.objects.filter(action="survey_question_deleted")
    assert [e.details["via"] for e in entries] == ["mcp", "mcp"]


@pytest.mark.parametrize(
    ("ops", "message"),
    [
        ([_remove(4)], "operation 1: there's no question 4: the survey has 3"),
        ([_remove("00000000-0000-0000-0000-000000000000")], "no question with id"),
        ([_remove(1), _remove(1)], "operation 2: question 1"),
        ([{"op": "update", "question": 1}], "Input should be 'remove'"),
        ([{**_remove(1), "after": 2}], "Extra inputs are not permitted"),
        ([_remove(True)], "Input should be a valid integer"),
    ],
)
def test_bad_question_changes_refused_before_saving(surveys_admin, ops, message):
    survey = _survey(is_active=False)
    _questions(survey)
    assert message in _refused(surveys_admin, survey, settings={"title": "x"}, questions=ops)
    assert (Survey.objects.get().title, _labels(survey)) == ("retreat", LABELS)


def test_failure_midway_reports_what_was_saved(surveys_admin):
    survey = _survey(is_active=False)
    _questions(survey)
    arguments = {"settings": {"title": "x"}, "questions": [_remove(3), _remove(2)]}
    second_fails = [DEFAULT, RuntimeError("db went away")]
    with patch(REMOVE_VIEW, wraps=delete_survey_question, side_effect=second_fails):
        report = json.loads(_refused(surveys_admin, survey, **arguments))
    assert report["error"].endswith('operation 2: remove question 2 ("why?") failed unexpectedly')
    assert report["applied"] == ["settings", 'operation 1: remove question 3 ("notes")']
    assert report["not_applied"] == ['operation 2: remove question 2 ("why?")']
    assert [q["label"] for q in report["survey"]["questions"]] == ["food?", "why?"]
    assert report["survey"]["title"] == "x"
