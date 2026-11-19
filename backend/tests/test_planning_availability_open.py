import pytest
from community.validation import Code
from django.test import TestCase
from notifications.models import Notification, NotificationType
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._planning import headers_for, send
from tests._users import make_user

URL = "/api/community/planning/years/2027/availability/open/"
VIEW = PermissionKey.VIEW_EVENT_PLANNING


def open_availability(api_client, actor, url=URL):
    with TestCase.captureOnCommitCallbacks(execute=True):
        return send(api_client, "post", url, headers=auth_headers_for(actor))


@pytest.mark.django_db
class TestOpenAvailability:
    def test_view_only_forbidden(self, api_client, year):
        assert send(api_client, "post", URL, headers=headers_for(VIEW)).status_code == 403

    def test_unknown_year(self, api_client, coordinator):
        response = open_availability(api_client, coordinator, URL.replace("2027", "2031"))
        assert response.status_code == 404
        assert_error_code(response, Code.Planning.YEAR_NOT_FOUND)

    def test_stamps_the_year_and_asks_planners(
        self, api_client, year, coordinator, fake_email_sender
    ):
        planner = make_user(VIEW)

        response = open_availability(api_client, coordinator)

        assert response.status_code == 200
        year.refresh_from_db()
        assert year.availability_opened_at is not None
        assert response.json()["availability_opened_at"] is not None
        notice = Notification.objects.get()
        assert (notice.recipient, notice.related_user) == (planner, coordinator)
        assert notice.notification_type == NotificationType.PLANNING_AVAILABILITY
        fake_email_sender.send.assert_called_once()

    def test_second_open_is_rejected_without_resending(
        self, api_client, year, coordinator, fake_email_sender
    ):
        make_user(VIEW)
        open_availability(api_client, coordinator)

        response = open_availability(api_client, coordinator)

        assert response.status_code == 400
        assert_error_code(response, Code.Planning.AVAILABILITY_ALREADY_OPEN)
        assert Notification.objects.count() == 1
        fake_email_sender.send.assert_called_once()

    def test_years_list_shows_opened_state(self, api_client, year, coordinator):
        url = "/api/community/planning/years/"
        before = send(api_client, "get", url, headers=auth_headers_for(coordinator))
        assert before.json()[0]["availability_opened_at"] is None
        open_availability(api_client, coordinator)
        after = send(api_client, "get", url, headers=auth_headers_for(coordinator))
        assert after.json()[0]["availability_opened_at"] is not None
