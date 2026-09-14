from datetime import timedelta

import pytest
from community._validation import Code
from community.models import (
    Event,
    EventStatus,
    EventType,
    JoinRequest,
    JoinRequestStatus,
    PageVisibility,
)
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests._asserts import assert_error_code


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


def _event(title, event_type, visibility=PageVisibility.PUBLIC, *, host):
    return Event.objects.create(
        title=title,
        start_datetime=timezone.now() + timedelta(days=3),
        end_datetime=timezone.now() + timedelta(days=3, hours=2),
        location="123 Sprout Lane",
        whatsapp_link="https://chat.whatsapp.com/abc",
        event_type=event_type,
        visibility=visibility,
        status=EventStatus.ACTIVE,
        rsvp_enabled=True,
        created_by=host,
    )


@pytest.fixture
def host(db):
    return User.objects.create_user(phone_number="+12025557100", first_name="Host")


@pytest.fixture
def tentative_user(db):
    user = User.objects.create(
        phone_number="+16505551234",
        first_name="Sprout",
        email="sprout@example.com",
        is_member=False,
        guidelines_consent_at=timezone.now(),
    )
    JoinRequest.objects.create(
        first_name="Sprout",
        phone_number=user.phone_number,
        email=user.email,
        user=user,
        status=JoinRequestStatus.TENTATIVE,
    )
    return user


@pytest.mark.django_db
class TestCheckPhoneTentative:
    def test_tentative_applicant_can_reach_the_login_step(self, api_client, tentative_user):
        response = api_client.post(
            "/api/community/check-phone/",
            {"phone_number": tentative_user.phone_number},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "member"

    def test_archived_tentative_applicant_stays_unknown(self, api_client, tentative_user):
        tentative_user.archived_at = timezone.now()
        tentative_user.save(update_fields=["archived_at"])
        response = api_client.post(
            "/api/community/check-phone/",
            {"phone_number": tentative_user.phone_number},
            content_type="application/json",
        )
        assert response.json()["status"] == "unknown"

    def test_plain_non_member_without_tentative_request_stays_unknown(self, api_client, db):
        User.objects.create(phone_number="+16505559999", first_name="Guest", is_member=False)
        response = api_client.post(
            "/api/community/check-phone/",
            {"phone_number": "+16505559999"},
            content_type="application/json",
        )
        assert response.json()["status"] == "unknown"


@pytest.mark.django_db
class TestTentativeEventAccess:
    def test_official_event_detail_unlocks_member_fields(self, api_client, tentative_user, host):
        event = _event("Official", EventType.OFFICIAL, host=host)
        response = api_client.get(f"/api/community/events/{event.id}/", **_auth(tentative_user))
        assert response.status_code == 200
        assert response.json()["whatsapp_link"] == "https://chat.whatsapp.com/abc"

    def test_club_event_detail_unlocks_member_fields(self, api_client, tentative_user, host):
        event = _event("Club", EventType.CLUB, host=host)
        response = api_client.get(f"/api/community/events/{event.id}/", **_auth(tentative_user))
        assert response.status_code == 200
        assert response.json()["whatsapp_link"] == "https://chat.whatsapp.com/abc"

    def test_members_only_club_event_is_visible(self, api_client, tentative_user, host):
        event = _event("Club", EventType.CLUB, PageVisibility.MEMBERS_ONLY, host=host)
        response = api_client.get(f"/api/community/events/{event.id}/", **_auth(tentative_user))
        assert response.status_code == 200

    def test_public_community_event_hides_member_fields(self, api_client, tentative_user, host):
        event = _event("Potluck", EventType.COMMUNITY, host=host)
        response = api_client.get(f"/api/community/events/{event.id}/", **_auth(tentative_user))
        assert response.status_code == 200
        assert response.json()["whatsapp_link"] == ""

    def test_members_only_community_event_is_hidden(self, api_client, tentative_user, host):
        event = _event("Private", EventType.COMMUNITY, PageVisibility.MEMBERS_ONLY, host=host)
        response = api_client.get(f"/api/community/events/{event.id}/", **_auth(tentative_user))
        assert response.status_code == 404

    def test_list_includes_official_club_and_public_community(
        self, api_client, tentative_user, host
    ):
        _event("Official", EventType.OFFICIAL, host=host)
        _event("Club", EventType.CLUB, PageVisibility.MEMBERS_ONLY, host=host)
        _event("Potluck", EventType.COMMUNITY, host=host)
        _event("Private", EventType.COMMUNITY, PageVisibility.MEMBERS_ONLY, host=host)
        response = api_client.get("/api/community/events/", **_auth(tentative_user))
        assert response.status_code == 200
        titles = {e["title"] for e in response.json()}
        assert titles == {"Official", "Club", "Potluck"}

    def test_list_gates_member_fields_per_event_type(self, api_client, tentative_user, host):
        _event("Official", EventType.OFFICIAL, host=host)
        _event("Potluck", EventType.COMMUNITY, host=host)
        response = api_client.get("/api/community/events/", **_auth(tentative_user))
        by_title = {e["title"]: e for e in response.json()}
        assert by_title["Official"]["whatsapp_link"] == "https://chat.whatsapp.com/abc"
        assert by_title["Potluck"]["whatsapp_link"] == ""

    def test_can_rsvp_to_official_event(self, api_client, tentative_user, host):
        event = _event("Official", EventType.OFFICIAL, host=host)
        response = api_client.post(
            f"/api/community/events/{event.id}/rsvp/",
            {"status": "attending"},
            content_type="application/json",
            **_auth(tentative_user),
        )
        assert response.status_code == 200

    def test_cannot_rsvp_to_community_event(self, api_client, tentative_user, host):
        event = _event("Potluck", EventType.COMMUNITY, host=host)
        response = api_client.post(
            f"/api/community/events/{event.id}/rsvp/",
            {"status": "attending"},
            content_type="application/json",
            **_auth(tentative_user),
        )
        assert response.status_code == 403

    def test_cannot_create_an_event(self, api_client, tentative_user):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "Sprout's Potluck",
                "start_datetime": (timezone.now() + timedelta(days=5)).isoformat(),
                "event_type": EventType.COMMUNITY,
                "visibility": PageVisibility.PUBLIC,
                "status": EventStatus.ACTIVE,
            },
            content_type="application/json",
            **_auth(tentative_user),
        )
        assert response.status_code == 403
        assert not Event.objects.filter(title="Sprout's Potluck").exists()

    def test_cannot_create_a_draft_event(self, api_client, tentative_user):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "Sprout's Draft",
                "event_type": EventType.COMMUNITY,
                "visibility": PageVisibility.PUBLIC,
                "status": EventStatus.DRAFT,
            },
            content_type="application/json",
            **_auth(tentative_user),
        )
        assert response.status_code == 403

    def test_member_can_still_create_an_event(self, api_client, test_user):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "Member Potluck",
                "start_datetime": (timezone.now() + timedelta(days=5)).isoformat(),
                "event_type": EventType.COMMUNITY,
                "visibility": PageVisibility.PUBLIC,
                "status": EventStatus.ACTIVE,
            },
            content_type="application/json",
            **_auth(test_user),
        )
        assert response.status_code == 201

    def test_member_still_sees_everything(self, api_client, test_user, host):
        _event("Official", EventType.OFFICIAL, host=host)
        _event("Private", EventType.COMMUNITY, PageVisibility.MEMBERS_ONLY, host=host)
        response = api_client.get("/api/community/events/", **_auth(test_user))
        titles = {e["title"] for e in response.json()}
        assert titles == {"Official", "Private"}


@pytest.mark.django_db
class TestTentativeDirectoryAccess:
    def test_directory_is_blocked_for_non_members(self, api_client, tentative_user, test_user):
        response = api_client.get("/api/auth/users/directory/", **_auth(tentative_user))
        assert response.status_code == 403
        assert_error_code(response, Code.Perm.DENIED)

    def test_member_profile_is_blocked_for_non_members(self, api_client, tentative_user, test_user):
        response = api_client.get(
            f"/api/auth/users/{test_user.id}/profile/", **_auth(tentative_user)
        )
        assert response.status_code == 403

    def test_directory_still_works_for_members(self, api_client, test_user):
        response = api_client.get("/api/auth/users/directory/", **_auth(test_user))
        assert response.status_code == 200
