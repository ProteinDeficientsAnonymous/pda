import pytest
from community.models import Event, EventStatus, EventType, PageVisibility, RSVPStatus
from django.utils import timezone


@pytest.mark.django_db
class TestCreateDevTestEvent:
    def test_create_default_is_active_with_going_fillers(self, api_client, auth_headers, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == EventStatus.ACTIVE
        assert body["title"]

        event = Event.objects.get(id=body["id"])
        assert event.rsvps.filter(status=RSVPStatus.ATTENDING).count() == 5
        assert event.rsvp_enabled is True
        assert event.visibility == PageVisibility.PUBLIC
        assert bool(event.photo)

    def test_create_allowed_on_staging(self, api_client, auth_headers, monkeypatch):
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "staging")
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201

    def test_404s_on_production(self, api_client, auth_headers, monkeypatch):
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 404

    def test_unauthenticated_401s(self, api_client, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_is_canceled_sets_cancelled_status(self, api_client, auth_headers, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={"is_canceled": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.json()["status"] == EventStatus.CANCELLED

    def test_is_past_backdates_event(self, api_client, auth_headers, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={"is_past": True},
            content_type="application/json",
            **auth_headers,
        )
        event = Event.objects.get(id=response.json()["id"])
        assert event.start_datetime < timezone.now()

    def test_is_club_sets_club_type(self, api_client, auth_headers, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={"is_club": True},
            content_type="application/json",
            **auth_headers,
        )
        event = Event.objects.get(id=response.json()["id"])
        assert event.event_type == EventType.CLUB
        assert event.visibility == PageVisibility.PUBLIC

    def test_cost_fields_are_set(self, api_client, auth_headers, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={"price": "$10", "venmo_link": "@test-venmo", "zelle_info": "test@zelle.com"},
            content_type="application/json",
            **auth_headers,
        )
        event = Event.objects.get(id=response.json()["id"])
        assert event.price == "$10"
        assert event.venmo_link == "@test-venmo"
        assert event.zelle_info == "test@zelle.com"

    def test_rsvp_enabled_toggle_off(self, api_client, auth_headers, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={"rsvp_enabled": False},
            content_type="application/json",
            **auth_headers,
        )
        event = Event.objects.get(id=response.json()["id"])
        assert event.rsvp_enabled is False

    def test_members_only_visibility(self, api_client, auth_headers, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={"visibility": "members_only"},
            content_type="application/json",
            **auth_headers,
        )
        event = Event.objects.get(id=response.json()["id"])
        assert event.visibility == PageVisibility.MEMBERS_ONLY

    def test_official_forces_public_visibility_even_if_requested_otherwise(
        self, api_client, auth_headers, monkeypatch
    ):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={"is_official": True, "visibility": "members_only"},
            content_type="application/json",
            **auth_headers,
        )
        event = Event.objects.get(id=response.json()["id"])
        assert event.visibility == PageVisibility.PUBLIC

    def test_max_attendees_below_going_count_creates_waitlist(
        self, api_client, auth_headers, monkeypatch
    ):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={"going_count": 5, "max_attendees": 2},
            content_type="application/json",
            **auth_headers,
        )
        event = Event.objects.get(id=response.json()["id"])
        assert event.rsvps.filter(status=RSVPStatus.ATTENDING).count() == 2
        assert event.rsvps.filter(status=RSVPStatus.WAITLISTED).count() == 3

    def test_attendee_counts_create_distinct_filler_users(self, api_client, auth_headers, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={"going_count": 3, "maybe_count": 2, "cant_go_count": 1, "invited_count": 2},
            content_type="application/json",
            **auth_headers,
        )
        event = Event.objects.get(id=response.json()["id"])
        assert event.rsvps.filter(status=RSVPStatus.ATTENDING).count() == 3
        assert event.rsvps.filter(status=RSVPStatus.MAYBE).count() == 2
        assert event.rsvps.filter(status=RSVPStatus.CANT_GO).count() == 1
        assert event.invited_users.count() == 2
        rsvp_user_ids = set(event.rsvps.values_list("user_id", flat=True))
        assert len(rsvp_user_ids) == 6

    def test_cohost_counts_populate_accepted_and_pending(self, api_client, auth_headers, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={"cohost_count": 2, "invited_cohost_count": 1},
            content_type="application/json",
            **auth_headers,
        )
        event = Event.objects.get(id=response.json()["id"])
        # co_hosts includes the creator (auto-seeded by seed_creator_as_host),
        # plus the 2 accepted fillers requested.
        assert event.co_hosts.count() == 3
        assert event.cohost_invites.count() == 1

    def test_non_member_going_adds_alongside_member_going(
        self, api_client, auth_headers, monkeypatch
    ):
        """non_member_going_count must ADD non-member RSVPs, not replace the
        member `going_count` pool — regression test for a bug where turning on
        non-member fillers made every going RSVP non-member."""
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={
                "going_count": 3,
                "non_member_going_count": 2,
                "maybe_count": 0,
                "cant_go_count": 0,
                "is_official": True,
            },
            content_type="application/json",
            **auth_headers,
        )
        event = Event.objects.get(id=response.json()["id"])
        assert event.event_type == EventType.OFFICIAL
        rsvp_users = [rsvp.user for rsvp in event.rsvps.select_related("user").all()]
        assert sum(1 for u in rsvp_users if u.is_member) == 3
        assert sum(1 for u in rsvp_users if not u.is_member) == 2

    def test_non_member_going_ignored_without_official(
        self, api_client, auth_headers, monkeypatch
    ):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={
                "going_count": 2,
                "non_member_going_count": 3,
                "maybe_count": 0,
                "cant_go_count": 0,
            },
            content_type="application/json",
            **auth_headers,
        )
        event = Event.objects.get(id=response.json()["id"])
        rsvp_users = [rsvp.user for rsvp in event.rsvps.select_related("user").all()]
        assert all(u.is_member for u in rsvp_users)
        assert len(rsvp_users) == 2

    def test_filler_pool_reused_before_creating_new_users(
        self, api_client, auth_headers, monkeypatch, test_user
    ):
        from users.models import User

        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        before = User.objects.filter(is_member=True).count()
        response = api_client.post(
            "/api/community/dev/test-events/",
            data={
                "going_count": 1,
                "maybe_count": 0,
                "cant_go_count": 0,
                "invited_count": 0,
                "cohost_count": 0,
                "invited_cohost_count": 0,
            },
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        after = User.objects.filter(is_member=True).count()
        # test_user + auth_headers' user are already members in the pool, so the
        # single filler should reuse one of them rather than always creating new.
        assert after - before <= 1
