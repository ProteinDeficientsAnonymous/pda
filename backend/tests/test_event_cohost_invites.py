"""Tests for the co-host invite approval flow (issue #363).

Covers diff-on-create, diff-on-patch, accept/decline/rescind endpoints, lazy
expiration, notifications, EventOut visibility, and permission checks.
"""

import json
from datetime import timedelta

import pytest
from community.models import (
    CoHostInviteStatus,
    Event,
    EventCoHostInvite,
    EventStatus,
)
from django.utils import timezone
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


def _create_event_via_api(api_client, creator: User, **overrides) -> dict:
    payload = {
        "title": overrides.get("title", "Community Potluck"),
        "start_datetime": overrides.get("start_datetime", future_iso(days=30)),
        "end_datetime": overrides.get("end_datetime", future_iso(days=30, hours=2)),
        "status": overrides.get("status", EventStatus.ACTIVE),
        "co_host_ids": overrides.get("co_host_ids", []),
    }
    response = api_client.post(
        "/api/community/events/",
        data=json.dumps(payload),
        content_type="application/json",
        **_auth_headers(creator),
    )
    assert response.status_code == 201, response.content
    return response.json()


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def creator(db) -> User:
    return _make_user("+12025550111", "Creator")


@pytest.fixture
def invitee(db) -> User:
    return _make_user("+12025550112", "Invitee")


@pytest.fixture
def other_member(db) -> User:
    return _make_user("+12025550113", "Stranger")


@pytest.fixture
def event_with_pending_invite(db, api_client, creator, invitee) -> tuple[Event, EventCoHostInvite]:
    _create_event_via_api(api_client, creator, co_host_ids=[str(invitee.pk)])
    event = Event.objects.get(created_by=creator)
    invite = EventCoHostInvite.objects.get(event=event, user=invitee)
    return event, invite


# ─── Diff on create ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDiffOnCreate:
    def test_co_host_id_creates_pending_invite_not_direct_add(self, api_client, creator, invitee):
        data = _create_event_via_api(api_client, creator, co_host_ids=[str(invitee.pk)])
        event = Event.objects.get(id=data["id"])

        # The new flow: invite row in PENDING, NOT yet in event.co_hosts.
        assert event.co_hosts.filter(pk=invitee.pk).exists() is False
        invite = EventCoHostInvite.objects.get(event=event, user=invitee)
        assert invite.status == CoHostInviteStatus.PENDING
        assert invite.invited_by == creator

    def test_invitee_receives_cohost_invite_notification(self, api_client, creator, invitee):
        _create_event_via_api(api_client, creator, co_host_ids=[str(invitee.pk)])
        notif = Notification.objects.get(recipient=invitee)
        assert notif.notification_type == NotificationType.COHOST_INVITE
        assert "invited you to co-host" in notif.message

    def test_creator_self_invite_is_noop(self, api_client, creator):
        # Creator includes themselves in co_host_ids — no invite row, no notification.
        # They're already a host; making them a co-host is meaningless.
        data = _create_event_via_api(api_client, creator, co_host_ids=[str(creator.pk)])
        event = Event.objects.get(id=data["id"])
        assert EventCoHostInvite.objects.filter(event=event, user=creator).exists() is False
        assert Notification.objects.filter(recipient=creator).count() == 0


# ─── Diff on patch ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDiffOnPatch:
    def test_adding_co_host_via_patch_creates_pending_invite(self, api_client, creator, invitee):
        data = _create_event_via_api(api_client, creator, co_host_ids=[])
        event_id = data["id"]
        response = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"co_host_ids": [str(invitee.pk)]}),
            content_type="application/json",
            **_auth_headers(creator),
        )
        assert response.status_code == 200, response.content
        invite = EventCoHostInvite.objects.get(event_id=event_id, user=invitee)
        assert invite.status == CoHostInviteStatus.PENDING

    def test_removing_pending_co_host_rescinds_invite(self, api_client, creator, invitee):
        data = _create_event_via_api(api_client, creator, co_host_ids=[str(invitee.pk)])
        event_id = data["id"]
        # Invitee was just invited (pending). Now creator removes them.
        response = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"co_host_ids": []}),
            content_type="application/json",
            **_auth_headers(creator),
        )
        assert response.status_code == 200
        invite = EventCoHostInvite.objects.get(event_id=event_id, user=invitee)
        assert invite.status == CoHostInviteStatus.RESCINDED

    def test_removing_accepted_co_host_rescinds_and_drops_from_co_hosts(
        self, api_client, creator, invitee
    ):
        data = _create_event_via_api(api_client, creator, co_host_ids=[str(invitee.pk)])
        event_id = data["id"]
        invite = EventCoHostInvite.objects.get(event_id=event_id, user=invitee)
        # Simulate acceptance.
        api_client.post(
            f"/api/community/events/{event_id}/cohost-invites/{invite.id}/accept/",
            **_auth_headers(invitee),
        )
        event = Event.objects.get(id=event_id)
        assert event.co_hosts.filter(pk=invitee.pk).exists()
        # Now creator removes the co-host via patch.
        response = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"co_host_ids": []}),
            content_type="application/json",
            **_auth_headers(creator),
        )
        assert response.status_code == 200
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.RESCINDED
        assert event.co_hosts.filter(pk=invitee.pk).exists() is False

    def test_re_invite_after_decline_flips_row_back_to_pending(self, api_client, creator, invitee):
        data = _create_event_via_api(api_client, creator, co_host_ids=[str(invitee.pk)])
        event_id = data["id"]
        invite = EventCoHostInvite.objects.get(event_id=event_id, user=invitee)
        api_client.post(
            f"/api/community/events/{event_id}/cohost-invites/{invite.id}/decline/",
            **_auth_headers(invitee),
        )
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.DECLINED
        # Re-invite: same user_id back in the list.
        response = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"co_host_ids": [str(invitee.pk)]}),
            content_type="application/json",
            **_auth_headers(creator),
        )
        assert response.status_code == 200
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.PENDING
        assert invite.decided_at is None
        # And there's still only one invite row for (event, user).
        assert EventCoHostInvite.objects.filter(event_id=event_id, user=invitee).count() == 1


# ─── Accept ───────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAccept:
    def test_invitee_can_accept(self, api_client, creator, event_with_pending_invite, invitee):
        event, invite = event_with_pending_invite
        response = api_client.post(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/accept/",
            **_auth_headers(invitee),
        )
        assert response.status_code == 200
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.ACCEPTED
        assert invite.decided_at is not None
        assert event.co_hosts.filter(pk=invitee.pk).exists()

    def test_acceptance_notifies_inviter(
        self, api_client, creator, event_with_pending_invite, invitee
    ):
        event, invite = event_with_pending_invite
        Notification.objects.all().delete()  # ignore the invite notification
        api_client.post(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/accept/",
            **_auth_headers(invitee),
        )
        notif = Notification.objects.get(recipient=creator)
        assert notif.notification_type == NotificationType.COHOST_INVITE_ACCEPTED
        assert "accepted" in notif.message

    def test_non_invitee_cannot_accept(self, api_client, event_with_pending_invite, other_member):
        event, invite = event_with_pending_invite
        response = api_client.post(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/accept/",
            **_auth_headers(other_member),
        )
        assert response.status_code == 403

    def test_cannot_accept_non_pending_invite(self, api_client, event_with_pending_invite, invitee):
        event, invite = event_with_pending_invite
        invite.status = CoHostInviteStatus.DECLINED
        invite.save(update_fields=["status"])
        response = api_client.post(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/accept/",
            **_auth_headers(invitee),
        )
        assert response.status_code == 400


# ─── Decline ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDecline:
    def test_invitee_can_decline(self, api_client, event_with_pending_invite, invitee):
        event, invite = event_with_pending_invite
        response = api_client.post(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/decline/",
            **_auth_headers(invitee),
        )
        assert response.status_code == 200
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.DECLINED
        assert event.co_hosts.filter(pk=invitee.pk).exists() is False

    def test_decline_notifies_inviter(
        self, api_client, creator, event_with_pending_invite, invitee
    ):
        event, invite = event_with_pending_invite
        Notification.objects.all().delete()
        api_client.post(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/decline/",
            **_auth_headers(invitee),
        )
        notif = Notification.objects.get(recipient=creator)
        assert notif.notification_type == NotificationType.COHOST_INVITE_DECLINED


# ─── Rescind via DELETE ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRescind:
    def test_creator_can_rescind_pending_invite(
        self, api_client, creator, event_with_pending_invite
    ):
        event, invite = event_with_pending_invite
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/",
            **_auth_headers(creator),
        )
        assert response.status_code == 200
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.RESCINDED

    def test_outsider_cannot_rescind(self, api_client, event_with_pending_invite, other_member):
        event, invite = event_with_pending_invite
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/",
            **_auth_headers(other_member),
        )
        assert response.status_code == 403

    def test_cannot_rescind_already_resolved_invite(
        self, api_client, creator, event_with_pending_invite
    ):
        # DECLINED is a terminal state — neither host nor invitee can act on it.
        event, invite = event_with_pending_invite
        invite.status = CoHostInviteStatus.DECLINED
        invite.save(update_fields=["status"])
        response = api_client.delete(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/",
            **_auth_headers(creator),
        )
        assert response.status_code == 400


# ─── Lazy expiration ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestLazyExpire:
    def test_pending_invite_expires_when_event_is_past(
        self, api_client, creator, event_with_pending_invite
    ):
        event, invite = event_with_pending_invite
        past = timezone.now() - timedelta(days=1)
        Event.objects.filter(pk=event.pk).update(
            start_datetime=past - timedelta(hours=1),
            end_datetime=past,
        )
        # Simply reading the event detail triggers lazy expiration.
        response = api_client.get(
            f"/api/community/events/{event.id}/",
            **_auth_headers(creator),
        )
        assert response.status_code == 200
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.EXPIRED


# ─── EventOut visibility ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestEventOutVisibility:
    def test_creator_sees_pending_invites(self, api_client, creator, event_with_pending_invite):
        event, _invite = event_with_pending_invite
        response = api_client.get(
            f"/api/community/events/{event.id}/",
            **_auth_headers(creator),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["pending_cohost_invites"]) == 1

    def test_outsider_does_not_see_pending_invites(
        self, api_client, event_with_pending_invite, other_member
    ):
        event, _invite = event_with_pending_invite
        response = api_client.get(
            f"/api/community/events/{event.id}/",
            **_auth_headers(other_member),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pending_cohost_invites"] == []

    def test_invitee_sees_my_pending_invite_id(
        self, api_client, event_with_pending_invite, invitee
    ):
        event, invite = event_with_pending_invite
        response = api_client.get(
            f"/api/community/events/{event.id}/",
            **_auth_headers(invitee),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["my_pending_cohost_invite_id"] == str(invite.id)
        # Outsider visibility check: still no pending list for the invitee.
        assert data["pending_cohost_invites"] == []


# ─── Draft visibility for invitees ────────────────────────────────────────────


@pytest.mark.django_db
class TestDraftVisibility:
    """A pending cohost invitee must be able to see the draft they were invited
    to so they can find the accept/decline banner — otherwise the notification
    deep-link 404s."""

    def test_cohost_invitee_can_see_draft_event(self, api_client, creator, invitee):
        data = _create_event_via_api(
            api_client,
            creator,
            status=EventStatus.DRAFT,
            co_host_ids=[str(invitee.pk)],
        )
        event_id = data["id"]
        response = api_client.get(
            f"/api/community/events/{event_id}/",
            **_auth_headers(invitee),
        )
        assert response.status_code == 200
        body = response.json()
        invite = EventCoHostInvite.objects.get(event_id=event_id, user=invitee)
        assert body["my_pending_cohost_invite_id"] == str(invite.id)
        # The invitee is not yet a host, so they don't see the pending list.
        assert body["pending_cohost_invites"] == []

    def test_outsider_403s_on_draft(self, api_client, creator, invitee, other_member):
        data = _create_event_via_api(
            api_client,
            creator,
            status=EventStatus.DRAFT,
            co_host_ids=[str(invitee.pk)],
        )
        response = api_client.get(
            f"/api/community/events/{data['id']}/",
            **_auth_headers(other_member),
        )
        assert response.status_code == 403

    def test_cohost_invitee_can_accept_invite_to_a_draft(self, api_client, creator, invitee):
        data = _create_event_via_api(
            api_client,
            creator,
            status=EventStatus.DRAFT,
            co_host_ids=[str(invitee.pk)],
        )
        event_id = data["id"]
        invite = EventCoHostInvite.objects.get(event_id=event_id, user=invitee)
        response = api_client.post(
            f"/api/community/events/{event_id}/cohost-invites/{invite.id}/accept/",
            **_auth_headers(invitee),
        )
        assert response.status_code == 200
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.ACCEPTED
