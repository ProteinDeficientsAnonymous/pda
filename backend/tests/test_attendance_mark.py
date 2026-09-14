import pytest
from community.models import (
    AttendanceStatus,
    Event,
    EventRSVP,
    EventType,
    PageVisibility,
    RSVPStatus,
)
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import Role, User
from users.permissions import PermissionKey

URL = "/api/community/events/attendance-mark/"


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.fixture
def members_admin(db):
    admin = User.objects.create_user(
        phone_number="+12025553000", password="x", first_name="Admin", is_member=True
    )
    role = Role.objects.create(name="mark_admin", permissions=[PermissionKey.MANAGE_USERS])
    admin.roles.add(role)
    return admin


@pytest.fixture
def events_only_admin(db):
    admin = User.objects.create_user(
        phone_number="+12025553004", password="x", first_name="Eventy", is_member=True
    )
    role = Role.objects.create(name="events_only", permissions=[PermissionKey.MANAGE_EVENTS])
    admin.roles.add(role)
    return admin


@pytest.fixture
def plain_member(db):
    return User.objects.create_user(
        phone_number="+12025553001", password="x", first_name="Plain", is_member=True
    )


@pytest.fixture
def alice(db):
    return User.objects.create_user(
        phone_number="+12025553002", password="x", first_name="Alice", is_member=True
    )


@pytest.fixture
def bob(db):
    return User.objects.create_user(
        phone_number="+12025553003", password="x", first_name="Bob", is_member=True
    )


@pytest.fixture
def past_event(db, members_admin):
    return Event.objects.create(
        title="Past Potluck",
        start_datetime=timezone.now() - timezone.timedelta(days=30),
        event_type=EventType.CLUB,
        created_by=members_admin,
    )


def _post(api_client, user, payload):
    return api_client.post(URL, payload, content_type="application/json", **_auth(user))


@pytest.mark.django_db
class TestPermissions:
    def test_forbidden_without_manage_users(self, api_client, plain_member, alice, past_event):
        resp = _post(
            api_client,
            plain_member,
            {"event_id": str(past_event.id), "user_ids": [str(alice.id)]},
        )
        assert resp.status_code == 403

    def test_manage_events_alone_is_not_enough(
        self, api_client, events_only_admin, alice, past_event
    ):
        resp = _post(
            api_client,
            events_only_admin,
            {"event_id": str(past_event.id), "user_ids": [str(alice.id)]},
        )
        assert resp.status_code == 403

    def test_event_picker_is_open_to_both_permissions(
        self, api_client, members_admin, events_only_admin, past_event
    ):
        url = "/api/community/events/attendance-import/events/"
        for user in (members_admin, events_only_admin):
            resp = api_client.get(url, **_auth(user))
            assert resp.status_code == 200
            assert any(e["id"] == str(past_event.id) for e in resp.json())


@pytest.mark.django_db
class TestExistingEvent:
    def test_marks_every_selected_member_attended(
        self, api_client, members_admin, alice, bob, past_event
    ):
        resp = _post(
            api_client,
            members_admin,
            {"event_id": str(past_event.id), "user_ids": [str(alice.id), str(bob.id)]},
        )

        assert resp.status_code == 200
        assert resp.json()["created_count"] == 2
        for user in (alice, bob):
            rsvp = EventRSVP.objects.get(event=past_event, user=user)
            assert rsvp.attendance == AttendanceStatus.ATTENDED
            assert rsvp.status == RSVPStatus.ATTENDING

    def test_remarking_updates_instead_of_duplicating(
        self, api_client, members_admin, alice, past_event
    ):
        EventRSVP.objects.create(
            event=past_event,
            user=alice,
            status=RSVPStatus.MAYBE,
            attendance=AttendanceStatus.DIDNT_GO,
        )

        resp = _post(
            api_client,
            members_admin,
            {"event_id": str(past_event.id), "user_ids": [str(alice.id)]},
        )

        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 1
        assert EventRSVP.objects.filter(event=past_event, user=alice).count() == 1
        assert (
            EventRSVP.objects.get(event=past_event, user=alice).attendance
            == AttendanceStatus.ATTENDED
        )

    def test_unknown_event_404s(self, api_client, members_admin, alice):
        resp = _post(
            api_client,
            members_admin,
            {
                "event_id": "00000000-0000-0000-0000-000000000000",
                "user_ids": [str(alice.id)],
            },
        )
        assert resp.status_code == 404


@pytest.mark.django_db
class TestLegacyEventCreation:
    def test_creates_a_legacy_event_kept_off_the_calendar(self, api_client, members_admin, alice):
        resp = _post(
            api_client,
            members_admin,
            {
                "event_title": "Summer Potluck 2023",
                "event_date": "2023-07-04",
                "event_type": EventType.CLUB,
                "user_ids": [str(alice.id)],
            },
        )

        assert resp.status_code == 200
        event = Event.objects.get(id=resp.json()["event_id"])
        assert event.is_legacy is True
        assert event.is_partiful_import is False
        assert event.rsvp_enabled is False
        assert event.visibility == PageVisibility.MEMBERS_ONLY
        assert event.event_type == EventType.CLUB
        assert event.start_datetime.date().isoformat() == "2023-07-04"

    def test_legacy_attendance_counts_toward_the_attendance_clock(
        self, api_client, members_admin, alice
    ):
        from community._attendance_clock import last_qualifying_attendance_date

        _post(
            api_client,
            members_admin,
            {
                "event_title": "Summer Potluck 2023",
                "event_date": "2023-07-04",
                "event_type": EventType.CLUB,
                "user_ids": [str(alice.id)],
            },
        )

        assert last_qualifying_attendance_date(alice).isoformat() == "2023-07-04"

    def test_title_and_date_required_without_event_id(self, api_client, members_admin, alice):
        resp = _post(api_client, members_admin, {"user_ids": [str(alice.id)]})
        assert resp.status_code == 400

    def test_rejects_unsupported_event_type(self, api_client, members_admin, alice):
        resp = _post(
            api_client,
            members_admin,
            {
                "event_title": "Summer Potluck 2023",
                "event_date": "2023-07-04",
                "event_type": "nonsense",
                "user_ids": [str(alice.id)],
            },
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestSelection:
    def test_rejects_an_empty_selection(self, api_client, members_admin, past_event):
        resp = _post(api_client, members_admin, {"event_id": str(past_event.id), "user_ids": []})
        assert resp.status_code == 400

    def test_skips_ids_that_are_not_users(self, api_client, members_admin, alice, past_event):
        resp = _post(
            api_client,
            members_admin,
            {
                "event_id": str(past_event.id),
                "user_ids": [str(alice.id), "00000000-0000-0000-0000-000000000000"],
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["created_count"] == 1
        assert body["skipped_count"] == 1


@pytest.mark.django_db
class TestLegacyEventInEventList:
    def test_event_list_flags_legacy_events(self, api_client, members_admin):
        event = Event.objects.create(
            title="Legacy Potluck",
            start_datetime=timezone.now() - timezone.timedelta(days=400),
            created_by=members_admin,
            is_legacy=True,
        )

        resp = api_client.get("/api/community/events/", **_auth(members_admin))

        assert resp.status_code == 200
        row = next(e for e in resp.json() if e["id"] == str(event.id))
        assert row["is_legacy"] is True
