import pytest


@pytest.mark.django_db
class TestCalendarToken:
    def test_get_token_empty_before_generation(self, api_client, auth_headers):
        resp = api_client.get("/api/community/calendar/token/", **auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["token"] == ""
        assert data["feed_url"] == ""

    def test_generate_token(self, api_client, auth_headers):
        resp = api_client.post("/api/community/calendar/token/", **auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["token"]) > 0
        assert "calendar/feed/?token=" in data["feed_url"]

    def test_regenerate_token_replaces_old(self, api_client, auth_headers):
        resp1 = api_client.post("/api/community/calendar/token/", **auth_headers)
        token1 = resp1.json()["token"]
        resp2 = api_client.post("/api/community/calendar/token/", **auth_headers)
        token2 = resp2.json()["token"]
        assert token1 != token2

    def test_get_token_returns_existing(self, api_client, auth_headers):
        api_client.post("/api/community/calendar/token/", **auth_headers)
        resp = api_client.get("/api/community/calendar/token/", **auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["token"]) > 0

    def test_token_endpoints_require_auth(self, api_client):
        assert api_client.get("/api/community/calendar/token/").status_code == 401
        assert api_client.post("/api/community/calendar/token/").status_code == 401


@pytest.mark.django_db
class TestCalendarFeed:
    def test_feed_returns_ics(self, api_client, auth_headers, test_user):
        from community.models import Event

        # Generate token
        resp = api_client.post("/api/community/calendar/token/", **auth_headers)
        token = resp.json()["token"]

        # Create an event
        from django.utils import timezone

        Event.objects.create(
            title="Test Potluck",
            description="Bring snacks!",
            location="The park",
            start_datetime=timezone.now(),
            created_by=test_user,
        )

        # Fetch feed
        resp = api_client.get(f"/api/community/calendar/feed/?token={token}")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/calendar"
        content = resp.content.decode()
        assert "BEGIN:VCALENDAR" in content
        assert "Test Potluck" in content
        assert "The park" in content

    def test_feed_defaults_end_to_start_plus_2h(self, api_client, auth_headers, test_user):
        import datetime as dt

        from community.models import Event

        resp = api_client.post("/api/community/calendar/token/", **auth_headers)
        token = resp.json()["token"]

        start = dt.datetime(2026, 7, 1, 18, 0, tzinfo=dt.UTC)
        Event.objects.create(
            title="No End Time",
            start_datetime=start,
            created_by=test_user,
        )

        resp = api_client.get(f"/api/community/calendar/feed/?token={token}")
        content = resp.content.decode()
        assert "DTEND" in content
        # start + 2h = 20:00 UTC
        assert "20260701T200000" in content

    def test_feed_includes_links_in_description(self, api_client, auth_headers, test_user):
        from community.models import Event
        from django.utils import timezone

        resp = api_client.post("/api/community/calendar/token/", **auth_headers)
        token = resp.json()["token"]

        Event.objects.create(
            title="Linked Event",
            description="Join us!",
            start_datetime=timezone.now(),
            whatsapp_link="https://chat.whatsapp.com/abc",
            partiful_link="https://partiful.com/e/xyz",
            created_by=test_user,
        )

        resp = api_client.get(f"/api/community/calendar/feed/?token={token}")
        # Unfold ICS line continuations before checking
        content = resp.content.decode().replace("\r\n ", "")
        assert "Join us!" in content
        assert "WhatsApp: https://chat.whatsapp.com/abc" in content
        assert "Partiful: https://partiful.com/e/xyz" in content
        # The "View on PDA: <url>" trailer is what the frontend "add to
        # calendar" button and the .ics feed both use to link people back to
        # the event detail page (issue #347).
        assert "View on PDA: http" in content

    def test_feed_invalid_token_403(self, api_client):
        resp = api_client.get("/api/community/calendar/feed/?token=bogus-token")
        assert resp.status_code == 403

    def test_feed_missing_token_403(self, api_client):
        resp = api_client.get("/api/community/calendar/feed/")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestCalendarFeedScope:
    """Scope preference: 'all' (default, excludes drafts) vs 'mine' (user's events only)."""

    def _token_for(self, api_client, auth_headers):
        resp = api_client.post("/api/community/calendar/token/", **auth_headers)
        return resp.json()["token"]

    def _make_other_user(self, suffix="0102"):
        from users.models import User

        return User.objects.create_user(
            phone_number=f"+1202555{suffix}",
            password="testpass123",
            display_name=f"Other {suffix}",
        )

    def test_all_mode_excludes_drafts(self, api_client, auth_headers, test_user):
        from community.models import Event, EventStatus
        from django.utils import timezone

        token = self._token_for(api_client, auth_headers)
        other = self._make_other_user("0201")

        Event.objects.create(
            title="Active Event",
            start_datetime=timezone.now(),
            created_by=other,
            status=EventStatus.ACTIVE,
        )
        Event.objects.create(
            title="Draft Event",
            start_datetime=timezone.now(),
            created_by=other,
            status=EventStatus.DRAFT,
        )

        resp = api_client.get(f"/api/community/calendar/feed/?token={token}")
        content = resp.content.decode()
        assert "Active Event" in content
        assert "Draft Event" not in content

    def test_all_mode_excludes_deleted_and_cancelled(self, api_client, auth_headers, test_user):
        from community.models import Event, EventStatus
        from django.utils import timezone

        token = self._token_for(api_client, auth_headers)
        other = self._make_other_user("0202")

        Event.objects.create(
            title="Cancelled Event",
            start_datetime=timezone.now(),
            created_by=other,
            status=EventStatus.CANCELLED,
        )
        Event.objects.create(
            title="Deleted Event",
            start_datetime=timezone.now(),
            created_by=other,
            status=EventStatus.DELETED,
        )

        resp = api_client.get(f"/api/community/calendar/feed/?token={token}")
        content = resp.content.decode()
        assert "Cancelled Event" not in content
        assert "Deleted Event" not in content

    def test_mine_mode_includes_creator_cohost_invited_and_rsvps(
        self, api_client, auth_headers, test_user
    ):
        from community.models import Event, EventRSVP, RSVPStatus
        from django.utils import timezone
        from users.models import CalendarFeedScope

        test_user.calendar_feed_scope = CalendarFeedScope.MINE
        test_user.save(update_fields=["calendar_feed_scope"])
        token = self._token_for(api_client, auth_headers)
        other = self._make_other_user("0301")

        # creator
        Event.objects.create(
            title="Creator Event",
            start_datetime=timezone.now(),
            created_by=test_user,
        )
        # co-host
        cohost_event = Event.objects.create(
            title="Cohost Event",
            start_datetime=timezone.now(),
            created_by=other,
        )
        cohost_event.co_hosts.add(test_user)
        # invited
        invited_event = Event.objects.create(
            title="Invited Event",
            start_datetime=timezone.now(),
            created_by=other,
        )
        invited_event.invited_users.add(test_user)
        # rsvp attending
        rsvp_going = Event.objects.create(
            title="Rsvp Attending",
            start_datetime=timezone.now(),
            created_by=other,
        )
        EventRSVP.objects.create(event=rsvp_going, user=test_user, status=RSVPStatus.ATTENDING)
        # rsvp maybe
        rsvp_maybe = Event.objects.create(
            title="Rsvp Maybe",
            start_datetime=timezone.now(),
            created_by=other,
        )
        EventRSVP.objects.create(event=rsvp_maybe, user=test_user, status=RSVPStatus.MAYBE)

        resp = api_client.get(f"/api/community/calendar/feed/?token={token}")
        content = resp.content.decode()
        assert "Creator Event" in content
        assert "Cohost Event" in content
        assert "Invited Event" in content
        assert "Rsvp Attending" in content
        assert "Rsvp Maybe" in content

    def test_mine_mode_excludes_cant_go_waitlisted_and_unrelated(
        self, api_client, auth_headers, test_user
    ):
        from community.models import Event, EventRSVP, RSVPStatus
        from django.utils import timezone
        from users.models import CalendarFeedScope

        test_user.calendar_feed_scope = CalendarFeedScope.MINE
        test_user.save(update_fields=["calendar_feed_scope"])
        token = self._token_for(api_client, auth_headers)
        other = self._make_other_user("0302")

        Event.objects.create(
            title="Unrelated Event",
            start_datetime=timezone.now(),
            created_by=other,
        )
        rsvp_cant_go = Event.objects.create(
            title="Cant Go Event",
            start_datetime=timezone.now(),
            created_by=other,
        )
        EventRSVP.objects.create(event=rsvp_cant_go, user=test_user, status=RSVPStatus.CANT_GO)
        rsvp_waitlisted = Event.objects.create(
            title="Waitlisted Event",
            start_datetime=timezone.now(),
            created_by=other,
        )
        EventRSVP.objects.create(
            event=rsvp_waitlisted, user=test_user, status=RSVPStatus.WAITLISTED
        )

        resp = api_client.get(f"/api/community/calendar/feed/?token={token}")
        content = resp.content.decode()
        assert "Unrelated Event" not in content
        assert "Cant Go Event" not in content
        assert "Waitlisted Event" not in content

    def test_mine_mode_still_hides_invite_only_when_not_participant(
        self, api_client, auth_headers, test_user
    ):
        from community.models import Event, PageVisibility
        from django.utils import timezone
        from users.models import CalendarFeedScope

        test_user.calendar_feed_scope = CalendarFeedScope.MINE
        test_user.save(update_fields=["calendar_feed_scope"])
        token = self._token_for(api_client, auth_headers)
        other = self._make_other_user("0303")

        # Invite-only event the test_user has no relationship to
        Event.objects.create(
            title="Secret Event",
            start_datetime=timezone.now(),
            created_by=other,
            visibility=PageVisibility.INVITE_ONLY,
        )

        resp = api_client.get(f"/api/community/calendar/feed/?token={token}")
        content = resp.content.decode()
        assert "Secret Event" not in content

    def test_patch_me_persists_scope(self, api_client, auth_headers, test_user):
        import json

        resp = api_client.patch(
            "/api/auth/me/",
            data=json.dumps({"calendar_feed_scope": "mine"}),
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["calendar_feed_scope"] == "mine"
        test_user.refresh_from_db()
        assert test_user.calendar_feed_scope == "mine"


@pytest.mark.django_db
class TestSingleEventIcs:
    def test_returns_ics_for_existing_event(self, api_client, test_user):
        from community.models import Event
        from django.utils import timezone

        event = Event.objects.create(
            title="Picnic in the Park",
            description="Bring hummus!",
            location="Prospect Park",
            start_datetime=timezone.now(),
            created_by=test_user,
        )

        resp = api_client.get(f"/api/community/events/{event.id}/ics/")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/calendar"
        content = resp.content.decode()
        assert "BEGIN:VCALENDAR" in content
        assert "Picnic in the Park" in content
        assert "Prospect Park" in content

    def test_returns_404_for_nonexistent_event(self, api_client):
        import uuid

        resp = api_client.get(f"/api/community/events/{uuid.uuid4()}/ics/")
        assert resp.status_code == 404
