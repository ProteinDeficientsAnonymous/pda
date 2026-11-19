import pytest
from community.models import EventStatus, EventType, RSVPStatus
from users.models import MembershipStatus

from tests._auth import auth_headers_for
from tests._events import make_event, make_rsvp
from tests._users import make_attendance_paused, make_user

pytestmark = pytest.mark.django_db


def _invite(api_client, event, user, invitee):
    return api_client.post(
        f"/api/community/events/{event.id}/invitations/",
        {"user_ids": [str(invitee.pk)]},
        content_type="application/json",
        **auth_headers_for(user),
    )


@pytest.mark.parametrize(
    ("rsvp", "status_code"),
    [(None, 403), (RSVPStatus.CANT_GO, 403), (RSVPStatus.MAYBE, 200), (RSVPStatus.ATTENDING, 200)],
)
def test_member_needs_to_have_rsvpd(api_client, rsvp, status_code):
    member, invitee = make_user(), make_user()
    event = make_event(rsvp_enabled=True)
    if rsvp:
        make_rsvp(event, member, rsvp)
    assert _invite(api_client, event, member, invitee).status_code == status_code


@pytest.mark.parametrize("fields", [{"status": EventStatus.CANCELLED}, {"rsvp_enabled": False}])
def test_host_cannot_invite_to_closed_event(api_client, fields):
    host, invitee = make_user(), make_user()
    event = make_event(**{"rsvp_enabled": True, **fields})
    event.co_hosts.add(host)
    assert _invite(api_client, event, host, invitee).status_code == 403
    assert not event.invited_users.exists()


@pytest.mark.parametrize(
    "make_limited",
    [lambda: make_user(membership_status=MembershipStatus.TENTATIVE), make_attendance_paused],
)
def test_limited_user_cannot_invite(api_client, make_limited):
    limited, invitee = make_limited(), make_user()
    event = make_event(event_type=EventType.OFFICIAL, rsvp_enabled=True)
    make_rsvp(event, limited)
    assert _invite(api_client, event, limited, invitee).status_code == 403
    assert not event.invited_users.exists()
