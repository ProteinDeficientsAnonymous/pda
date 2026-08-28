import json

import pytest
from community.models import Event, EventRSVP, EventStatus, EventType, RSVPStatus
from django.utils import timezone
from users.models import CalendarFeedScope, User


@pytest.mark.django_db
class TestCalendarFeedExcludedTypes:
    """Per-event-type filtering of the subscription feed (Issue 1169)."""

    def _token_for(self, api_client, auth_headers):
        return api_client.post("/api/community/calendar/token/", **auth_headers).json()["token"]

    def _make_other(self, suffix="0401"):
        return User.objects.create_user(
            phone_number=f"+1202555{suffix}",
            password="testpass123",
            first_name=f"Other {suffix}",
            last_name="",
        )

    def _make_events(self):
        other = self._make_other()
        for event_type in (EventType.OFFICIAL, EventType.COMMUNITY, EventType.CLUB):
            Event.objects.create(
                title=f"{event_type.label} Event",
                start_datetime=timezone.now(),
                created_by=other,
                status=EventStatus.ACTIVE,
                event_type=event_type,
            )

    def test_defaults_to_every_type(self, api_client, auth_headers, test_user):
        token = self._token_for(api_client, auth_headers)
        self._make_events()

        content = api_client.get(f"/api/community/calendar/feed/?token={token}").content.decode()
        assert "Official Event" in content
        assert "Community Event" in content
        assert "Club Event" in content

    def test_excluded_type_is_dropped(self, api_client, auth_headers, test_user):
        test_user.calendar_feed_excluded_types = ["club"]
        test_user.save(update_fields=["calendar_feed_excluded_types"])
        token = self._token_for(api_client, auth_headers)
        self._make_events()

        content = api_client.get(f"/api/community/calendar/feed/?token={token}").content.decode()
        assert "Club Event" not in content
        assert "Official Event" in content
        assert "Community Event" in content

    def test_excluding_every_type_yields_empty_feed(self, api_client, auth_headers, test_user):
        test_user.calendar_feed_excluded_types = [
            EventType.OFFICIAL,
            EventType.COMMUNITY,
            EventType.CLUB,
        ]
        test_user.save(update_fields=["calendar_feed_excluded_types"])
        token = self._token_for(api_client, auth_headers)
        self._make_events()

        content = api_client.get(f"/api/community/calendar/feed/?token={token}").content.decode()
        assert "BEGIN:VEVENT" not in content

    def test_excluded_type_still_includes_own_events(self, api_client, auth_headers, test_user):
        test_user.calendar_feed_excluded_types = [EventType.CLUB]
        test_user.save(update_fields=["calendar_feed_excluded_types"])
        token = self._token_for(api_client, auth_headers)
        other = self._make_other("0402")

        Event.objects.create(
            title="Mine Created",
            start_datetime=timezone.now(),
            created_by=test_user,
            event_type=EventType.CLUB,
        )
        cohost = Event.objects.create(
            title="Mine Cohost",
            start_datetime=timezone.now(),
            created_by=other,
            event_type=EventType.CLUB,
        )
        cohost.co_hosts.add(test_user)
        invited = Event.objects.create(
            title="Mine Invited",
            start_datetime=timezone.now(),
            created_by=other,
            event_type=EventType.CLUB,
        )
        invited.invited_users.add(test_user)
        rsvpd = Event.objects.create(
            title="Mine Rsvpd",
            start_datetime=timezone.now(),
            created_by=other,
            event_type=EventType.CLUB,
        )
        EventRSVP.objects.create(event=rsvpd, user=test_user, status=RSVPStatus.ATTENDING)
        Event.objects.create(
            title="Unrelated Club",
            start_datetime=timezone.now(),
            created_by=other,
            event_type=EventType.CLUB,
        )

        content = api_client.get(f"/api/community/calendar/feed/?token={token}").content.decode()
        assert "Mine Created" in content
        assert "Mine Cohost" in content
        assert "Mine Invited" in content
        assert "Mine Rsvpd" in content
        assert "Unrelated Club" not in content

    def test_excluded_type_drops_declined_rsvp(self, api_client, auth_headers, test_user):
        test_user.calendar_feed_excluded_types = [EventType.CLUB]
        test_user.save(update_fields=["calendar_feed_excluded_types"])
        token = self._token_for(api_client, auth_headers)
        other = self._make_other("0403")

        declined = Event.objects.create(
            title="Declined Club",
            start_datetime=timezone.now(),
            created_by=other,
            event_type=EventType.CLUB,
        )
        EventRSVP.objects.create(event=declined, user=test_user, status=RSVPStatus.CANT_GO)

        content = api_client.get(f"/api/community/calendar/feed/?token={token}").content.decode()
        assert "Declined Club" not in content

    def test_excluded_type_exemption_applies_in_mine_scope(
        self, api_client, auth_headers, test_user
    ):
        test_user.calendar_feed_scope = CalendarFeedScope.MINE
        test_user.calendar_feed_excluded_types = [EventType.CLUB]
        test_user.save(
            update_fields=["calendar_feed_scope", "calendar_feed_excluded_types"],
        )
        token = self._token_for(api_client, auth_headers)

        Event.objects.create(
            title="Mine Club",
            start_datetime=timezone.now(),
            created_by=test_user,
            event_type=EventType.CLUB,
        )

        content = api_client.get(f"/api/community/calendar/feed/?token={token}").content.decode()
        assert "Mine Club" in content

    def test_patch_me_persists_excluded_types(self, api_client, auth_headers, test_user):
        resp = api_client.patch(
            "/api/auth/me/",
            data=json.dumps({"calendar_feed_excluded_types": ["club", "official"]}),
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["calendar_feed_excluded_types"] == ["club", "official"]
        test_user.refresh_from_db()
        assert test_user.calendar_feed_excluded_types == ["club", "official"]

    def test_patch_me_rejects_unknown_type(self, api_client, auth_headers, test_user):
        resp = api_client.patch(
            "/api/auth/me/",
            data=json.dumps({"calendar_feed_excluded_types": ["bogus"]}),
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 422
        test_user.refresh_from_db()
        assert test_user.calendar_feed_excluded_types == []
