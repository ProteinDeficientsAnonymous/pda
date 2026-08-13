"""Calendar list must not hydrate every RSVP/invitee or presign photos."""

import pytest
from community.models import Event, EventRSVP, PageVisibility, RSVPStatus
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso


def _user(phone: str, name: str) -> User:
    return User.objects.create_user(
        phone_number=phone,
        password="Testpass123!",
        first_name=name,
        last_name="",
    )


@pytest.mark.django_db
class TestListEventsMemory:
    def test_list_events_does_not_instantiate_every_rsvp(
        self, api_client, test_user, auth_headers, monkeypatch
    ):
        event = Event.objects.create(
            title="Packed Calendar Event",
            start_datetime=future_iso(days=10),
            rsvp_enabled=True,
            max_attendees=50,
            created_by=test_user,
        )
        guests = []
        for i in range(12):
            guest = _user(f"+14155557{i:03d}", f"Guest{i}")
            guests.append(guest)
            EventRSVP.objects.create(
                event=event,
                user=guest,
                status=RSVPStatus.ATTENDING,
                has_plus_one=(i == 0),
            )
        waitlisted = _user("+14155557999", "Wait")
        EventRSVP.objects.create(
            event=event, user=waitlisted, status=RSVPStatus.WAITLISTED, has_plus_one=True
        )
        extras = [_user(f"+14155558{i:03d}", f"Inv{i}") for i in range(8)]
        event.invited_users.add(guests[0], *extras)

        instantiated = {"n": 0}
        orig = EventRSVP.__init__

        def _spy(self, *args, **kwargs):
            instantiated["n"] += 1
            orig(self, *args, **kwargs)

        monkeypatch.setattr(EventRSVP, "__init__", _spy)

        response = api_client.get("/api/community/events/", **auth_headers)
        assert response.status_code == 200
        row = next(e for e in response.json() if e["id"] == str(event.id))
        assert row["attending_count"] == 13  # 12 going, first has plus-one
        assert row["waitlisted_count"] == 2
        assert row["invited_count"] == 9
        assert instantiated["n"] <= 1

    def test_list_events_does_not_presign_photos(self, api_client, test_user, auth_headers):
        Event.objects.create(
            title="Photo Skip",
            start_datetime=future_iso(days=4),
            created_by=test_user,
        )
        response = api_client.get("/api/community/events/", **auth_headers)
        assert response.status_code == 200
        row = next(e for e in response.json() if e["title"] == "Photo Skip")
        assert row["photo_url"] == ""
        assert row["created_by_photo_url"] == ""
        assert row["co_host_photo_urls"] == []

    def test_list_my_rsvp_still_uses_viewer_row(self, api_client, test_user, auth_headers):
        event = Event.objects.create(
            title="My RSVP",
            start_datetime=future_iso(days=6),
            rsvp_enabled=True,
            created_by=test_user,
        )
        EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.MAYBE)
        response = api_client.get("/api/community/events/", **auth_headers)
        row = next(e for e in response.json() if e["id"] == str(event.id))
        assert row["my_rsvp"] == RSVPStatus.MAYBE

    def test_list_hides_invite_only_without_loading_invitees(
        self, api_client, test_user, auth_headers
    ):
        creator = _user("+14155557000", "Host")
        hidden = Event.objects.create(
            title="Secret",
            start_datetime=future_iso(days=8),
            visibility=PageVisibility.INVITE_ONLY,
            created_by=creator,
        )
        hidden.invited_users.add(_user("+14155557001", "Invitee"))
        response = api_client.get("/api/community/events/", **auth_headers)
        assert response.status_code == 200
        assert all(e["id"] != str(hidden.id) for e in response.json())


@pytest.mark.django_db
class TestGetEventMemory:
    def test_detail_skips_rsvp_hydration_when_guests_hidden(
        self, api_client, test_user, monkeypatch
    ):
        event = Event.objects.create(
            title="Busy Detail",
            start_datetime=future_iso(days=11),
            rsvp_enabled=True,
            created_by=test_user,
        )
        guests = []
        for i in range(10):
            guest = _user(f"+14155559{i:03d}", f"DGuest{i}")
            guests.append(guest)
            EventRSVP.objects.create(event=event, user=guest, status=RSVPStatus.ATTENDING)
        event.invited_users.add(guests[0])

        viewer = _user("+14155559111", "Stranger")
        headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(viewer).access_token}"}

        instantiated = {"n": 0}
        orig = EventRSVP.__init__

        def _spy(self, *args, **kwargs):
            instantiated["n"] += 1
            orig(self, *args, **kwargs)

        monkeypatch.setattr(EventRSVP, "__init__", _spy)
        response = api_client.get(f"/api/community/events/{event.id}/", **headers)
        assert response.status_code == 200
        body = response.json()
        assert body["attending_count"] == 10
        assert body["guests"] == []
        assert body["invited_user_ids"] == []
        assert instantiated["n"] <= 1
