import json
import time
from datetime import timedelta
from unittest.mock import patch

import anyio
import pytest
from asgiref.sync import async_to_sync
from audit.models import AuditLogEntry
from community._surveys import create_survey_question as create_question_view
from community._validation import Code
from community.models import Event, Survey, SurveyQuestion
from django.utils import timezone
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from mcp_gateway.confirm import MAX_AGE_SECONDS
from mcp_gateway.server import BASE_URL, pda_mcp
from mcp_gateway.tools import surveys_write
from users.permissions import PermissionKey
from users.roles import Role

from tests.test_mcp_events_write import _error, _run
from tests.test_mcp_server import _signed_in

pytestmark = pytest.mark.django_db
SETTINGS = {"title": "Retreat Planning!"}
NAME = {"label": "name", "required": True}
NOTES = {"label": "notes", "field_type": "textarea"}
FOOD = {"label": "food?", "field_type": "radio", "options": ["vegan", "very vegan"]}
WHY = {"label": "why?", "show_if": {"position": 1, "value": "very vegan"}}
SECTION = {"label": "about you", "field_type": "section", "description": " optional "}
POLL = {"label": "when", "field_type": "datetime_poll", "options": ["2099-11-07T11:00"]}


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


def _publish(user, survey_id, **arguments) -> dict:
    return _run(user, "publish_survey", survey=survey_id, **arguments)


def _publish_refused(user, survey_id, **arguments) -> str:
    return _error(user, "publish_survey", survey=survey_id, **arguments)


def test_publish_two_step(surveys_admin):
    survey_id = _create(surveys_admin)["id"]
    preview = _publish(surveys_admin, survey_id)
    assert (preview["is_active"], preview["notes"]) == (False, [])
    assert not Survey.objects.get(pk=survey_id).is_active
    published = _publish(surveys_admin, survey_id, confirm_token=preview["confirm_token"])
    assert published["is_active"] and Survey.objects.get(pk=survey_id).is_active
    entry = AuditLogEntry.objects.get(action="survey_updated")
    assert (entry.details["fields_changed"], entry.details["via"]) == (["is_active"], "mcp")


def test_publish_token_single_use_and_refused_once_on(surveys_admin):
    survey_id = _create(surveys_admin)["id"]
    token = _publish(surveys_admin, survey_id)["confirm_token"]
    _publish(surveys_admin, survey_id, confirm_token=token)
    assert "already switched on" in _publish_refused(surveys_admin, survey_id, confirm_token=token)
    Survey.objects.filter(pk=survey_id).update(is_active=False)
    assert "already used" in _publish_refused(surveys_admin, survey_id, confirm_token=token)


def test_publish_token_bound_to_member_survey_and_age(surveys_admin, manage_users_user):
    survey_id = _create(surveys_admin)["id"]
    other_id = _create(surveys_admin, slug="other")["id"]
    manage_users_user.roles.add(*surveys_admin.roles.all())
    token = _publish(surveys_admin, survey_id)["confirm_token"]
    assert "fresh preview" in _publish_refused(manage_users_user, survey_id, confirm_token=token)
    assert "fresh preview" in _publish_refused(surveys_admin, other_id, confirm_token=token)
    later = timezone.now().timestamp() + MAX_AGE_SECONDS + 1
    with patch("django.core.signing.time.time", return_value=later):
        assert "fresh preview" in _publish_refused(surveys_admin, survey_id, confirm_token=token)
    assert not Survey.objects.get(pk=survey_id).is_active


@pytest.mark.parametrize(
    "change",
    [
        lambda pk: Survey.objects.filter(pk=pk).update(title="changed"),
        lambda pk: Survey.objects.filter(pk=pk).update(feedback_event_type="official"),
        lambda pk: SurveyQuestion.objects.filter(survey_id=pk, label="notes").update(label="x"),
    ],
    ids=["title", "feedback_event_type", "question"],
)
def test_publish_token_bound_to_survey_state(surveys_admin, change):
    survey_id = _create(surveys_admin)["id"]
    token = _publish(surveys_admin, survey_id)["confirm_token"]
    change(survey_id)
    assert "fresh preview" in _publish_refused(surveys_admin, survey_id, confirm_token=token)
    assert not Survey.objects.get(pk=survey_id).is_active


def test_feedback_survey_preview_warns_about_emails(surveys_admin):
    survey_id = _create(surveys_admin)["id"]
    Survey.objects.filter(pk=survey_id).update(feedback_event_type="club")
    preview = _publish(surveys_admin, survey_id)
    assert (preview["feedback_event_type"], preview["url"]) == ("club", None)
    assert "starts the daily feedback emails" in preview["notes"][0]


def test_refused_without_manage_surveys(test_user):
    assert "permission" in _create_refused(test_user)
    survey = Survey.objects.create(title="old", slug="old", is_active=False)
    assert "permission" in _publish_refused(test_user, str(survey.pk))
    assert not Survey.objects.get().is_active


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
        (({**SECTION, "options": ["x"]},), {}, "section questions take no options"),
        (({**SECTION, "required": True},), {}, "section headers can't be required"),
        (({**NAME, "description": "x"},), {}, "only section headers take a description"),
        (({"label": "rate", "field_type": "rating", "options": ["a"] * 6},), {}, "at most 5"),
        (({**POLL, "options": ["2099-07-04T11:00Z"]},), {}, "new york is at -04:00 on"),
        ((FOOD, {**WHY, "show_if": {"position": 2, "value": "vegan"}}), {}, "earlier question"),
        ((FOOD, {**WHY, "show_if": {"position": 3, "value": "vegan"}}), {}, "earlier question"),
        ((FOOD, {**WHY, "show_if": {"position": 1, "value": "x" * 301}}), {}, '"show_if.value"'),
        ((FOOD, {**WHY, "show_if": {**WHY["show_if"], "question_id": "x"}}), {}, "question_id"),
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


def test_creates_section_headers(surveys_admin):
    summary = _create(surveys_admin, (SECTION, NAME))
    section, name = SurveyQuestion.objects.filter(survey_id=summary["id"]).order_by("display_order")
    assert (section.field_type, section.description) == ("section", "optional")
    assert (name.field_type, name.description) == ("text", "")
    assert summary["questions"][0]["description"] == "optional"


def test_show_if_wired_to_the_created_source(surveys_admin):
    summary = _create(surveys_admin, (FOOD, NOTES, WHY))
    food = SurveyQuestion.objects.get(survey_id=summary["id"], label="food?")
    condition = {"question_id": str(food.pk), "operator": "equals", "value": "very vegan"}
    assert SurveyQuestion.objects.get(label="why?").show_if == condition
    shown = {**condition, "question_position": 1, "question": "food?"}
    assert summary["questions"][2]["show_if"] == shown


def test_condition_the_website_refuses_leaves_no_survey(surveys_admin):
    error = _create_refused(
        surveys_admin, (FOOD, {**WHY, "show_if": {"position": 1, "value": "x"}})
    )
    detail = json.loads(error.removeprefix("nothing was saved: question 2: "))
    assert detail["detail"][0]["code"] == Code.Survey.CONDITION_VALUE_INVALID
    assert not Survey.objects.exists()


def test_rating_labels_and_poll_times_stored_like_the_builder(surveys_admin):
    stars = {"label": "stars", "field_type": "rating", "options": ["meh", "", "", "great"]}
    blank = {"label": "blank", "field_type": "rating", "options": ["", " "]}
    summary = _create(surveys_admin, (stars, blank, POLL))
    saved = SurveyQuestion.objects.filter(survey_id=summary["id"]).order_by("display_order")
    assert [q.options for q in saved] == [
        ["meh", "", "", "great", ""],
        [],
        ["2099-11-07T16:00:00.000Z"],
    ]
    assert summary["questions"][2]["option_times"] == ["2099-11-07T11:00:00-05:00"]


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
            async_to_sync(cancel_midway)()
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
            assert async_to_sync(cancel)()
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
