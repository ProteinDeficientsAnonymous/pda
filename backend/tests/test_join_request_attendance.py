"""Tests for join-request attendance history (Issue 1093)."""

from datetime import timedelta

import pytest
from community.models import (
    AttendanceStatus,
    Event,
    EventRSVP,
    EventStatus,
    EventType,
    FeatureFlag,
    FeatureFlagState,
    JoinRequest,
    RSVPStatus,
)
from django.utils import timezone

JOIN_REQUESTS_URL = "/api/community/join-requests/"


@pytest.fixture
def flag_on(db):
    FeatureFlagState.objects.create(key=FeatureFlag.ADMIN_ATTENDANCE_ANALYTICS, enabled=True)


@pytest.fixture
def host_user(db):
    from users.models import User

    return User.objects.create_user(phone_number="+12025551800", password="x", first_name="Host")


def _make_event(host_user, title, days_ago, event_type):
    start = timezone.now() - timedelta(days=days_ago)
    return Event.objects.create(
        title=title,
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        rsvp_enabled=True,
        created_by=host_user,
        status=EventStatus.ACTIVE,
        event_type=event_type,
    )


@pytest.mark.django_db
class TestJoinRequestAttendedEvents:
    def test_empty_when_flag_off(self, api_client, vettor_headers, host_user):
        from users.models import User

        guest = User.objects.create_user(
            phone_number="+16505551234", password="x", first_name="Guest", is_member=False
        )
        event = _make_event(
            host_user, "Community Meetup", days_ago=5, event_type=EventType.COMMUNITY
        )
        EventRSVP.objects.create(
            event=event,
            user=guest,
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        JoinRequest.objects.create(
            first_name="Sprout", last_name="Seedling", phone_number="+16505551234"
        )

        response = api_client.get(JOIN_REQUESTS_URL, **vettor_headers)
        assert response.status_code == 200
        row = response.json()[0]
        assert row["attended_events"] == []

    def test_all_event_types_included_when_account_linked(
        self, api_client, vettor_headers, flag_on, host_user
    ):
        from users.models import User

        applicant = User.objects.create_user(
            phone_number="+16505551234", password="x", first_name="Guest", is_member=False
        )
        community_event = _make_event(
            host_user, "Community Meetup", days_ago=5, event_type=EventType.COMMUNITY
        )
        club_event = _make_event(host_user, "Club Night", days_ago=10, event_type=EventType.CLUB)
        for ev in (community_event, club_event):
            EventRSVP.objects.create(
                event=ev,
                user=applicant,
                status=RSVPStatus.ATTENDING,
                attendance=AttendanceStatus.ATTENDED,
            )
        JoinRequest.objects.create(
            first_name="Sprout",
            last_name="Seedling",
            phone_number="+16505551234",
            user=applicant,
        )

        response = api_client.get(JOIN_REQUESTS_URL, **vettor_headers)
        row = response.json()[0]
        titles = {e["title"]: e["event_type"] for e in row["attended_events"]}
        assert titles == {"Community Meetup": "community", "Club Night": "club"}

    def test_no_history_without_linked_account(
        self, api_client, vettor_headers, flag_on, host_user
    ):
        """A bare phone match to a guest row must not surface that guest's history."""
        from users.models import User

        guest = User.objects.create_user(
            phone_number="+16505551234", password="x", first_name="Guest", is_member=False
        )
        event = _make_event(
            host_user, "Community Meetup", days_ago=5, event_type=EventType.COMMUNITY
        )
        EventRSVP.objects.create(
            event=event,
            user=guest,
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        JoinRequest.objects.create(
            first_name="Sprout", last_name="Seedling", phone_number="+16505551234"
        )

        response = api_client.get(JOIN_REQUESTS_URL, **vettor_headers)
        row = response.json()[0]
        assert row["attended_events"] == []

    def test_two_guests_same_phone_not_attributed(
        self, api_client, vettor_headers, flag_on, host_user
    ):
        """Guest A's attendance must not appear on unlinked applicant B who shares A's phone."""
        from users.models import User

        guest_a = User.objects.create_user(
            phone_number="+16505551234", password="x", first_name="GuestA", is_member=False
        )
        event = _make_event(host_user, "Club Night", days_ago=10, event_type=EventType.CLUB)
        EventRSVP.objects.create(
            event=event,
            user=guest_a,
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        JoinRequest.objects.create(
            first_name="Applicant", last_name="Bee", phone_number="+16505551234"
        )

        response = api_client.get(JOIN_REQUESTS_URL, **vettor_headers)
        row = response.json()[0]
        assert row["attended_events"] == []

    def test_resolves_via_join_request_user_fk(
        self, api_client, vettor_headers, flag_on, host_user
    ):
        from users.models import User

        member = User.objects.create_user(
            phone_number="+16505559999", password="x", first_name="Member", is_member=True
        )
        event = _make_event(host_user, "Official Gala", days_ago=3, event_type=EventType.OFFICIAL)
        EventRSVP.objects.create(
            event=event,
            user=member,
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        jr = JoinRequest.objects.create(
            first_name="Sprout",
            last_name="Seedling",
            phone_number="+16505550000",
            user=member,
        )

        response = api_client.get(JOIN_REQUESTS_URL, **vettor_headers)
        row = next(r for r in response.json() if r["id"] == str(jr.id))
        assert [e["title"] for e in row["attended_events"]] == ["Official Gala"]

    def test_empty_when_no_match(self, api_client, vettor_headers, flag_on):
        JoinRequest.objects.create(
            first_name="Nomatch", last_name="Person", phone_number="+16505550001"
        )
        response = api_client.get(JOIN_REQUESTS_URL, **vettor_headers)
        row = response.json()[0]
        assert row["attended_events"] == []

    def test_phone_fallback_excludes_members(self, api_client, vettor_headers, flag_on, host_user):
        """A member sharing the phone number of a JoinRequest isn't a guest match."""
        from users.models import User

        member = User.objects.create_user(
            phone_number="+16505551234", password="x", first_name="Member", is_member=True
        )
        event = _make_event(host_user, "Club Meetup", days_ago=5, event_type=EventType.CLUB)
        EventRSVP.objects.create(
            event=event,
            user=member,
            status=RSVPStatus.ATTENDING,
            attendance=AttendanceStatus.ATTENDED,
        )
        JoinRequest.objects.create(
            first_name="Sprout", last_name="Seedling", phone_number="+16505551234"
        )

        response = api_client.get(JOIN_REQUESTS_URL, **vettor_headers)
        row = response.json()[0]
        assert row["attended_events"] == []
