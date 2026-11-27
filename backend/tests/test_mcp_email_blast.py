from unittest.mock import patch

import pytest
from notifications.email_types import BatchSendResult
from users.models import MembershipStatus
from users.permissions import PermissionKey

from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._users import make_user

pytestmark = pytest.mark.django_db
TOOL = "send_member_email_blast"
BODY = {"subject": "hello", "body_html": "<p>hi</p>"}


@pytest.fixture
def send_batch():
    with patch("notifications.member_blasts.service.get_email_sender") as get:
        get.return_value.send_batch.return_value = BatchSendResult(accepted=2)
        yield get.return_value.send_batch


@pytest.fixture
def admin():
    return make_user(
        PermissionKey.SEND_EMAIL_BLAST, membership_status=MembershipStatus.ACTIVE_MEMBER
    )


def test_tool_needs_permission():
    assert TOOL not in tool_names(make_user())
    assert TOOL in tool_names(make_user(PermissionKey.SEND_EMAIL_BLAST))


def test_first_call_previews_without_sending(admin, send_batch):
    result = run_tool(admin, TOOL, **BODY)

    assert result["confirm_token"]
    assert "recipient_count" in result
    send_batch.assert_not_called()


def test_confirm_sends_once(admin, send_batch):
    token = run_tool(admin, TOOL, **BODY)["confirm_token"]

    assert run_tool(admin, TOOL, **BODY, confirm_token=token)["status"] == "sent"
    assert "already used" in tool_error(admin, TOOL, **BODY, confirm_token=token)
    assert send_batch.call_count == 1


def test_token_bound_to_body(admin, send_batch):
    token = run_tool(admin, TOOL, **BODY)["confirm_token"]
    other = {**BODY, "body_html": "<p>different</p>"}

    assert "doesn't match" in tool_error(admin, TOOL, **other, confirm_token=token)
    send_batch.assert_not_called()


def test_send_test_to_me(admin, send_batch):
    assert run_tool(admin, TOOL, **BODY, send_test_to_me=True) == {"test_sent_to": "you"}


def test_confirm_without_permission_fails(admin, send_batch):
    token = run_tool(admin, TOOL, **BODY)["confirm_token"]
    admin.roles.clear()

    assert tool_error(admin, TOOL, **BODY, confirm_token=token)
    send_batch.assert_not_called()
