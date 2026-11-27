import pytest
from community.models import Club

from tests._auth import auth_headers_for
from tests._users import make_user


@pytest.mark.django_db
class TestRepClubIds:
    def test_me_lists_rep_clubs_sorted(self, api_client):
        user = make_user()
        clubs = [Club.objects.create(name=n, requirements="") for n in ("book club", "movie club")]
        for club in clubs:
            club.reps.add(user)

        response = api_client.get("/api/auth/me/", **auth_headers_for(user))

        assert response.json()["rep_club_ids"] == sorted(str(c.id) for c in clubs)

    def test_me_is_empty_for_non_rep(self, api_client):
        response = api_client.get("/api/auth/me/", **auth_headers_for(make_user()))

        assert response.json()["rep_club_ids"] == []

    def test_user_list_does_not_carry_rep_clubs(self, api_client):
        from users.permissions import PermissionKey

        admin = make_user(PermissionKey.MANAGE_USERS)
        club = Club.objects.create(name="book club", requirements="")
        club.reps.add(admin)

        response = api_client.get("/api/auth/users/", **auth_headers_for(admin))

        assert response.status_code == 200
        assert all(u["rep_club_ids"] == [] for u in response.json())
