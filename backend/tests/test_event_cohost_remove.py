"""Tests for removing accepted co-hosts (issue #384).

Two flows share the DELETE endpoint:
- A host kicks an accepted co-host.
- A co-host steps down themselves (with a last-host guard).

The pending-invite rescind flow lives in test_event_cohost_invites.py.
"""

import json

import pytest
from community.models import (
    CoHostInviteStatus,
    Event,
    EventCoHostInvite,
    EventStatus,
)
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from users.models import User

from tests.conftest import future_iso

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_user(phone: str, name: str = "Member") -> User:
    return User.objects.create_user(
        phone_number=phone,
        password="testpass123",
        display_name=name,
    )


def _auth_headers(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


def _create_event(api_client, creator: User, co_host_ids: list[str]) -> str:
    response = api_client.post(
        "/api/community/events/",
        data=json.dumps(
            {
                "title": "Community Potluck",
                "start_datetime": future_iso(days=30),
                "end_datetime": future_iso(days=30, hours=2),
                "status": EventStatus.ACTIVE,
                "co_host_ids": co_host_ids,
            }
        ),
        content_type="application/json",
        **_auth_headers(creator),
    )
    assert response.status_code == 201, response.content
    return response.json()["id"]


def _accept_invite(api_client, event_id: str, invite_id: str, invitee: User) -> None:
    response = api_client.post(
        f"/api/community/events/{event_id}/cohost-invites/{invite_id}/accept/",
        **_auth_headers(invitee),
    )
    assert response.status_code == 200, response.content


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def creator(db) -> User:
    return _make_user("+12025550221", "Creator")


@pytest.fixture
def cohost(db) -> User:
    return _make_user("+12025550222", "Cohost")


@pytest.fixture
def stranger(db) -> User:
    return _make_user("+12025550223", "Stranger")


@pytest.fixture
def event_with_accepted_cohost(db, api_client, creator, cohost) -> tuple[Event, EventCoHostInvite]:
    event_id = _create_event(api_client, creator, co_host_ids=[str(cohost.pk)])
    invite = EventCoHostInvite.objects.get(event_id=event_id, user=cohost)
    _accept_invite(api_client, event_id, str(invite.id), cohost)
    invite.refresh_from_db()
    return Event.objects.get(id=event_id), invite


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRemoveAcceptedCoHost:
    def test_host_can_remove_accepted_cohost(
        self, api_client, creator, event_with_accepted_cohost, cohost
    ):
        event, invite = event_with_accepted_cohost
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/",
            **_auth_headers(creator),
        )
        assert response.status_code == 200
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.REMOVED
        assert event.co_hosts.filter(pk=cohost.pk).exists() is False

    def test_host_removal_notifies_removed_cohost(
        self, api_client, creator, event_with_accepted_cohost, cohost
    ):
        event, invite = event_with_accepted_cohost
        Notification.objects.all().delete()
        api_client.delete(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/",
            **_auth_headers(creator),
        )
        notif = Notification.objects.get(recipient=cohost)
        assert notif.notification_type == NotificationType.COHOST_REMOVED
        assert "removed you" in notif.message

    def test_cohost_can_step_down(self, api_client, event_with_accepted_cohost, cohost):
        event, invite = event_with_accepted_cohost
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/",
            **_auth_headers(cohost),
        )
        assert response.status_code == 200
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.REMOVED
        assert event.co_hosts.filter(pk=cohost.pk).exists() is False

    def test_self_step_down_does_not_notify(self, api_client, event_with_accepted_cohost, cohost):
        event, invite = event_with_accepted_cohost
        Notification.objects.all().delete()
        api_client.delete(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/",
            **_auth_headers(cohost),
        )
        # Step-down: nobody gets notified — neither the cohost (self-action)
        # nor the creator (matches existing decline-policy precedent of "no
        # spam for routine roster changes").
        assert Notification.objects.count() == 0

    def test_outsider_cannot_remove_accepted_cohost(
        self, api_client, event_with_accepted_cohost, stranger
    ):
        event, invite = event_with_accepted_cohost
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/",
            **_auth_headers(stranger),
        )
        assert response.status_code == 403

    def test_last_host_cannot_step_down(self, api_client, event_with_accepted_cohost, cohost):
        # Set the scene: cohost is accepted, then creator deletes their account
        # so created_by gets nulled (SET_NULL). cohost is now the only host.
        event, invite = event_with_accepted_cohost
        Event.objects.filter(pk=event.pk).update(created_by=None)
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/",
            **_auth_headers(cohost),
        )
        assert response.status_code == 400
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.ACCEPTED  # unchanged
        assert event.co_hosts.filter(pk=cohost.pk).exists()

    def test_host_can_remove_last_cohost_even_if_creator_is_set(
        self, api_client, creator, event_with_accepted_cohost
    ):
        # Sanity check the inverse of the last-host guard: with creator set,
        # removing the only co-host is fine — the creator is still a host.
        event, invite = event_with_accepted_cohost
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/",
            **_auth_headers(creator),
        )
        assert response.status_code == 200
