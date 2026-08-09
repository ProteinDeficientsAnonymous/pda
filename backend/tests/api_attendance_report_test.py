import pytest
from community.models import Event, EventStatus, EventType, EventRSVP, RSVPStatus, AttendanceStatus
from django.utils import timezone
from users.permissions import PermissionKey


@pytest.mark.django_db
class TestAttendanceReport:
    def test_returns_split_no_show_counts_by_event_type(self, api_client, test_user, auth_headers):
        test_user.grant_permission(PermissionKey.MANAGE_EVENTS)

        official_event = Event.objects.create(
            title="Official Event",
            start_datetime=timezone.now() + timezone.timedelta(days=1),
            status=EventStatus.ACTIVE,
            event_type=EventType.OFFICIAL,
            rsvp_enabled=True,
        )
        club_event = Event.objects.create(
            title="Club Event",
            start_datetime=timezone.now() + timezone.timedelta(days=2),
            status=EventStatus.ACTIVE,
            event_type=EventType.CLUB,
            rsvp_enabled=True,
        )

        attending_user = test_user
        EventRSVP.objects.create(
            event=official_event,
            user=attending_user,
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.DIDNT_GO,
        )
        EventRSVP.objects.create(
            event=club_event,
            user=attending_user,
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.DIDNT_GO,
        )

        response = api_client.get("/api/community/events/attendance-report/", **auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["official_no_show_count"] == 1
        assert data["club_no_show_count"] == 1
        assert len(data["events"]) == 2

    def test_includes_event_type_in_rows(self, api_client, test_user, auth_headers):
        test_user.grant_permission(PermissionKey.MANAGE_EVENTS)

        event = Event.objects.create(
            title="Official Event",
            start_datetime=timezone.now() + timezone.timedelta(days=1),
            status=EventStatus.ACTIVE,
            event_type=EventType.OFFICIAL,
            rsvp_enabled=True,
        )

        attending_user = test_user
        EventRSVP.objects.create(
            event=event,
            user=attending_user,
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )

        response = api_client.get("/api/community/events/attendance-report/", **auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["event_type"] == "official"

    def test_only_counts_official_and_club_types(self, api_client, test_user, auth_headers):
        test_user.grant_permission(PermissionKey.MANAGE_EVENTS)

        official_event = Event.objects.create(
            title="Official",
            start_datetime=timezone.now() + timezone.timedelta(days=1),
            status=EventStatus.ACTIVE,
            event_type=EventType.OFFICIAL,
            rsvp_enabled=True,
        )
        club_event = Event.objects.create(
            title="Club",
            start_datetime=timezone.now() + timezone.timedelta(days=2),
            status=EventStatus.ACTIVE,
            event_type=EventType.CLUB,
            rsvp_enabled=True,
        )
        community_event = Event.objects.create(
            title="Community",
            start_datetime=timezone.now() + timezone.timedelta(days=3),
            status=EventStatus.ACTIVE,
            event_type=EventType.COMMUNITY,
            rsvp_enabled=True,
        )

        attending_user = test_user
        for event in [official_event, club_event, community_event]:
            EventRSVP.objects.create(
                event=event,
                user=attending_user,
                status=RSVPStatus.ATTENDING,
                attendance=AttendanceStatus.DIDNT_GO,
            )

        response = api_client.get("/api/community/events/attendance-report/", **auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["official_no_show_count"] == 1
        assert data["club_no_show_count"] == 1

    def test_excludes_draft_and_deleted_events(self, api_client, test_user, auth_headers):
        test_user.grant_permission(PermissionKey.MANAGE_EVENTS)

        draft_event = Event.objects.create(
            title="Draft Official",
            start_datetime=timezone.now() + timezone.timedelta(days=1),
            status=EventStatus.DRAFT,
            event_type=EventType.OFFICIAL,
            rsvp_enabled=True,
        )
        deleted_event = Event.objects.create(
            title="Deleted Club",
            start_datetime=timezone.now() + timezone.timedelta(days=2),
            status=EventStatus.DELETED,
            event_type=EventType.CLUB,
            rsvp_enabled=True,
        )

        attending_user = test_user
        for event in [draft_event, deleted_event]:
            EventRSVP.objects.create(
                event=event,
                user=attending_user,
                status=RSVPStatus.ATTENDING,
                attendance=AttendanceStatus.DIDNT_GO,
            )

        response = api_client.get("/api/community/events/attendance-report/", **auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["official_no_show_count"] == 0
        assert data["club_no_show_count"] == 0
        assert len(data["events"]) == 0

    def test_requires_manage_events_permission(self, api_client, test_user, auth_headers):
        response = api_client.get("/api/community/events/attendance-report/", **auth_headers)
        assert response.status_code == 403
