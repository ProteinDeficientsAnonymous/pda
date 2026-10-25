from uuid import uuid4

import pytest
from audit.models import AuditLogEntry
from community.models import Survey
from users.permissions import PermissionKey
from users.roles import Role

from tests.test_mcp_events_write import _error, _run
from tests.test_mcp_surveys_read import _tool_names

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


@pytest.fixture
def surveys_admin(test_user):
    role = Role.objects.create(name="surveys", permissions=[PermissionKey.MANAGE_SURVEYS])
    test_user.roles.add(role)
    return test_user


def _survey(**fields) -> Survey:
    return Survey.objects.create(**{"title": "retreat", "slug": "retreat", **fields})


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
