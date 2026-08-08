import pytest
from community.models import AttendanceStatus, EventRSVP, RSVPStatus

from tests.test_event_stats import (
    _auth,
    admin_user,
    cohost_user,
    host_user,
    members,
    open_check_in_event,
    stats_event,
)

__all__ = [
    "admin_user",
    "cohost_user",
    "host_user",
    "members",
    "open_check_in_event",
    "stats_event",
]


@pytest.mark.django_db
class TestStatsEndpoint:
    def test_host_gets_stats(self, api_client, stats_event, host_user, members):
        EventRSVP.objects.create(event=stats_event, user=members[0], status=RSVPStatus.ATTENDING)
        EventRSVP.objects.create(event=stats_event, user=members[1], status=RSVPStatus.CANT_GO)
        response = api_client.get(
            f"/api/community/events/{stats_event.id}/stats/", **_auth(host_user)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["going_count"] == 1
        assert data["cant_go_count"] == 1
        assert data["no_response_count"] == 2

    def test_cohost_gets_stats(self, api_client, stats_event, cohost_user):
        response = api_client.get(
            f"/api/community/events/{stats_event.id}/stats/", **_auth(cohost_user)
        )
        assert response.status_code == 200

    def test_admin_gets_stats(self, api_client, stats_event, admin_user):
        response = api_client.get(
            f"/api/community/events/{stats_event.id}/stats/", **_auth(admin_user)
        )
        assert response.status_code == 200

    def test_non_host_forbidden(self, api_client, stats_event, members):
        response = api_client.get(
            f"/api/community/events/{stats_event.id}/stats/", **_auth(members[0])
        )
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client, stats_event):
        response = api_client.get(f"/api/community/events/{stats_event.id}/stats/")
        assert response.status_code == 401

    def test_not_found(self, api_client, host_user):
        response = api_client.get(
            "/api/community/events/00000000-0000-0000-0000-000000000000/stats/",
            **_auth(host_user),
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestSetAttendance:
    def test_host_marks_attended(self, api_client, open_check_in_event, host_user, members):
        rsvp = EventRSVP.objects.create(
            event=open_check_in_event, user=members[0], status=RSVPStatus.ATTENDING
        )
        response = api_client.post(
            f"/api/community/events/{open_check_in_event.id}/rsvps/{members[0].pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 200
        rsvp.refresh_from_db()
        assert rsvp.attendance == AttendanceStatus.ATTENDED
        assert rsvp.checked_in_at is not None

    def test_guest_order_is_stable_across_check_ins(
        self, api_client, open_check_in_event, host_user, members
    ):
        for m in members:
            EventRSVP.objects.create(event=open_check_in_event, user=m, status=RSVPStatus.ATTENDING)
        detail_url = f"/api/community/events/{open_check_in_event.id}/"
        expected = [str(m.pk) for m in members]
        assert [
            g["user_id"] for g in api_client.get(detail_url, **_auth(host_user)).json()["guests"]
        ] == expected

        api_client.post(
            f"/api/community/events/{open_check_in_event.id}/rsvps/{members[1].pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(host_user),
        )

        after = api_client.get(detail_url, **_auth(host_user)).json()["guests"]
        assert [g["user_id"] for g in after] == expected

    def test_no_show_does_not_stamp_checked_in_at(
        self, api_client, open_check_in_event, host_user, members
    ):
        rsvp = EventRSVP.objects.create(
            event=open_check_in_event, user=members[0], status=RSVPStatus.ATTENDING
        )
        response = api_client.post(
            f"/api/community/events/{open_check_in_event.id}/rsvps/{members[0].pk}/attendance/",
            {"attendance": AttendanceStatus.NO_SHOW},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 200
        rsvp.refresh_from_db()
        assert rsvp.checked_in_at is None

    def test_checked_in_at_preserved_on_re_mark(
        self, api_client, open_check_in_event, host_user, members
    ):
        rsvp = EventRSVP.objects.create(
            event=open_check_in_event, user=members[0], status=RSVPStatus.ATTENDING
        )
        url = f"/api/community/events/{open_check_in_event.id}/rsvps/{members[0].pk}/attendance/"
        api_client.post(
            url,
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(host_user),
        )
        rsvp.refresh_from_db()
        first_check_in = rsvp.checked_in_at
        api_client.post(
            url,
            {"attendance": AttendanceStatus.NO_SHOW},
            content_type="application/json",
            **_auth(host_user),
        )
        api_client.post(
            url,
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(host_user),
        )
        rsvp.refresh_from_db()
        assert rsvp.checked_in_at == first_check_in

    def test_cohost_can_mark(self, api_client, open_check_in_event, cohost_user, members):
        EventRSVP.objects.create(
            event=open_check_in_event, user=members[0], status=RSVPStatus.ATTENDING
        )
        response = api_client.post(
            f"/api/community/events/{open_check_in_event.id}/rsvps/{members[0].pk}/attendance/",
            {"attendance": AttendanceStatus.NO_SHOW},
            content_type="application/json",
            **_auth(cohost_user),
        )
        assert response.status_code == 200

    def test_rejects_non_host(self, api_client, open_check_in_event, members):
        EventRSVP.objects.create(
            event=open_check_in_event, user=members[0], status=RSVPStatus.ATTENDING
        )
        response = api_client.post(
            f"/api/community/events/{open_check_in_event.id}/rsvps/{members[0].pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(members[1]),
        )
        assert response.status_code == 403

    def test_rejects_when_check_in_not_open(self, api_client, stats_event, host_user, members):
        EventRSVP.objects.create(event=stats_event, user=members[0], status=RSVPStatus.ATTENDING)
        response = api_client.post(
            f"/api/community/events/{stats_event.id}/rsvps/{members[0].pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 400
        assert response.json()["detail"][0]["code"] == "event.attendance_opens_later"

    def test_host_marks_attended_for_maybe_rsvp(
        self, api_client, open_check_in_event, host_user, members
    ):
        rsvp = EventRSVP.objects.create(
            event=open_check_in_event, user=members[0], status=RSVPStatus.MAYBE
        )
        response = api_client.post(
            f"/api/community/events/{open_check_in_event.id}/rsvps/{members[0].pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 200
        rsvp.refresh_from_db()
        assert rsvp.attendance == AttendanceStatus.ATTENDED
        assert rsvp.checked_in_at is not None

    def test_allows_check_in_when_rsvp_not_going(
        self, api_client, open_check_in_event, host_user, members
    ):
        EventRSVP.objects.create(
            event=open_check_in_event, user=members[0], status=RSVPStatus.CANT_GO
        )
        response = api_client.post(
            f"/api/community/events/{open_check_in_event.id}/rsvps/{members[0].pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 200

    def test_allows_check_in_when_rsvp_waitlisted(
        self, api_client, open_check_in_event, host_user, members
    ):
        EventRSVP.objects.create(
            event=open_check_in_event, user=members[0], status=RSVPStatus.WAITLISTED
        )
        response = api_client.post(
            f"/api/community/events/{open_check_in_event.id}/rsvps/{members[0].pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 200

    def test_rejects_unknown_rsvp(self, api_client, open_check_in_event, host_user, members):
        response = api_client.post(
            f"/api/community/events/{open_check_in_event.id}/rsvps/{members[0].pk}/attendance/",
            {"attendance": AttendanceStatus.ATTENDED},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 404

    def test_rejects_invalid_attendance_value(
        self, api_client, open_check_in_event, host_user, members
    ):
        EventRSVP.objects.create(
            event=open_check_in_event, user=members[0], status=RSVPStatus.ATTENDING
        )
        response = api_client.post(
            f"/api/community/events/{open_check_in_event.id}/rsvps/{members[0].pk}/attendance/",
            {"attendance": "maybe_attended"},
            content_type="application/json",
            **_auth(host_user),
        )
        assert response.status_code == 422

    def test_default_attendance_is_unknown(self, stats_event, members):
        rsvp = EventRSVP.objects.create(
            event=stats_event, user=members[0], status=RSVPStatus.ATTENDING
        )
        assert rsvp.attendance == AttendanceStatus.UNKNOWN
