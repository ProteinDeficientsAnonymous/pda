import pytest
from community._shared import _optional_jwt
from community.models import Event, EventComment, EventRSVP, PageVisibility, RSVPStatus
from config.auth import gated_jwt
from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests.conftest import future_iso

_ROLES_TABLE = User.roles.through._meta.db_table


def _host() -> User:
    return User.objects.create_user(phone_number="+14155550999", password="x", first_name="Host")


def _capture(api_client, url: str, headers: dict) -> CaptureQueriesContext:
    with CaptureQueriesContext(connection) as ctx:
        response = api_client.get(url, **headers)
    assert response.status_code == 200
    return ctx


def _roles_queries(ctx: CaptureQueriesContext) -> int:
    return sum(_ROLES_TABLE in q["sql"] for q in ctx.captured_queries)


@pytest.mark.django_db
@pytest.mark.parametrize("auth", [gated_jwt, _optional_jwt], ids=["gated", "optional"])
def test_has_permission_loads_roles_once(auth, test_user, django_assert_num_queries):
    token = str(RefreshToken.for_user(test_user).access_token)
    user = auth.authenticate(RequestFactory().get("/api/community/events/"), token)
    with django_assert_num_queries(1):
        user.has_permission(PermissionKey.MANAGE_EVENTS)
        user.has_permission(PermissionKey.MANAGE_USERS)


@pytest.mark.django_db
def test_roles_add_invalidates_cached_roles(test_user):
    assert not test_user.has_permission(PermissionKey.MANAGE_USERS)
    test_user.roles.add(Role.objects.get(name="admin", is_default=True))
    assert test_user.has_permission(PermissionKey.MANAGE_USERS)


@pytest.mark.django_db
def test_unread_count_skips_roles(api_client, auth_headers):
    ctx = _capture(api_client, "/api/notifications/unread-count/", auth_headers)
    assert _roles_queries(ctx) == 0


@pytest.mark.django_db
def test_event_detail_loads_roles_once(api_client, test_user, auth_headers):
    event = Event.objects.create(title="e", start_datetime=future_iso(days=3), created_by=_host())
    EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)
    ctx = _capture(api_client, f"/api/community/events/{event.id}/", auth_headers)
    assert _roles_queries(ctx) == 1


@pytest.mark.django_db
def test_comment_list_does_not_scale_with_comments(
    api_client, test_user, auth_headers, django_assert_num_queries
):
    host = _host()
    event = Event.objects.create(title="e", start_datetime=future_iso(days=3), created_by=host)
    EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)
    url = f"/api/community/events/{event.id}/comments/"

    def add_threads(n: int) -> None:
        for i in range(n):
            parent = EventComment.objects.create(event=event, author=host, body=f"c{i}")
            EventComment.objects.create(event=event, author=host, body=f"r{i}", parent=parent)

    add_threads(1)
    small = _capture(api_client, url, auth_headers)
    assert _roles_queries(small) == 1
    add_threads(6)
    with django_assert_num_queries(len(small.captured_queries)):
        api_client.get(url, **auth_headers)


@pytest.mark.django_db
def test_calendar_feed_does_not_scale_with_invite_only_events(
    api_client, test_user, django_assert_num_queries
):
    test_user.calendar_token = "feed-token"
    test_user.save(update_fields=["calendar_token"])
    host = _host()
    url = "/api/community/calendar/feed/?token=feed-token"

    def add_invite_only(n: int) -> None:
        for i in range(n):
            Event.objects.create(
                title=f"p{i}",
                start_datetime=future_iso(days=3 + i),
                created_by=host,
                visibility=PageVisibility.INVITE_ONLY,
            )

    add_invite_only(1)
    small = _capture(api_client, url, {})
    add_invite_only(5)
    with django_assert_num_queries(len(small.captured_queries)):
        api_client.get(url)


@pytest.mark.django_db
def test_me_reuses_authenticated_user(api_client, auth_headers, django_assert_num_queries):
    with django_assert_num_queries(2):
        response = api_client.get("/api/auth/me/", **auth_headers)
    assert response.status_code == 200
