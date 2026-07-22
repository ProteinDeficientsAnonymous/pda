"""Tests for the host-only per-event check-in report + CSV export."""

from datetime import timedelta

import pytest
from community.models import (
    AttendanceStatus,
    Event,
    EventRSVP,
    FeatureFlag,
    FeatureFlagState,
    RSVPStatus,
)
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.fixture(autouse=True)
def _flag_on(db):
    FeatureFlagState.objects.create(key=FeatureFlag.HOST_ATTENDANCE_REPORT, enabled=True)


@pytest.fixture
def host_user(db):
    return User.objects.create_user(phone_number="+12025559000", password="x", first_name="Host")


@pytest.fixture
def members(db):
    return [
        User.objects.create_user(
            phone_number=f"+1202555910{i}", password="x", first_name=f"Member {i}"
        )
        for i in range(1, 5)
    ]


@pytest.fixture
def guest_user(db):
    return User.objects.create_user(
        phone_number="+12025559200", password="x", first_name="Guest", is_member=False
    )


@pytest.fixture
def other_member(db):
    return User.objects.create_user(phone_number="+12025559300", password="x", first_name="Other")


@pytest.fixture
def past_event(db, host_user):
    return Event.objects.create(
        title="Past Potluck",
        start_datetime=timezone.now() - timedelta(days=2),
        end_datetime=timezone.now() - timedelta(days=2, hours=-2),
        rsvp_enabled=True,
        created_by=host_user,
    )


@pytest.fixture
def future_event(db, host_user):
    return Event.objects.create(
        title="Future Potluck",
        start_datetime=timezone.now() + timedelta(days=2),
        end_datetime=timezone.now() + timedelta(days=2, hours=2),
        rsvp_enabled=True,
        created_by=host_user,
    )


@pytest.fixture
def stocked_event(past_event, members, guest_user):
    EventRSVP.objects.create(
        event=past_event,
        user=members[0],
        status=RSVPStatus.ATTENDING,
        attendance=AttendanceStatus.ATTENDED,
        checked_in_at=timezone.now() - timedelta(days=2),
    )
    EventRSVP.objects.create(
        event=past_event,
        user=guest_user,
        status=RSVPStatus.ATTENDING,
        attendance=AttendanceStatus.ATTENDED,
        checked_in_at=timezone.now() - timedelta(days=2),
    )
    EventRSVP.objects.create(
        event=past_event,
        user=members[1],
        status=RSVPStatus.ATTENDING,
        attendance=AttendanceStatus.NO_SHOW,
    )
    EventRSVP.objects.create(
        event=past_event,
        user=members[2],
        status=RSVPStatus.CANT_GO,
        cancelled_at=past_event.start_datetime - timedelta(days=1),
    )
    EventRSVP.objects.create(
        event=past_event,
        user=members[3],
        status=RSVPStatus.ATTENDING,
    )
    return past_event


@pytest.mark.django_db
class TestCheckInReportEndpoint:
    def test_host_gets_report(self, api_client, stocked_event, host_user):
        response = api_client.get(
            f"/api/community/events/{stocked_event.id}/report/", **_auth(host_user)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["attended_count"] == 2
        assert data["no_show_count"] == 1
        assert data["canceled_count"] == 1
        assert data["unmarked_count"] == 1

    def test_guest_rsvp_tagged_not_member(self, api_client, stocked_event, host_user, guest_user):
        response = api_client.get(
            f"/api/community/events/{stocked_event.id}/report/", **_auth(host_user)
        )
        attended = response.json()["attended"]
        guest_row = next(r for r in attended if r["user_id"] == str(guest_user.pk))
        assert guest_row["is_member"] is False

    def test_canceled_includes_cancelled_at(self, api_client, stocked_event, host_user):
        response = api_client.get(
            f"/api/community/events/{stocked_event.id}/report/", **_auth(host_user)
        )
        canceled = response.json()["canceled"]
        assert len(canceled) == 1
        assert canceled[0]["cancelled_at"] is not None

    def test_attended_includes_checked_in_at(self, api_client, stocked_event, host_user):
        response = api_client.get(
            f"/api/community/events/{stocked_event.id}/report/", **_auth(host_user)
        )
        attended = response.json()["attended"]
        assert all(r["checked_in_at"] is not None for r in attended)

    def test_non_host_forbidden(self, api_client, stocked_event, other_member):
        response = api_client.get(
            f"/api/community/events/{stocked_event.id}/report/", **_auth(other_member)
        )
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client, stocked_event):
        response = api_client.get(f"/api/community/events/{stocked_event.id}/report/")
        assert response.status_code == 401

    def test_not_found(self, api_client, host_user):
        response = api_client.get(
            "/api/community/events/00000000-0000-0000-0000-000000000000/report/",
            **_auth(host_user),
        )
        assert response.status_code == 404

    def test_event_not_ended_rejected(self, api_client, future_event, host_user):
        response = api_client.get(
            f"/api/community/events/{future_event.id}/report/", **_auth(host_user)
        )
        assert response.status_code == 400
        assert response.json()["detail"][0]["code"] == "event.check_in_report_not_yet_available"

    def test_flag_off_not_found(self, api_client, stocked_event, host_user):
        FeatureFlagState.objects.filter(key=FeatureFlag.HOST_ATTENDANCE_REPORT).update(
            enabled=False
        )
        response = api_client.get(
            f"/api/community/events/{stocked_event.id}/report/", **_auth(host_user)
        )
        assert response.status_code == 404

    def test_maybe_and_waitlisted_land_in_unmarked(
        self, api_client, past_event, members, host_user
    ):
        EventRSVP.objects.create(event=past_event, user=members[0], status=RSVPStatus.MAYBE)
        EventRSVP.objects.create(event=past_event, user=members[1], status=RSVPStatus.WAITLISTED)
        response = api_client.get(
            f"/api/community/events/{past_event.id}/report/", **_auth(host_user)
        )
        data = response.json()
        assert data["unmarked_count"] == 2
        assert {r["user_id"] for r in data["unmarked"]} == {
            str(members[0].pk),
            str(members[1].pk),
        }

    def test_removed_rsvps_excluded(self, api_client, past_event, members, host_user):
        EventRSVP.objects.create(event=past_event, user=members[0], status=RSVPStatus.REMOVED)
        response = api_client.get(
            f"/api/community/events/{past_event.id}/report/", **_auth(host_user)
        )
        data = response.json()
        total = (
            data["attended_count"]
            + data["no_show_count"]
            + data["canceled_count"]
            + data["unmarked_count"]
        )
        assert total == 0

    def test_own_row_shows_full_name_despite_hide_last_name(self, api_client, past_event):
        host = past_event.created_by
        host.first_name, host.last_name, host.hide_last_name = "Ada", "Lovelace", True
        host.save(update_fields=["first_name", "last_name", "hide_last_name"])
        EventRSVP.objects.create(event=past_event, user=host, status=RSVPStatus.ATTENDING)
        response = api_client.get(f"/api/community/events/{past_event.id}/report/", **_auth(host))
        row = next(r for r in response.json()["unmarked"] if r["user_id"] == str(host.pk))
        assert row["name"] == "Ada Lovelace"


@pytest.mark.django_db
class TestCheckInReportCsvEndpoint:
    def test_host_downloads_csv(self, api_client, stocked_event, host_user):
        response = api_client.get(
            f"/api/community/events/{stocked_event.id}/report.csv", **_auth(host_user)
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert "attachment" in response["Content-Disposition"]
        body = response.content.decode()
        assert "name" in body.splitlines()[0]

    def test_column_selection_respected(self, api_client, stocked_event, host_user):
        response = api_client.get(
            f"/api/community/events/{stocked_event.id}/report.csv?columns=name,attendance",
            **_auth(host_user),
        )
        header = response.content.decode().splitlines()[0]
        assert header == "name,attendance"

    def test_unknown_column_rejected(self, api_client, stocked_event, host_user):
        response = api_client.get(
            f"/api/community/events/{stocked_event.id}/report.csv?columns=name,not_a_column",
            **_auth(host_user),
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["code"] == "event.check_in_report_invalid_column"

    def test_non_host_forbidden(self, api_client, stocked_event, other_member):
        response = api_client.get(
            f"/api/community/events/{stocked_event.id}/report.csv", **_auth(other_member)
        )
        assert response.status_code == 403

    def test_event_not_ended_rejected(self, api_client, future_event, host_user):
        response = api_client.get(
            f"/api/community/events/{future_event.id}/report.csv", **_auth(host_user)
        )
        assert response.status_code == 400

    def test_flag_off_not_found(self, api_client, stocked_event, host_user):
        FeatureFlagState.objects.filter(key=FeatureFlag.HOST_ATTENDANCE_REPORT).update(
            enabled=False
        )
        response = api_client.get(
            f"/api/community/events/{stocked_event.id}/report.csv", **_auth(host_user)
        )
        assert response.status_code == 404

    def test_csv_matches_report_row_count(self, api_client, past_event, members, host_user):
        EventRSVP.objects.create(event=past_event, user=members[0], status=RSVPStatus.ATTENDING)
        EventRSVP.objects.create(event=past_event, user=members[1], status=RSVPStatus.MAYBE)
        EventRSVP.objects.create(event=past_event, user=members[2], status=RSVPStatus.REMOVED)
        report = api_client.get(
            f"/api/community/events/{past_event.id}/report/", **_auth(host_user)
        ).json()
        csv_body = api_client.get(
            f"/api/community/events/{past_event.id}/report.csv", **_auth(host_user)
        ).content.decode()
        data_rows = [line for line in csv_body.splitlines()[1:] if line]
        report_total = (
            report["attended_count"]
            + report["no_show_count"]
            + report["canceled_count"]
            + report["unmarked_count"]
        )
        assert len(data_rows) == report_total == 2

    def test_csv_escapes_formula_injection(self, api_client, past_event, host_user):
        attacker = User.objects.create_user(
            phone_number="+12025559500",
            password="x",
            first_name="=HYPERLINK(1)",
            is_member=False,
        )
        EventRSVP.objects.create(event=past_event, user=attacker, status=RSVPStatus.ATTENDING)
        response = api_client.get(
            f"/api/community/events/{past_event.id}/report.csv?columns=name", **_auth(host_user)
        )
        body = response.content.decode()
        assert "'=HYPERLINK(1)" in body
        assert "\n=HYPERLINK(1)" not in body.replace("\r", "")
