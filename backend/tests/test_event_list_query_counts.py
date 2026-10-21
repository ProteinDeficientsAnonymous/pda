import pytest
from community.models import Event, EventRSVP, PageVisibility, RSVPStatus
from django.db import connection
from django.test.utils import CaptureQueriesContext
from ninja_jwt.tokens import RefreshToken
from users._helpers import visible_display_name, visible_name
from users.models import User
from users.roles import Role

from tests.conftest import future_iso


def _user(phone: str, name: str, **extra) -> User:
    return User.objects.create_user(
        phone_number=phone, password="Testpass123!", first_name=name, last_name="Last", **extra
    )


def _headers(user: User) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}


_seq = {"n": 0}


def _make_events(count: int, viewer: User | None) -> None:
    for _ in range(count):
        _seq["n"] += 1
        i = _seq["n"]
        creator = _user(f"+1415555{i:04d}", f"Host{i}", hide_last_name=True)
        cohost = _user(f"+1415666{i:04d}", f"Co{i}", hide_last_name=True)
        event = Event.objects.create(
            title=f"Event {i}", start_datetime=future_iso(days=2 + i), created_by=creator
        )
        event.co_hosts.add(cohost)
        invite_only = Event.objects.create(
            title=f"Private {i}",
            start_datetime=future_iso(days=2 + i),
            created_by=creator,
            visibility=PageVisibility.INVITE_ONLY,
        )
        if viewer is not None:
            invite_only.invited_users.add(viewer)


def _count(api_client, headers: dict) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = api_client.get("/api/community/events/", **headers)
    assert response.status_code == 200
    return len(ctx.captured_queries)


@pytest.mark.django_db
class TestListEventsQueryCount:
    def _assert_constant(self, api_client, viewer, headers):
        _make_events(2, viewer)
        small = _count(api_client, headers)
        _make_events(6, viewer)
        large = _count(api_client, headers)
        assert large == small

    def test_anonymous(self, api_client):
        self._assert_constant(api_client, None, {})

    def test_member(self, api_client, test_user, auth_headers):
        self._assert_constant(api_client, test_user, auth_headers)

    def test_admin(self, api_client):
        admin = _user("+12025550901", "Admin")
        admin.roles.add(Role.objects.get(name="admin", is_default=True))
        self._assert_constant(api_client, admin, _headers(admin))


def _add_people(event: Event, count: int) -> None:
    for _ in range(count):
        _seq["n"] += 1
        i = _seq["n"]
        event.co_hosts.add(_user(f"+1415777{i:04d}", f"Co{i}", hide_last_name=True))
        guest = _user(f"+1415888{i:04d}", f"Guest{i}", hide_last_name=True)
        EventRSVP.objects.create(event=event, user=guest, status=RSVPStatus.ATTENDING)


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["", "guests/"])
def test_event_detail_names_do_not_query_per_person(api_client, test_user, auth_headers, path):
    host = _user("+12025550902", "Host", hide_last_name=True)
    event = Event.objects.create(
        title="Busy", start_datetime=future_iso(days=4), created_by=host, rsvp_enabled=True
    )
    EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)
    url = f"/api/community/events/{event.id}/{path}"

    _add_people(event, 2)
    with CaptureQueriesContext(connection) as small:
        assert api_client.get(url, **auth_headers).status_code == 200
    _add_people(event, 6)
    with CaptureQueriesContext(connection) as large:
        assert api_client.get(url, **auth_headers).status_code == 200
    assert len(large) == len(small)


@pytest.mark.django_db
def test_visible_names_check_viewer_roles_once(test_user, django_assert_num_queries):
    targets = [_user(f"+1415999{i:04d}", f"Hidden{i}", hide_last_name=True) for i in range(5)]
    viewer = User.objects.get(pk=test_user.pk)
    with django_assert_num_queries(1):
        for target in targets:
            visible_display_name(target, viewer)
            visible_name(target, viewer)
