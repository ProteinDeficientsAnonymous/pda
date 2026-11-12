from unittest.mock import patch

import pytest
from community.models import EventType, RSVPStatus
from django.utils import timezone
from notifications.models import Notification
from users.models import MembershipStatus

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._events import make_event, make_rsvp
from tests._users import make_attendance_paused, make_user

pytestmark = pytest.mark.django_db


def _invite(api_client, event, host, invitee):
    with patch("community.events._invite_email.send_event_invite_email") as send:
        response = api_client.post(
            f"/api/community/events/{event.id}/invitations/",
            {"user_ids": [str(invitee.pk)]},
            content_type="application/json",
            **auth_headers_for(host),
        )
    return response, send


def _hosted_event(event_type=EventType.COMMUNITY):
    host = make_user()
    event = make_event(rsvp_enabled=True, event_type=event_type, created_by=host)
    event.co_hosts.add(host)
    return host, event


def _limited_users():
    return [make_user(membership_status=MembershipStatus.TENTATIVE), make_attendance_paused()]


def test_limited_user_cannot_be_invited_to_community_event(api_client):
    host, event = _hosted_event()
    for invitee in _limited_users():
        response, send = _invite(api_client, event, host, invitee)
        assert response.status_code == 400
        assert_error_code(response, "event.guest_not_eligible")
        send.assert_not_called()
    assert not event.invited_users.exists()
    assert not Notification.objects.exists()


@pytest.mark.parametrize(
    "fields",
    [
        {"membership_status": MembershipStatus.ARCHIVED, "archived_at": timezone.now()},
        {"membership_status": MembershipStatus.GUIDELINES_PAUSED},
        {"membership_status": MembershipStatus.NONE},
    ],
)
def test_user_who_cannot_sign_in_cannot_be_invited(api_client, fields):
    host, event = _hosted_event(EventType.OFFICIAL)
    response, _ = _invite(api_client, event, host, make_user(**fields))
    assert response.status_code == 400
    assert not event.invited_users.exists()


@pytest.mark.parametrize("event_type", [EventType.OFFICIAL, EventType.CLUB])
def test_limited_user_can_be_invited_to_official_or_club_event(api_client, event_type):
    host, event = _hosted_event(event_type)
    for invitee in _limited_users():
        response, _ = _invite(api_client, event, host, invitee)
        assert response.status_code == 200
    assert event.invited_users.count() == 2


def _comments_url(event):
    return f"/api/community/events/{event.id}/comments/"


def test_limited_guest_cannot_read_or_post_community_comments(api_client):
    _, event = _hosted_event()
    guest = make_attendance_paused()
    make_rsvp(event, guest, RSVPStatus.ATTENDING)
    listed = api_client.get(_comments_url(event), **auth_headers_for(guest))
    assert listed.status_code == 200
    assert listed.json()["can_post"] is False
    posted = api_client.post(
        _comments_url(event),
        {"body": "hi"},
        content_type="application/json",
        **auth_headers_for(guest),
    )
    assert posted.status_code == 403


def test_limited_guest_can_post_official_comments(api_client):
    _, event = _hosted_event(EventType.OFFICIAL)
    guest = make_attendance_paused()
    make_rsvp(event, guest, RSVPStatus.ATTENDING)
    posted = api_client.post(
        _comments_url(event),
        {"body": "hi"},
        content_type="application/json",
        **auth_headers_for(guest),
    )
    assert posted.status_code == 201
