"""Calendar list must not hydrate every RSVP/invitee or presign photos."""

import io

import pytest
from community._event_helpers import _event_out, load_event_with_stats_prefetch
from community.models import Event, EventRSVP, PageVisibility, RSVPStatus
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from ninja_jwt.tokens import RefreshToken
from PIL import Image
from users.models import User

from tests.conftest import future_iso


def _user(phone: str, name: str) -> User:
    return User.objects.create_user(
        phone_number=phone,
        password="Testpass123!",
        first_name=name,
        last_name="",
    )


def _image(name: str = "test.jpg") -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", (20, 20)).save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


def _spy_inits(monkeypatch, model):
    count = {"n": 0}
    orig = model.__init__

    def _spy(self, *args, **kwargs):
        count["n"] += 1
        orig(self, *args, **kwargs)

    monkeypatch.setattr(model, "__init__", _spy)
    return count


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

        instantiated = _spy_inits(monkeypatch, EventRSVP)

        response = api_client.get("/api/community/events/", **auth_headers)
        assert response.status_code == 200
        row = next(e for e in response.json() if e["id"] == str(event.id))
        assert row["attending_count"] == 13  # 12 going, first has plus-one
        assert row["waitlisted_count"] == 2
        assert row["invited_count"] == 0
        assert instantiated["n"] == 0

    def test_list_events_does_not_presign_photos(self, api_client, test_user, auth_headers):
        test_user.profile_photo = _image("creator.jpg")
        test_user.save()
        cohost = _user("+14155550002", "Co")
        cohost.profile_photo = _image("cohost.jpg")
        cohost.save()
        event = Event.objects.create(
            title="Photo Skip",
            start_datetime=future_iso(days=4),
            created_by=test_user,
            photo=_image("event.jpg"),
        )
        event.co_hosts.add(cohost)

        response = api_client.get("/api/community/events/", **auth_headers)
        assert response.status_code == 200
        row = next(e for e in response.json() if e["title"] == "Photo Skip")
        assert row["photo_url"] == ""
        assert row["created_by_photo_url"] == ""
        assert row["co_host_photo_urls"] == []

        detail = api_client.get(f"/api/community/events/{event.id}/", **auth_headers)
        assert detail.status_code == 200
        body = detail.json()
        assert body["photo_url"]
        assert body["created_by_photo_url"]
        assert any(url for url in body["co_host_photo_urls"])

    def test_list_my_rsvp_still_uses_viewer_row(self, api_client, test_user, auth_headers):
        event = Event.objects.create(
            title="My RSVP",
            start_datetime=future_iso(days=6),
            rsvp_enabled=True,
            created_by=test_user,
        )
        EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.MAYBE)
        response = api_client.get("/api/community/events/", **auth_headers)
        assert response.status_code == 200
        row = next(e for e in response.json() if e["id"] == str(event.id))
        assert row["my_rsvp"] == RSVPStatus.MAYBE

    def test_list_hides_invite_only_events(self, api_client, test_user, auth_headers):
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

        instantiated = _spy_inits(monkeypatch, EventRSVP)
        response = api_client.get(f"/api/community/events/{event.id}/", **headers)
        assert response.status_code == 200
        body = response.json()
        assert body["attending_count"] == 10
        assert body["guests"] == []
        assert body["invited_user_ids"] == []
        assert body["invited_count"] == 0
        assert instantiated["n"] == 0

    def test_detail_attendee_does_not_receive_invited_count(
        self, api_client, test_user, auth_headers
    ):
        event = Event.objects.create(
            title="Attendee Detail",
            start_datetime=future_iso(days=13),
            rsvp_enabled=True,
            created_by=test_user,
        )
        EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)
        event.invited_users.add(_user("+14155556400", "Invitee"))
        attendee = _user("+14155556401", "Going")
        EventRSVP.objects.create(event=event, user=attendee, status=RSVPStatus.ATTENDING)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(attendee).access_token}"}
        response = api_client.get(f"/api/community/events/{event.id}/", **headers)
        assert response.status_code == 200
        body = response.json()
        assert len(body["guests"]) >= 1
        assert body["invited_user_ids"] == []
        assert body["invited_count"] == 0

    def test_detail_host_receives_invited_count(self, api_client, test_user, auth_headers):
        event = Event.objects.create(
            title="Host Invites",
            start_datetime=future_iso(days=14),
            rsvp_enabled=True,
            created_by=test_user,
        )
        invitees = [_user(f"+141555565{i:02d}", f"HInv{i}") for i in range(4)]
        event.invited_users.add(*invitees)
        response = api_client.get(f"/api/community/events/{event.id}/", **auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["invited_count"] == 4
        assert set(body["invited_user_ids"]) == {str(u.id) for u in invitees}

    def test_invite_only_detail_does_not_hydrate_invitees(self, api_client, monkeypatch):
        creator = _user("+14155556000", "Host")
        event = Event.objects.create(
            title="Private",
            start_datetime=future_iso(days=9),
            visibility=PageVisibility.INVITE_ONLY,
            created_by=creator,
        )
        invitees = [_user(f"+141555561{i:02d}", f"Inv{i}") for i in range(8)]
        event.invited_users.add(*invitees)
        invitee_pks = {u.pk for u in invitees}

        stranger = _user("+14155556200", "Stranger")
        headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(stranger).access_token}"}

        hydrated = {"n": 0}
        orig = User.__init__

        def _spy(self, *args, **kwargs):
            orig(self, *args, **kwargs)
            if getattr(self, "pk", None) in invitee_pks:
                hydrated["n"] += 1

        monkeypatch.setattr(User, "__init__", _spy)
        response = api_client.get(f"/api/community/events/{event.id}/", **headers)
        assert response.status_code == 403
        assert hydrated["n"] == 0

    def test_event_out_reuses_prefetched_rsvps(self, test_user):
        event = Event.objects.create(
            title="Prefetch Reuse",
            start_datetime=future_iso(days=12),
            rsvp_enabled=True,
            created_by=test_user,
        )
        for i in range(8):
            EventRSVP.objects.create(
                event=event,
                user=_user(f"+141555563{i:02d}", f"G{i}"),
                status=RSVPStatus.ATTENDING,
            )
        loaded = load_event_with_stats_prefetch(event.id)
        with CaptureQueriesContext(connection) as ctx:
            out = _event_out(loaded, test_user)
        rsvp_sql = [q["sql"] for q in ctx.captured_queries if "community_eventrsvp" in q["sql"]]
        assert out.attending_count == 8
        assert len(out.guests) == 8
        assert rsvp_sql == []
