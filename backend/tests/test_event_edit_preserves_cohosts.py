import json

import pytest
from community.models import Event, EventCoHostInvite, EventStatus
from community.models.choices import CoHostInviteStatus
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso


def _make_user(phone: str, name: str = "Member", email: str | None = "") -> User:
    return User.objects.create_user(
        phone_number=phone,
        password="testpass123",
        first_name=name,
        email=email,
    )


def _auth_headers(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def creator(db) -> User:
    return _make_user("+12025550201", "Creator", email="creator@example.com")


@pytest.fixture
def cohost(db) -> User:
    return _make_user("+12025550202", "CoHost", email="cohost@example.com")


@pytest.mark.django_db
class TestEventEditPreservesCohosts:
    def test_patch_without_cohost_ids_preserves_accepted_cohosts(self, api_client, creator, cohost):
        event_id = Event.objects.create(
            title="Potluck",
            start_datetime=future_iso(days=30),
            end_datetime=future_iso(days=30, hours=2),
            status=EventStatus.ACTIVE,
            created_by=creator,
        ).id

        event = Event.objects.get(id=event_id)
        invite = EventCoHostInvite.objects.create(
            event=event,
            user=cohost,
            invited_by=creator,
            status=CoHostInviteStatus.ACCEPTED,
        )
        event.co_hosts.add(cohost)

        response = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"title": "Updated Potluck"}),
            content_type="application/json",
            **_auth_headers(creator),
        )

        assert response.status_code == 200, response.content
        event.refresh_from_db()
        assert event.co_hosts.filter(pk=cohost.pk).exists()
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.ACCEPTED

    def test_patch_without_cohost_ids_preserves_pending_invites(self, api_client, creator, cohost):
        event_id = Event.objects.create(
            title="Potluck",
            start_datetime=future_iso(days=30),
            end_datetime=future_iso(days=30, hours=2),
            status=EventStatus.ACTIVE,
            created_by=creator,
        ).id

        event = Event.objects.get(id=event_id)
        invite = EventCoHostInvite.objects.create(
            event=event,
            user=cohost,
            invited_by=creator,
            status=CoHostInviteStatus.PENDING,
        )

        response = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"title": "Updated Potluck"}),
            content_type="application/json",
            **_auth_headers(creator),
        )

        assert response.status_code == 200, response.content
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.PENDING

    def test_patch_with_empty_cohost_ids_removes_accepted_cohosts(
        self, api_client, creator, cohost
    ):
        event_id = Event.objects.create(
            title="Potluck",
            start_datetime=future_iso(days=30),
            end_datetime=future_iso(days=30, hours=2),
            status=EventStatus.ACTIVE,
            created_by=creator,
        ).id

        event = Event.objects.get(id=event_id)
        invite = EventCoHostInvite.objects.create(
            event=event,
            user=cohost,
            invited_by=creator,
            status=CoHostInviteStatus.ACCEPTED,
        )
        event.co_hosts.add(cohost)

        response = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"title": "Updated Potluck", "co_host_ids": []}),
            content_type="application/json",
            **_auth_headers(creator),
        )

        assert response.status_code == 200, response.content
        event.refresh_from_db()
        assert not event.co_hosts.filter(pk=cohost.pk).exists()
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.RESCINDED
