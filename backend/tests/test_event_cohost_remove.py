"""Tests for removing hosts from co_hosts (issue #384).

DELETE .../cohosts/{user_id}/ covers both a kick and a step-down, guarded so
the last host can't leave. The pending-invite rescind flow lives in
test_event_cohost_invites.py.
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

from tests.conftest import future_iso, past_iso

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_user(phone: str, name: str = "Member") -> User:
    return User.objects.create_user(
        phone_number=phone,
        password="testpass123",
        first_name=name,
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
            f"/api/community/events/{event.id}/cohosts/{cohost.pk}/",
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
            f"/api/community/events/{event.id}/cohosts/{cohost.pk}/",
            **_auth_headers(creator),
        )
        notif = Notification.objects.get(recipient=cohost)
        assert notif.notification_type == NotificationType.COHOST_REMOVED
        assert "removed you" in notif.message

    def test_cohost_can_step_down(self, api_client, event_with_accepted_cohost, cohost):
        event, invite = event_with_accepted_cohost
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohosts/{cohost.pk}/",
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
            f"/api/community/events/{event.id}/cohosts/{cohost.pk}/",
            **_auth_headers(cohost),
        )
        # Step-down: nobody gets notified — neither the cohost (self-action)
        # nor the creator (matches existing decline-policy precedent of "no
        # spam for routine roster changes").
        assert Notification.objects.count() == 0

    def test_outsider_cannot_remove_accepted_cohost(
        self, api_client, event_with_accepted_cohost, stranger, cohost
    ):
        event, invite = event_with_accepted_cohost
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohosts/{cohost.pk}/",
            **_auth_headers(stranger),
        )
        assert response.status_code == 403

    def test_last_host_cannot_step_down(
        self, api_client, event_with_accepted_cohost, creator, cohost
    ):
        # Simulate creator account deletion (SET_NULL + M2M cascade) — cohost is now the only host.
        event, invite = event_with_accepted_cohost
        event.co_hosts.remove(creator)
        Event.objects.filter(pk=event.pk).update(created_by=None)
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohosts/{cohost.pk}/",
            **_auth_headers(cohost),
        )
        assert response.status_code == 400
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.ACCEPTED  # unchanged
        assert event.co_hosts.filter(pk=cohost.pk).exists()

    def test_host_can_remove_last_cohost_even_if_creator_is_set(
        self, api_client, creator, event_with_accepted_cohost, cohost
    ):
        # Sanity check the inverse of the last-host guard: with creator set,
        # removing the only co-host is fine — the creator is still a host.
        event, invite = event_with_accepted_cohost
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohosts/{cohost.pk}/",
            **_auth_headers(creator),
        )
        assert response.status_code == 200

    def test_cohost_can_remove_the_creator(
        self, api_client, creator, cohost, event_with_accepted_cohost
    ):
        event, _invite = event_with_accepted_cohost
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohosts/{creator.pk}/",
            **_auth_headers(cohost),
        )
        assert response.status_code == 200
        assert not event.co_hosts.filter(pk=creator.pk).exists()
        event.refresh_from_db()
        assert event.created_by_id == creator.pk  # audit field untouched

    def test_stepped_down_creator_can_be_reinvited(
        self, api_client, creator, cohost, event_with_accepted_cohost
    ):
        event, _invite = event_with_accepted_cohost
        api_client.delete(
            f"/api/community/events/{event.id}/cohosts/{creator.pk}/",
            **_auth_headers(creator),
        )
        assert not event.co_hosts.filter(pk=creator.pk).exists()
        response = api_client.patch(
            f"/api/community/events/{event.id}/",
            data=json.dumps({"co_host_ids": [str(creator.pk), str(cohost.pk)]}),
            content_type="application/json",
            **_auth_headers(cohost),
        )
        assert response.status_code == 200
        assert event.cohost_invites.filter(user=creator, status=CoHostInviteStatus.PENDING).exists()


@pytest.mark.django_db
class TestStepDown:
    def test_creator_can_step_down_with_cohost_present(
        self, api_client, creator, cohost, event_with_accepted_cohost
    ):
        event, _invite = event_with_accepted_cohost
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohosts/{creator.pk}/",
            **_auth_headers(creator),
        )
        assert response.status_code == 200
        event.refresh_from_db()
        assert event.created_by_id == creator.pk  # audit field untouched
        assert not event.co_hosts.filter(pk=creator.pk).exists()
        assert event.co_hosts.filter(pk=cohost.pk).exists()

    def test_creator_cannot_step_down_as_last_host(self, api_client, creator, db):
        event_id = _create_event(api_client, creator, co_host_ids=[])
        response = api_client.delete(
            f"/api/community/events/{event_id}/cohosts/{creator.pk}/",
            **_auth_headers(creator),
        )
        assert response.status_code == 400
        event = Event.objects.get(id=event_id)
        assert event.co_hosts.filter(pk=creator.pk).exists()

    def test_invited_cohost_can_step_down(
        self, api_client, creator, cohost, event_with_accepted_cohost
    ):
        event, invite = event_with_accepted_cohost
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohosts/{cohost.pk}/",
            **_auth_headers(cohost),
        )
        assert response.status_code == 200
        assert not event.co_hosts.filter(pk=cohost.pk).exists()
        assert event.co_hosts.filter(pk=creator.pk).exists()
        # Row must close out, else _upsert_pending_invite refuses to re-invite them.
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.REMOVED

    def test_stranger_cannot_remove_a_host(
        self, api_client, stranger, cohost, event_with_accepted_cohost
    ):
        event, _invite = event_with_accepted_cohost
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohosts/{cohost.pk}/",
            **_auth_headers(stranger),
        )
        assert response.status_code == 403

    def test_can_step_down_on_past_event(self, api_client, creator, cohost, db):
        # Roster housekeeping stays available after the event — only the
        # hostless guard blocks a removal.
        event = Event.objects.create(
            title="Past Potluck",
            start_datetime=past_iso(days=2),
            end_datetime=past_iso(days=2),
            created_by=creator,
        )
        event.co_hosts.add(cohost)
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohosts/{creator.pk}/",
            **_auth_headers(creator),
        )
        assert response.status_code == 200
        assert not event.co_hosts.filter(pk=creator.pk).exists()

    def test_sole_host_cannot_step_down_on_past_event(self, api_client, creator, db):
        event = Event.objects.create(
            title="Past Solo Potluck",
            start_datetime=past_iso(days=2),
            end_datetime=past_iso(days=2),
            created_by=creator,
        )
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohosts/{creator.pk}/",
            **_auth_headers(creator),
        )
        assert response.status_code == 400
        assert "would_leave_hostless" in response.content.decode()
        assert event.co_hosts.filter(pk=creator.pk).exists()

    def test_remaining_cohost_can_uncancel_after_creator_steps_down(
        self, api_client, creator, cohost, event_with_accepted_cohost
    ):
        event, _invite = event_with_accepted_cohost
        api_client.delete(
            f"/api/community/events/{event.id}/cohosts/{creator.pk}/",
            **_auth_headers(creator),
        )
        event.status = EventStatus.CANCELLED
        event.save(update_fields=["status"])

        response = api_client.patch(
            f"/api/community/events/{event.id}/",
            data=json.dumps({"status": EventStatus.ACTIVE}),
            content_type="application/json",
            **_auth_headers(cohost),
        )
        assert response.status_code == 200
        assert response.json()["status"] == EventStatus.ACTIVE
