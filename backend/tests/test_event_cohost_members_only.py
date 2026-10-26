import json

import pytest
from community._validation import Code
from community.models import Event, EventCoHostInvite, EventStatus
from community.models.choices import CoHostInviteStatus
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests._asserts import assert_error_code
from tests.conftest import future_iso


def _auth_headers(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def creator(db) -> User:
    return User.objects.create_user(phone_number="+12025550601", first_name="Creator")


@pytest.fixture
def member(db) -> User:
    return User.objects.create_user(phone_number="+12025550602", first_name="Member")


@pytest.fixture
def tentative(db) -> User:
    return User.objects.create_user(
        phone_number="+12025550603", first_name="Tentative", is_member=False
    )


@pytest.fixture
def event(creator) -> Event:
    event = Event.objects.create(
        title="Potluck",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        status=EventStatus.ACTIVE,
        created_by=creator,
    )
    event.co_hosts.add(creator)
    return event


def _event_payload(co_host_ids: list[str]) -> dict:
    return {
        "title": "Potluck",
        "start_datetime": future_iso(days=30),
        "end_datetime": future_iso(days=30, hours=2),
        "status": EventStatus.ACTIVE,
        "co_host_ids": co_host_ids,
    }


@pytest.mark.django_db
class TestCohostsMustBeMembers:
    def test_add_cohosts_rejects_tentative_member(self, api_client, event, creator, tentative):
        response = api_client.post(
            f"/api/community/events/{event.id}/cohost-invites/",
            data=json.dumps({"user_ids": [str(tentative.pk)]}),
            content_type="application/json",
            **_auth_headers(creator),
        )
        assert response.status_code == 400
        assert_error_code(response, Code.CoHostInvite.NOT_MEMBER)
        assert not EventCoHostInvite.objects.filter(event=event, user=tentative).exists()

    def test_patch_rejects_tentative_member(self, api_client, event, creator, member, tentative):
        response = api_client.patch(
            f"/api/community/events/{event.id}/",
            data=json.dumps({"co_host_ids": [str(member.pk), str(tentative.pk)]}),
            content_type="application/json",
            **_auth_headers(creator),
        )
        assert response.status_code == 400
        assert_error_code(response, Code.CoHostInvite.NOT_MEMBER)
        assert not EventCoHostInvite.objects.filter(event=event).exists()

    def test_create_rejects_tentative_member_without_creating_event(
        self, api_client, creator, tentative
    ):
        response = api_client.post(
            "/api/community/events/",
            data=json.dumps(_event_payload([str(tentative.pk)])),
            content_type="application/json",
            **_auth_headers(creator),
        )
        assert response.status_code == 400
        assert_error_code(response, Code.CoHostInvite.NOT_MEMBER)
        assert not Event.objects.filter(created_by=creator).exists()

    def test_create_still_invites_members(self, api_client, creator, member):
        response = api_client.post(
            "/api/community/events/",
            data=json.dumps(_event_payload([str(member.pk)])),
            content_type="application/json",
            **_auth_headers(creator),
        )
        assert response.status_code == 201, response.content
        invite = EventCoHostInvite.objects.get(event_id=response.json()["id"], user=member)
        assert invite.status == CoHostInviteStatus.PENDING

    def test_patch_resending_existing_tentative_invite_is_allowed(
        self, api_client, event, creator, tentative
    ):
        # Invites that predate the rule stay untouched; only new or revived ones are blocked.
        EventCoHostInvite.objects.create(
            event=event, user=tentative, invited_by=creator, status=CoHostInviteStatus.PENDING
        )
        response = api_client.patch(
            f"/api/community/events/{event.id}/",
            data=json.dumps({"co_host_ids": [str(tentative.pk)]}),
            content_type="application/json",
            **_auth_headers(creator),
        )
        assert response.status_code == 200, response.content

    def test_tentative_member_cannot_accept_existing_invite(
        self, api_client, event, creator, tentative
    ):
        invite = EventCoHostInvite.objects.create(
            event=event, user=tentative, invited_by=creator, status=CoHostInviteStatus.PENDING
        )
        response = api_client.post(
            f"/api/community/events/{event.id}/cohost-invites/{invite.id}/accept/",
            **_auth_headers(tentative),
        )
        assert response.status_code == 403
        assert_error_code(response, Code.CoHostInvite.NOT_MEMBER)
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.PENDING
        assert not event.co_hosts.filter(pk=tentative.pk).exists()
