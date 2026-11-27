import pytest
from community.models import Club, Event, EventType, PageVisibility
from users.permissions import PermissionKey

from tests._auth import auth_headers_for
from tests._time import future_iso
from tests._users import make_user

EVENTS_URL = "/api/community/events/"


@pytest.fixture
def book(db):
    return Club.objects.create(name="book club", requirements="")


@pytest.fixture
def movie(db):
    return Club.objects.create(name="movie club", requirements="")


@pytest.fixture
def rep(book):
    user = make_user()
    book.reps.add(user)
    return user


def _create(api_client, user, club, **fields):
    payload = {
        "title": "Meetup",
        "start_datetime": future_iso(days=10),
        "event_type": EventType.CLUB,
        "visibility": PageVisibility.PUBLIC,
        "club_id": str(club.id),
        **fields,
    }
    return api_client.post(
        EVENTS_URL, payload, content_type="application/json", **auth_headers_for(user)
    )


@pytest.mark.django_db
class TestRepClubEvents:
    def test_rep_creates_club_event_for_own_club(self, api_client, rep, book):
        assert _create(api_client, rep, book).status_code == 201

    def test_rep_cannot_create_for_other_club(self, api_client, rep, movie):
        assert _create(api_client, rep, movie).status_code == 403

    def test_rep_cannot_create_draft_for_other_club(self, api_client, rep, movie):
        assert _create(api_client, rep, movie, status="draft").status_code == 403

    def test_rep_cannot_move_event_to_other_club(self, api_client, rep, book, movie):
        event_id = _create(api_client, rep, book).json()["id"]

        response = api_client.patch(
            f"{EVENTS_URL}{event_id}/",
            {"club_id": str(movie.id)},
            content_type="application/json",
            **auth_headers_for(rep),
        )

        assert response.status_code == 403
        assert Event.objects.get(id=event_id).club_id == book.id

    def test_tag_club_event_holder_posts_for_any_club(self, api_client, movie):
        holder = make_user(PermissionKey.TAG_CLUB_EVENT)
        assert _create(api_client, holder, movie).status_code == 201

    def test_non_rep_without_permission_cannot_create_club_event(self, api_client, book):
        assert _create(api_client, make_user(), book).status_code == 403
