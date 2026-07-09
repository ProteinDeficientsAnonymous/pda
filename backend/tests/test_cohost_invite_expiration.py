"""Tests for scheduled co-host invite expiration (issue #382).

The `expire_stale_cohost_invites` management command sweeps PENDING invites on
past events to EXPIRED, replacing the old lazy-on-read expiration. Also covers
the accept/decline guard that blocks a stale invite before the daily sweep runs.
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
from django.core.management import call_command
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso


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


def _mark_event_past(event: Event) -> None:
    past = timezone.now() - timedelta(days=1)
    Event.objects.filter(pk=event.pk).update(
        start_datetime=past - timedelta(hours=1),
        end_datetime=past,
    )


@pytest.fixture
def creator(db) -> User:
    return _make_user("+12025550111", "Creator")


@pytest.fixture
def invitee(db) -> User:
    return _make_user("+12025550112", "Invitee")


@pytest.fixture
def event_with_pending_invite(db, api_client, creator, invitee) -> tuple[Event, EventCoHostInvite]:
    _create_event_via_api(api_client, creator, co_host_ids=[str(invitee.pk)])
    event = Event.objects.get(created_by=creator)
    invite = EventCoHostInvite.objects.get(event=event, user=invitee)
    return event, invite


@pytest.mark.django_db
class TestExpireStaleCohostInvitesCommand:
    def test_command_marks_stale_pending_invites_expired(self, event_with_pending_invite):
        event, invite = event_with_pending_invite
        _mark_event_past(event)

        call_command("expire_stale_cohost_invites")

        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.EXPIRED
        assert invite.decided_at is not None

    def test_command_leaves_future_event_invites_pending(self, event_with_pending_invite):
        _event, invite = event_with_pending_invite

        call_command("expire_stale_cohost_invites")

        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.PENDING

    def test_command_leaves_non_pending_invites_untouched(self, event_with_pending_invite):
        event, invite = event_with_pending_invite
        _mark_event_past(event)
        invite.status = CoHostInviteStatus.ACCEPTED
        invite.save(update_fields=["status"])

        call_command("expire_stale_cohost_invites")

        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.ACCEPTED

    def test_command_expires_invite_on_past_event_with_no_end(self, event_with_pending_invite):
        # end_datetime is nullable; is_past falls back to start_datetime. The
        # sweep must match so these invites don't strand forever.
        event, invite = event_with_pending_invite
        past = timezone.now() - timedelta(days=1)
        Event.objects.filter(pk=event.pk).update(start_datetime=past, end_datetime=None)

        call_command("expire_stale_cohost_invites")

        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.EXPIRED

    def test_command_leaves_tbd_event_invites_pending(self, event_with_pending_invite):
        event, invite = event_with_pending_invite
        past = timezone.now() - timedelta(days=1)
        Event.objects.filter(pk=event.pk).update(
            start_datetime=past, end_datetime=None, datetime_tbd=True
        )

        call_command("expire_stale_cohost_invites")

        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.PENDING

    def test_accepting_invite_on_past_event_is_rejected(
        self, api_client, invitee, event_with_pending_invite
    ):
        event, invite = event_with_pending_invite
        _mark_event_past(event)
        response = api_client.post(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/accept/",
            **_auth_headers(invitee),
        )
        assert response.status_code == 400
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.PENDING

    def test_declining_invite_on_past_event_is_rejected(
        self, api_client, invitee, event_with_pending_invite
    ):
        event, invite = event_with_pending_invite
        _mark_event_past(event)
        response = api_client.post(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/decline/",
            **_auth_headers(invitee),
        )
        assert response.status_code == 400
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.PENDING
