from datetime import timedelta

import pytest
from community.models import AttendanceStatus, Event, EventRSVP, RSVPStatus
from django.utils import timezone
from notifications.models import Notification, NotificationType
from users.roles import Role

from tests._query_counts import assert_constant_queries, headers_for
from tests._users import make_user


def _grow_members(n: int) -> None:
    for _ in range(n):
        make_user(first_name="Grow", hide_last_name=True)


def _past_event(host) -> Event:
    return Event.objects.create(
        title="Past", start_datetime=timezone.now() - timedelta(days=3), created_by=host
    )


@pytest.mark.django_db
class TestUserEndpointsQueryCount:
    def test_member_directory(self, api_client):
        viewer = make_user(first_name="Viewer")
        assert_constant_queries(
            api_client, "/api/auth/users/directory/", _grow_members, headers_for(viewer)
        )

    def test_user_search(self, api_client):
        viewer = make_user(first_name="Viewer")
        assert_constant_queries(
            api_client, "/api/auth/users/search/?q=grow", _grow_members, headers_for(viewer)
        )

    def test_user_list(self, api_client, manage_users_headers):
        role = Role.objects.create(name="grower")

        def grow(n: int) -> None:
            for _ in range(n):
                user = make_user(first_name="Grow")
                user.roles.add(role)
                rsvp = EventRSVP.objects.create(
                    event=_past_event(user), user=user, status=RSVPStatus.ATTENDING
                )
                EventRSVP.objects.filter(pk=rsvp.pk).update(attendance=AttendanceStatus.ATTENDED)

        assert_constant_queries(api_client, "/api/auth/users/", grow, manage_users_headers)

    def test_member_attended_events(self, api_client, manage_users_headers):
        member = make_user(first_name="Member")

        def grow(n: int) -> None:
            for _ in range(n):
                EventRSVP.objects.create(
                    event=_past_event(make_user(first_name="Host")),
                    user=member,
                    status=RSVPStatus.ATTENDING,
                    attendance=AttendanceStatus.ATTENDED,
                )

        url = f"/api/auth/users/{member.id}/attended-events/"
        assert_constant_queries(api_client, url, grow, manage_users_headers)

    def test_roles(self, api_client, manage_roles_headers):
        def grow(n: int) -> None:
            for _ in range(n):
                role = Role.objects.create(name=f"role-{Role.objects.count()}")
                make_user(first_name="Grow").roles.add(role)

        assert_constant_queries(api_client, "/api/auth/roles/", grow, manage_roles_headers)

    def test_notifications(self, api_client, test_user, auth_headers):
        def grow(n: int) -> None:
            for _ in range(n):
                actor = make_user(first_name="Actor")
                Notification.objects.create(
                    recipient=test_user,
                    notification_type=NotificationType.EVENT_INVITE,
                    event=_past_event(actor),
                    related_user=actor,
                    message="invited you",
                )

        assert_constant_queries(api_client, "/api/notifications/", grow, auth_headers)
