from datetime import timedelta

import pytest
from audit.models import AuditLogEntry
from community.models import Event, EventStatus, InvitePermission
from django.utils import timezone
from notifications.models import Notification

from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._users import make_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def make_event(test_user):
    def make(status=EventStatus.ACTIVE, days=7, **fields) -> Event:
        start = timezone.now() + timedelta(days=days)
        event = Event.objects.create(
            title="walk", created_by=test_user, start_datetime=start, status=status, **fields
        )
        event.co_hosts.add(test_user)
        return event

    return make


@pytest.fixture
def guest(db):
    return make_user(first_name="Robin", last_name="Oak")


def _invite(user, event, *members, **arguments):
    ids = [str(m.pk) for m in members]
    return run_tool(user, "invite_to_event", event=str(event.pk), member_ids=ids, **arguments)


def _refused(user, event, *members, **arguments) -> str:
    ids = [str(m.pk) for m in members]
    return tool_error(user, "invite_to_event", event=str(event.pk), member_ids=ids, **arguments)


def test_search_members_returns_ids_and_names_for_any_member(test_user, guest):
    assert {"search_members", "invite_to_event"} <= tool_names(test_user)
    rows = run_tool(test_user, "search_members", query="robin")["result"]
    assert rows == [{"id": str(guest.pk), "name": "Robin Oak"}]


def test_draft_invites_right_away_without_notifying(test_user, guest, make_event):
    event = make_event(EventStatus.DRAFT)
    assert _invite(test_user, event, guest)["invited"] == ["Robin Oak"]
    assert list(event.invited_users.all()) == [guest]
    assert not Notification.objects.filter(recipient=guest).exists()


def test_published_event_previews_then_invites_and_notifies(
    test_user, guest, make_event, fake_email_sender
):
    event = make_event()
    preview = _invite(test_user, event, guest)
    assert preview["would_invite"] == ["Robin Oak"]
    assert not event.invited_users.exists()
    done = _invite(test_user, event, guest, confirm_token=preview["confirm_token"])
    assert done["invited"] == ["Robin Oak"]
    assert Notification.objects.filter(recipient=guest, event=event).exists()
    assert fake_email_sender.send.called
    entry = AuditLogEntry.objects.get(action="event_invitations_added", target_id=str(event.pk))
    assert entry.details["via"] == "mcp"


def test_token_bound_to_the_invitees(test_user, guest, make_event):
    event, other = make_event(), make_user(first_name="Sky")
    token = _invite(test_user, event, guest)["confirm_token"]
    assert "fresh preview" in _refused(test_user, event, other, confirm_token=token)
    assert not event.invited_users.exists()


def test_refuses_already_invited_and_unknown_members(test_user, guest, make_event):
    event = make_event(EventStatus.DRAFT)
    event.invited_users.add(guest)
    assert _refused(test_user, event, guest) == "everyone listed is already invited"
    onboarding = make_user(needs_onboarding=True)
    assert "use search_members" in _refused(test_user, event, onboarding)


def test_non_host_needs_the_event_to_allow_member_invites(guest, make_event):
    event = make_event(invite_permission=InvitePermission.CO_HOSTS_ONLY)
    member = make_user()
    assert "permission" in _refused(member, event, guest)
    Event.objects.filter(pk=event.pk).update(invite_permission=InvitePermission.ALL_MEMBERS)
    assert _invite(member, event, guest)["would_invite"] == ["Robin Oak"]


@pytest.mark.parametrize(
    ("fields", "reason"),
    [({"status": EventStatus.CANCELLED}, "cancelled"), ({"days": -7}, "already happened")],
)
def test_refuses_cancelled_and_past_events(test_user, guest, make_event, fields, reason):
    assert reason in _refused(test_user, make_event(**fields), guest)
