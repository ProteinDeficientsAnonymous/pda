"""Tests for event public/auth visibility and invite-only access control."""

import pytest
from community.models import Event
from users.permissions import PermissionKey
from users.roles import Role


@pytest.fixture
def official_event_user(db):
    """A user with tag_official_event permission."""
    from users.models import User

    user = User.objects.create_user(
        phone_number="+14155559999",
        password="officialpass123",
        display_name="Official Tagger",
    )
    role = Role.objects.create(
        name="official_tagger", permissions=[PermissionKey.TAG_OFFICIAL_EVENT]
    )
    user.roles.add(role)
    return user


@pytest.fixture
def official_event_headers(official_event_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(official_event_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def manage_events_user(db):
    """A non-superuser with only manage_events permission."""
    from users.models import User

    user = User.objects.create_user(
        phone_number="+14155551234",
        password="eventmanagerpass123",
        display_name="Event Manager",
    )
    role = Role.objects.create(name="event_manager", permissions=[PermissionKey.MANAGE_EVENTS])
    user.roles.add(role)
    return user


@pytest.fixture
def manage_events_headers(manage_events_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(manage_events_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestEventVisibility:
    def test_events_public(self, api_client):
        response = api_client.get("/api/community/events/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_events_authenticated(self, api_client, auth_headers):
        response = api_client.get("/api/community/events/", **auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_events_strips_private_fields_for_anonymous(self, api_client, auth_headers, test_user):
        from community.models import Event
        from django.utils import timezone

        event = Event.objects.create(
            title="Test",
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            location="",
            whatsapp_link="https://chat.whatsapp.com/abc",
            partiful_link="https://partiful.com/e/abc",
            rsvp_enabled=False,
            created_by=test_user,
        )
        anon_res = api_client.get("/api/community/events/")
        authed_res = api_client.get("/api/community/events/", **auth_headers)

        anon_event = next(e for e in anon_res.json() if e["id"] == str(event.id))
        authed_event = next(e for e in authed_res.json() if e["id"] == str(event.id))

        assert anon_event["whatsapp_link"] == ""
        assert anon_event["partiful_link"] == ""
        assert authed_event["whatsapp_link"] == "https://chat.whatsapp.com/abc"
        assert authed_event["partiful_link"] == "https://partiful.com/e/abc"


@pytest.mark.django_db
class TestInviteOnlyVisibility:
    """Tests for invite_only PageVisibility — events hidden from non-invited members."""

    def _make_invite_only_event(self, creator, co_host=None, invited_user=None):
        from community.models import PageVisibility
        from django.utils import timezone

        event = Event.objects.create(
            title="Secret Gathering",
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            visibility=PageVisibility.INVITE_ONLY,
            created_by=creator,
        )
        if co_host:
            event.co_hosts.add(co_host)
        if invited_user:
            event.invited_users.add(invited_user)
        return event

    def _make_user(self, phone, name):
        from users.models import User

        return User.objects.create_user(phone_number=phone, password="pass123", display_name=name)

    def _auth_headers(self, user):
        from ninja_jwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]

    def test_list_hides_invite_only_from_non_invited(self, api_client, test_user):
        creator = self._make_user("+12025550201", "Creator")
        event = self._make_invite_only_event(creator)
        response = api_client.get("/api/community/events/", **self._auth_headers(test_user))
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(event.id) not in ids

    def test_list_hides_invite_only_from_anonymous(self, api_client, test_user):
        creator = self._make_user("+12025550202", "Creator2")
        event = self._make_invite_only_event(creator)
        response = api_client.get("/api/community/events/")
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(event.id) not in ids

    def test_list_shows_invite_only_to_creator(self, api_client, test_user):
        event = self._make_invite_only_event(test_user)
        response = api_client.get("/api/community/events/", **self._auth_headers(test_user))
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(event.id) in ids

    def test_list_shows_invite_only_to_co_host(self, api_client, test_user):
        creator = self._make_user("+12025550203", "Creator3")
        event = self._make_invite_only_event(creator, co_host=test_user)
        response = api_client.get("/api/community/events/", **self._auth_headers(test_user))
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(event.id) in ids

    def test_list_shows_invite_only_to_invited_user(self, api_client, test_user):
        creator = self._make_user("+12025550204", "Creator4")
        event = self._make_invite_only_event(creator, invited_user=test_user)
        response = api_client.get("/api/community/events/", **self._auth_headers(test_user))
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(event.id) in ids

    def test_list_shows_invite_only_to_manage_events_user(
        self, api_client, manage_events_user, manage_events_headers
    ):
        creator = self._make_user("+12025550205", "Creator5")
        event = self._make_invite_only_event(creator)
        response = api_client.get("/api/community/events/", **manage_events_headers)
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(event.id) in ids

    def test_get_event_404_for_non_invited(self, api_client, test_user):
        creator = self._make_user("+12025550206", "Creator6")
        event = self._make_invite_only_event(creator)
        response = api_client.get(
            f"/api/community/events/{event.id}/", **self._auth_headers(test_user)
        )
        assert response.status_code == 404

    def test_get_event_404_for_anonymous(self, api_client, test_user):
        creator = self._make_user("+12025550207", "Creator7")
        event = self._make_invite_only_event(creator)
        response = api_client.get(f"/api/community/events/{event.id}/")
        assert response.status_code == 404

    def test_get_event_200_for_invited_user(self, api_client, test_user):
        creator = self._make_user("+12025550208", "Creator8")
        event = self._make_invite_only_event(creator, invited_user=test_user)
        response = api_client.get(
            f"/api/community/events/{event.id}/", **self._auth_headers(test_user)
        )
        assert response.status_code == 200

    def test_get_event_200_for_creator(self, api_client, test_user):
        event = self._make_invite_only_event(test_user)
        response = api_client.get(
            f"/api/community/events/{event.id}/", **self._auth_headers(test_user)
        )
        assert response.status_code == 200

    def test_get_event_200_for_co_host(self, api_client, test_user):
        creator = self._make_user("+12025550209", "Creator9")
        event = self._make_invite_only_event(creator, co_host=test_user)
        response = api_client.get(
            f"/api/community/events/{event.id}/", **self._auth_headers(test_user)
        )
        assert response.status_code == 200

    def test_invited_list_visible_to_invited_user(self, api_client, test_user):
        creator = self._make_user("+12025550210", "Creator10")
        event = self._make_invite_only_event(creator, invited_user=test_user)
        response = api_client.get(
            f"/api/community/events/{event.id}/", **self._auth_headers(test_user)
        )
        assert response.status_code == 200
        assert len(response.json()["invited_user_ids"]) == 1

    def test_invited_list_hidden_for_regular_public_event(self, api_client, test_user):
        from community.models import PageVisibility
        from django.utils import timezone

        creator = self._make_user("+12025550211", "Creator11")
        event = Event.objects.create(
            title="Public Event",
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            visibility=PageVisibility.PUBLIC,
            created_by=creator,
        )
        event.invited_users.add(test_user)
        response = api_client.get(
            f"/api/community/events/{event.id}/", **self._auth_headers(test_user)
        )
        assert response.status_code == 200
        assert response.json()["invited_user_ids"] == []

    def test_rsvp_blocked_for_non_invited(self, api_client, test_user):
        creator = self._make_user("+12025550212", "Creator12")
        event = self._make_invite_only_event(creator)
        event.rsvp_enabled = True
        event.save(update_fields=["rsvp_enabled"])
        response = api_client.post(
            f"/api/community/events/{event.id}/rsvp/",
            {"status": "attending"},
            content_type="application/json",
            **self._auth_headers(test_user),
        )
        assert response.status_code == 404

    def test_rsvp_allowed_for_invited_user(self, api_client, test_user):
        creator = self._make_user("+12025550213", "Creator13")
        event = self._make_invite_only_event(creator, invited_user=test_user)
        event.rsvp_enabled = True
        event.save(update_fields=["rsvp_enabled"])
        response = api_client.post(
            f"/api/community/events/{event.id}/rsvp/",
            {"status": "attending"},
            content_type="application/json",
            **self._auth_headers(test_user),
        )
        assert response.status_code == 200

    def test_calendar_feed_excludes_invite_only_for_non_invited(self, api_client):
        import secrets

        from community.models import PageVisibility
        from django.utils import timezone
        from users.models import User

        owner = User.objects.create_user(
            phone_number="+12025550214", password="pass123", display_name="Feed Owner"
        )
        owner.calendar_token = secrets.token_urlsafe(32)
        owner.save(update_fields=["calendar_token"])

        creator = self._make_user("+12025550215", "Creator15")
        Event.objects.create(
            title="Private Party",
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            visibility=PageVisibility.INVITE_ONLY,
            created_by=creator,
        )

        response = api_client.get(f"/api/community/calendar/feed/?token={owner.calendar_token}")
        assert response.status_code == 200
        assert b"Private Party" not in response.content

    def test_calendar_feed_includes_invite_only_for_invited(self, api_client):
        import secrets

        from community.models import PageVisibility
        from django.utils import timezone
        from users.models import User

        owner = User.objects.create_user(
            phone_number="+12025550216", password="pass123", display_name="Invited Owner"
        )
        owner.calendar_token = secrets.token_urlsafe(32)
        owner.save(update_fields=["calendar_token"])

        creator = self._make_user("+12025550217", "Creator17")
        event = Event.objects.create(
            title="Exclusive Hangout",
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            visibility=PageVisibility.INVITE_ONLY,
            created_by=creator,
        )
        event.invited_users.add(owner)

        response = api_client.get(f"/api/community/calendar/feed/?token={owner.calendar_token}")
        assert response.status_code == 200
        assert b"Exclusive Hangout" in response.content


@pytest.mark.django_db
class TestOfficialEventVisibility:
    """Official events are public — visible to anonymous users."""

    def _make_official_event(self, creator):
        from community.models import EventType
        from django.utils import timezone

        return Event.objects.create(
            title="Official Meetup",
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            event_type=EventType.OFFICIAL,
            created_by=creator,
        )

    def test_list_shows_official_event_to_anonymous(self, api_client, test_user):
        event = self._make_official_event(test_user)
        response = api_client.get("/api/community/events/")
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(event.id) in ids

    def test_get_official_event_visible_to_anonymous(self, api_client, test_user):
        event = self._make_official_event(test_user)
        response = api_client.get(f"/api/community/events/{event.id}/")
        assert response.status_code == 200
        assert response.json()["event_type"] == "official"

    def test_create_official_event_rejects_non_public_visibility(
        self, api_client, official_event_headers
    ):
        from django.utils import timezone

        payload = {
            "title": "Official Event",
            "description": "",
            "start_datetime": timezone.now().isoformat(),
            "event_type": "official",
            "visibility": "members_only",
        }
        response = api_client.post(
            "/api/community/events/",
            payload,
            content_type="application/json",
            **official_event_headers,
        )
        assert response.status_code == 400

    def test_update_to_official_rejects_non_public_visibility(
        self, api_client, official_event_user, official_event_headers
    ):
        from community.models import PageVisibility
        from django.utils import timezone

        event = Event.objects.create(
            title="Community Event",
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            visibility=PageVisibility.MEMBERS_ONLY,
            created_by=official_event_user,
        )
        response = api_client.patch(
            f"/api/community/events/{event.id}/",
            {"event_type": "official"},
            content_type="application/json",
            **official_event_headers,
        )
        assert response.status_code == 400

    def test_update_official_event_rejects_visibility_change(
        self, api_client, official_event_user, official_event_headers
    ):
        event = self._make_official_event(official_event_user)
        response = api_client.patch(
            f"/api/community/events/{event.id}/",
            {"visibility": "members_only"},
            content_type="application/json",
            **official_event_headers,
        )
        assert response.status_code == 400
