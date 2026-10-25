import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from community.models import Survey, SurveyResponse
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.server import BASE_URL, pda_mcp
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests.test_mcp_server import _signed_in

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


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
        return asyncio.run(pda_mcp.call_tool(name, arguments)).structured_content  # type: ignore[union-attr]
    finally:
        auth_context_var.reset(token)


def _tool_names(user) -> set[str]:
    token = _signed_in(user)
    try:
        return {tool.name for tool in asyncio.run(pda_mcp.list_tools())}
    finally:
        auth_context_var.reset(token)


def test_list_surveys_needs_manage_surveys(test_user, surveys_admin):
    assert "list_surveys" not in _tool_names(test_user)
    assert "list_surveys" in _tool_names(surveys_admin)
    with pytest.raises(ToolError, match="permission"):
        _call(test_user, "list_surveys")


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
        "url": f"{BASE_URL}/surveys/old",
        "edit_url": f"{BASE_URL}/admin/surveys/{old.id}",
    }


def test_list_surveys_pages(surveys_admin):
    for day in range(5):
        _survey(f"s{day}", days_ago=day)
    first = _call(surveys_admin, "list_surveys", limit=2)
    assert ([r["slug"] for r in first["surveys"]], first["next_offset"]) == (["s0", "s1"], 2)
    last = _call(surveys_admin, "list_surveys", limit=2, offset=4)
    assert ([r["slug"] for r in last["surveys"]], last["next_offset"]) == (["s4"], None)


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
