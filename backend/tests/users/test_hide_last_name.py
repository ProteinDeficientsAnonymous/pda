import pytest
from community.models import (
    Event,
    EventComment,
    EventPoll,
    EventRSVP,
    PollAvailability,
    PollOption,
    PollVote,
    RSVPStatus,
)
from ninja_jwt.tokens import RefreshToken
from tests.conftest import future_iso
from users.models import User
from users.roles import Role


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        phone_number="+12025550501",
        password="adminpass123",
        first_name="Admin",
        last_name="Adminson",
    )
    admin_role = Role.objects.get(name="admin", is_default=True)
    user.roles.add(admin_role)
    return user


@pytest.fixture
def admin_headers(admin_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(admin_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def hidden_user(db):
    return User.objects.create_user(
        phone_number="+12025550502",
        password="hiddenpass123",
        first_name="Hidden",
        last_name="Lastname",
        hide_last_name=True,
    )


@pytest.mark.django_db
class TestDirectoryHidesLastName:
    def test_non_admin_sees_first_name_only(self, api_client, auth_headers, hidden_user):
        response = api_client.get("/api/auth/users/directory/", **auth_headers)
        assert response.status_code == 200
        entry = next(u for u in response.json() if u["id"] == str(hidden_user.pk))
        assert entry["last_name"] == ""
        assert entry["full_name"] == "Hidden"

    def test_admin_sees_full_name(self, api_client, admin_headers, hidden_user):
        response = api_client.get("/api/auth/users/directory/", **admin_headers)
        assert response.status_code == 200
        entry = next(u for u in response.json() if u["id"] == str(hidden_user.pk))
        assert entry["last_name"] == "Lastname"
        assert entry["full_name"] == "Hidden Lastname"


@pytest.mark.django_db
class TestProfileHidesLastName:
    def test_non_admin_sees_first_name_only(self, api_client, auth_headers, hidden_user):
        response = api_client.get(f"/api/auth/users/{hidden_user.pk}/profile/", **auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["last_name"] == ""
        assert body["full_name"] == "Hidden"

    def test_admin_sees_full_name(self, api_client, admin_headers, hidden_user):
        response = api_client.get(f"/api/auth/users/{hidden_user.pk}/profile/", **admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["last_name"] == "Lastname"
        assert body["full_name"] == "Hidden Lastname"

    def test_self_sees_own_full_name(self, api_client, hidden_user):
        from ninja_jwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(hidden_user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
        response = api_client.get(f"/api/auth/users/{hidden_user.pk}/profile/", **headers)
        assert response.status_code == 200
        body = response.json()
        assert body["last_name"] == "Lastname"
        assert body["full_name"] == "Hidden Lastname"


@pytest.mark.django_db
class TestSearchHidesLastName:
    def test_non_admin_search_by_hidden_last_name_no_match(
        self, api_client, auth_headers, hidden_user
    ):
        response = api_client.get("/api/auth/users/search/?q=Lastname", **auth_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(hidden_user.pk) not in ids

    def test_non_admin_search_by_first_name_matches_but_omits_last_name(
        self, api_client, auth_headers, hidden_user
    ):
        response = api_client.get("/api/auth/users/search/?q=Hidden", **auth_headers)
        assert response.status_code == 200
        entry = next(u for u in response.json() if u["id"] == str(hidden_user.pk))
        assert entry["last_name"] == ""
        assert entry["full_name"] == "Hidden"

    def test_admin_search_by_last_name_matches_with_full_name(
        self, api_client, admin_headers, hidden_user
    ):
        response = api_client.get("/api/auth/users/search/?q=Lastname", **admin_headers)
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert str(hidden_user.pk) in ids
        entry = next(u for u in response.json() if u["id"] == str(hidden_user.pk))
        assert entry["last_name"] == "Lastname"
        assert entry["full_name"] == "Hidden Lastname"


@pytest.mark.django_db
class TestMeHideLastName:
    def test_me_always_shows_own_last_name(self, api_client, hidden_user):
        from ninja_jwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(hidden_user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
        response = api_client.get("/api/auth/me/", **headers)
        assert response.status_code == 200
        body = response.json()
        assert body["last_name"] == "Lastname"
        assert body["full_name"] == "Hidden Lastname"
        assert body["hide_last_name"] is True

    def test_patch_me_persists_hide_last_name(self, api_client, auth_headers, test_user):
        response = api_client.patch(
            "/api/auth/me/",
            {"hide_last_name": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["hide_last_name"] is True
        test_user.refresh_from_db()
        assert test_user.hide_last_name is True


@pytest.fixture
def hidden_headers(hidden_user):
    refresh = RefreshToken.for_user(hidden_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestEventGuestListHidesLastName:
    def test_non_admin_sees_first_name_only(self, api_client, auth_headers, hidden_user):
        event = Event.objects.create(
            title="Guest List Event",
            start_datetime=future_iso(days=10),
            rsvp_enabled=True,
        )
        EventRSVP.objects.create(event=event, user=hidden_user, status=RSVPStatus.ATTENDING)
        response = api_client.get(f"/api/community/events/{event.id}/", **auth_headers)
        assert response.status_code == 200
        guest = next(g for g in response.json()["guests"] if g["user_id"] == str(hidden_user.pk))
        assert guest["name"] == "Hidden"

    def test_admin_sees_full_name(self, api_client, admin_headers, hidden_user):
        event = Event.objects.create(
            title="Guest List Event Admin",
            start_datetime=future_iso(days=10),
            rsvp_enabled=True,
        )
        EventRSVP.objects.create(event=event, user=hidden_user, status=RSVPStatus.ATTENDING)
        response = api_client.get(f"/api/community/events/{event.id}/", **admin_headers)
        assert response.status_code == 200
        guest = next(g for g in response.json()["guests"] if g["user_id"] == str(hidden_user.pk))
        assert guest["name"] == "Hidden Lastname"


@pytest.mark.django_db
class TestPollVotersHideLastName:
    def test_non_admin_sees_first_name_only(self, api_client, auth_headers, hidden_user):
        event = Event.objects.create(title="Poll Event", start_datetime=future_iso(days=10))
        poll = EventPoll.objects.create(event=event, created_by=hidden_user)
        option = PollOption.objects.create(poll=poll, datetime=future_iso(days=20), display_order=0)
        PollVote.objects.create(option=option, user=hidden_user, availability=PollAvailability.YES)
        response = api_client.get(f"/api/community/events/{event.id}/poll/", **auth_headers)
        assert response.status_code == 200
        voter = response.json()["options"][0]["yes_voters"][0]
        assert voter["name"] == "Hidden"

    def test_admin_sees_full_name(self, api_client, admin_headers, hidden_user):
        event = Event.objects.create(title="Poll Event Admin", start_datetime=future_iso(days=10))
        poll = EventPoll.objects.create(event=event, created_by=hidden_user)
        option = PollOption.objects.create(poll=poll, datetime=future_iso(days=20), display_order=0)
        PollVote.objects.create(option=option, user=hidden_user, availability=PollAvailability.YES)
        response = api_client.get(f"/api/community/events/{event.id}/poll/", **admin_headers)
        assert response.status_code == 200
        voter = response.json()["options"][0]["yes_voters"][0]
        assert voter["name"] == "Hidden Lastname"


@pytest.mark.django_db
class TestCommentAuthorHidesLastName:
    def test_non_admin_sees_first_name_only(self, api_client, auth_headers, hidden_user):
        event = Event.objects.create(
            title="Comment Event", start_datetime=future_iso(days=10), created_by=hidden_user
        )
        EventRSVP.objects.create(event=event, user=hidden_user, status=RSVPStatus.ATTENDING)
        EventComment.objects.create(event=event, author=hidden_user, body="hello")
        response = api_client.get(f"/api/community/events/{event.id}/comments/", **auth_headers)
        assert response.status_code == 200
        comment = response.json()["items"][0]
        assert comment["author_display_name"] == "Hidden"

    def test_admin_sees_full_name(self, api_client, admin_headers, hidden_user):
        event = Event.objects.create(
            title="Comment Event Admin",
            start_datetime=future_iso(days=10),
            created_by=hidden_user,
        )
        EventRSVP.objects.create(event=event, user=hidden_user, status=RSVPStatus.ATTENDING)
        EventComment.objects.create(event=event, author=hidden_user, body="hello")
        response = api_client.get(f"/api/community/events/{event.id}/comments/", **admin_headers)
        assert response.status_code == 200
        comment = response.json()["items"][0]
        assert comment["author_display_name"] == "Hidden Lastname"
