import json
import time
from unittest.mock import patch

import anyio
import pytest
from audit.models import AuditLogEntry
from community._surveys import create_survey as create_survey_view
from community._validation import Code
from community.models import Survey
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp_gateway.server import pda_mcp
from users.permissions import PermissionKey
from users.roles import Role

from tests.test_mcp_events_write import _error, _run
from tests.test_mcp_server import _signed_in

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)
SETTINGS = {"title": "Retreat Planning!"}


@pytest.fixture
def surveys_admin(test_user):
    role = Role.objects.create(name="surveys", permissions=[PermissionKey.MANAGE_SURVEYS])
    test_user.roles.add(role)
    return test_user


def _create(user, **settings) -> dict:
    return _run(user, "create_survey", settings={**SETTINGS, **settings})


def _create_refused(user, **settings) -> str:
    return _error(user, "create_survey", settings={**SETTINGS, **settings})


def test_refused_without_manage_surveys(test_user):
    assert "permission" in _create_refused(test_user)
    assert not Survey.objects.exists()


def test_creates_switched_off(surveys_admin):
    settings = {"description": "help us plan", "slug": "Retreat 2099", "visibility": "members_only"}
    summary = _create(surveys_admin, **settings)
    expected = {**settings, "slug": "retreat-2099", "is_active": False, "status": "closed"}
    assert {key: summary[key] for key in expected} == expected
    entry = AuditLogEntry.objects.get(actor=surveys_admin)
    assert (entry.action, entry.target_id, entry.details["via"]) == (
        "survey_created",
        summary["id"],
        "mcp",
    )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"title": " "}, "at least 1 character"),
        ({"title": "🌱🌱"}, "give a slug"),
        ({"closes_on": "2099-07-04"}, "closes_on"),
        ({"feedback_event_type": "official"}, "feedback_event_type"),
    ],
)
def test_bad_settings_refused_before_writing(surveys_admin, changes, message):
    assert message in _create_refused(surveys_admin, **changes)
    assert not Survey.objects.exists()


def test_duplicate_slug_refused(surveys_admin):
    Survey.objects.create(title="old", slug="retreat-planning")
    error = json.loads(_create_refused(surveys_admin))
    assert (error["status"], error["detail"][0]["code"]) == (400, Code.Survey.SLUG_ALREADY_EXISTS)


def _cancel_midway(user, view: str, real, arguments: dict) -> None:
    def slow(*args, **kwargs):
        time.sleep(0.3)
        return real(*args, **kwargs)

    async def cancel():
        with anyio.move_on_after(0.1):
            await pda_mcp.call_tool("create_survey", arguments)
        await anyio.sleep(0.5)  # lets an unshielded view thread finish, as it would in production

    reset = _signed_in(user)
    try:
        with patch(f"mcp_gateway.tools.surveys_write.{view}", slow):
            anyio.run(cancel)
    finally:
        auth_context_var.reset(reset)


def test_cancel_during_create_leaves_no_survey(surveys_admin):
    _cancel_midway(surveys_admin, "create_survey_view", create_survey_view, {"settings": SETTINGS})
    assert not Survey.objects.exists()
