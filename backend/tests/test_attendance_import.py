import pytest
from community.models import AttendanceStatus, Event, EventRSVP, EventType, RSVPStatus
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import Role, User
from users.permissions import PermissionKey


def _auth(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


def _csv(rows: list[str]) -> SimpleUploadedFile:
    body = "Name,Status,Checked in,RSVP date\n" + "\n".join(rows)
    return SimpleUploadedFile("partiful.csv", body.encode(), content_type="text/csv")


@pytest.fixture
def events_admin(db):
    admin = User.objects.create_user(
        phone_number="+12025552000", password="x", first_name="Admin", is_member=True
    )
    role = Role.objects.create(name="events_admin", permissions=[PermissionKey.MANAGE_EVENTS])
    admin.roles.add(role)
    return admin


@pytest.fixture
def plain_member(db):
    return User.objects.create_user(
        phone_number="+12025552001", password="x", first_name="Plain", is_member=True
    )


@pytest.fixture
def alice(db):
    return User.objects.create_user(
        phone_number="+12025552002",
        password="x",
        first_name="Alice",
        last_name="Smith",
        is_member=True,
    )


@pytest.fixture
def bob(db):
    return User.objects.create_user(
        phone_number="+12025552003", password="x", first_name="Bob", is_member=True
    )


@pytest.fixture
def past_event(db, events_admin):
    return Event.objects.create(
        title="Past Potluck",
        start_datetime=timezone.now() - timezone.timedelta(days=30),
        created_by=events_admin,
    )


@pytest.mark.django_db
class TestPreviewEndpoint:
    def test_forbidden_without_permission(self, api_client, plain_member):
        response = api_client.post(
            "/api/community/events/attendance-import/preview/",
            {"csv_file": _csv(["Alice Smith,Going,Yes,2026-01-01 00:00:00"])},
            **_auth(plain_member),
        )
        assert response.status_code == 403

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.post(
            "/api/community/events/attendance-import/preview/",
            {"csv_file": _csv(["Alice Smith,Going,Yes,2026-01-01 00:00:00"])},
        )
        assert response.status_code == 401

    def test_exact_match_goes_to_matched(self, api_client, events_admin, alice):
        response = api_client.post(
            "/api/community/events/attendance-import/preview/",
            {"csv_file": _csv(["Alice Smith,Going,Yes,2026-01-01 00:00:00"])},
            **_auth(events_admin),
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["matched"]) == 1
        assert body["matched"][0]["matched_user_id"] == str(alice.id)
        assert body["needs_review"] == []

    def test_match_is_case_insensitive(self, api_client, events_admin, alice):
        response = api_client.post(
            "/api/community/events/attendance-import/preview/",
            {"csv_file": _csv(["alice smith,Going,Yes,2026-01-01 00:00:00"])},
            **_auth(events_admin),
        )
        body = response.json()
        assert len(body["matched"]) == 1

    def test_unmatched_name_goes_to_needs_review(self, api_client, events_admin):
        response = api_client.post(
            "/api/community/events/attendance-import/preview/",
            {"csv_file": _csv(["Nobody Here,Maybe,Yes,2026-01-01 00:00:00"])},
            **_auth(events_admin),
        )
        body = response.json()
        assert body["matched"] == []
        assert len(body["needs_review"]) == 1
        row = body["needs_review"][0]
        assert row["raw_name"] == "Nobody Here"
        assert row["candidates"] == []

    def test_not_checked_in_rows_are_dropped(self, api_client, events_admin, alice):
        response = api_client.post(
            "/api/community/events/attendance-import/preview/",
            {
                "csv_file": _csv(
                    [
                        "Alice Smith,Going,No,2026-01-01 00:00:00",
                        "Nobody Here,Maybe,No,2026-01-01 00:00:00",
                    ]
                )
            },
            **_auth(events_admin),
        )
        body = response.json()
        assert body["matched"] == []
        assert body["needs_review"] == []

    def test_ambiguous_name_goes_to_needs_review_with_candidates(self, api_client, events_admin):
        User.objects.create_user(
            phone_number="+12025552010",
            password="x",
            first_name="Sam",
            nickname="Sam",
            is_member=True,
        )
        User.objects.create_user(
            phone_number="+12025552011",
            password="x",
            first_name="Sammy",
            nickname="Sam",
            is_member=True,
        )
        response = api_client.post(
            "/api/community/events/attendance-import/preview/",
            {"csv_file": _csv(["Sam,Going,Yes,2026-01-01 00:00:00"])},
            **_auth(events_admin),
        )
        body = response.json()
        assert body["matched"] == []
        assert len(body["needs_review"]) == 1
        assert len(body["needs_review"][0]["candidates"]) == 2

    def test_no_event_id_leaves_has_existing_rsvp_false(self, api_client, events_admin, alice):
        response = api_client.post(
            "/api/community/events/attendance-import/preview/",
            {"csv_file": _csv(["Alice Smith,Going,Yes,2026-01-01 00:00:00"])},
            **_auth(events_admin),
        )
        body = response.json()
        assert body["matched"][0]["has_existing_rsvp"] is False

    def test_event_id_flags_rows_with_existing_rsvp(
        self, api_client, events_admin, past_event, alice
    ):
        EventRSVP.objects.create(event=past_event, user=alice, status=RSVPStatus.ATTENDING)
        response = api_client.post(
            f"/api/community/events/attendance-import/preview/?event_id={past_event.id}",
            {"csv_file": _csv(["Alice Smith,Going,Yes,2026-01-01 00:00:00"])},
            **_auth(events_admin),
        )
        body = response.json()
        assert body["matched"][0]["has_existing_rsvp"] is True

    def test_malformed_csv_rejected(self, api_client, events_admin):
        bad = SimpleUploadedFile(
            "bad.csv", b"not,the,right,headers\n1,2,3,4", content_type="text/csv"
        )
        response = api_client.post(
            "/api/community/events/attendance-import/preview/",
            {"csv_file": bad},
            **_auth(events_admin),
        )
        assert response.status_code == 400

    def test_empty_csv_rejected(self, api_client, events_admin):
        empty = SimpleUploadedFile(
            "empty.csv", b"Name,Status,Checked in,RSVP date\n", content_type="text/csv"
        )
        response = api_client.post(
            "/api/community/events/attendance-import/preview/",
            {"csv_file": empty},
            **_auth(events_admin),
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestCommitEndpoint:
    def _row(self, **overrides):
        row = {
            "row_index": 0,
            "raw_name": "Alice Smith",
            "partiful_status": "Going",
            "checked_in": True,
            "user_id": None,
            "skip": False,
        }
        row.update(overrides)
        return row

    def test_forbidden_without_permission(self, api_client, plain_member, past_event):
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {"event_id": str(past_event.id), "rows": []},
            content_type="application/json",
            **_auth(plain_member),
        )
        assert response.status_code == 403

    def test_checked_in_row_marks_attended(self, api_client, events_admin, past_event, alice):
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {
                "event_id": str(past_event.id),
                "rows": [self._row(user_id=str(alice.id), checked_in=True)],
            },
            content_type="application/json",
            **_auth(events_admin),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["created_count"] == 1
        rsvp = EventRSVP.objects.get(event=past_event, user=alice)
        assert rsvp.attendance == AttendanceStatus.ATTENDED
        assert rsvp.status == RSVPStatus.ATTENDING

    def test_going_but_not_checked_in_marks_no_show(
        self, api_client, events_admin, past_event, alice
    ):
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {
                "event_id": str(past_event.id),
                "rows": [
                    self._row(user_id=str(alice.id), checked_in=False, partiful_status="Going")
                ],
            },
            content_type="application/json",
            **_auth(events_admin),
        )
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=past_event, user=alice)
        assert rsvp.attendance == AttendanceStatus.DIDNT_GO
        assert rsvp.status == RSVPStatus.ATTENDING

    def test_maybe_not_checked_in_leaves_attendance_unknown(
        self, api_client, events_admin, past_event, alice
    ):
        api_client.post(
            "/api/community/events/attendance-import/commit/",
            {
                "event_id": str(past_event.id),
                "rows": [
                    self._row(user_id=str(alice.id), checked_in=False, partiful_status="Maybe")
                ],
            },
            content_type="application/json",
            **_auth(events_admin),
        )
        rsvp = EventRSVP.objects.get(event=past_event, user=alice)
        assert rsvp.attendance == AttendanceStatus.UNKNOWN

    def test_skip_row_is_not_written(self, api_client, events_admin, past_event, alice):
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {
                "event_id": str(past_event.id),
                "rows": [self._row(user_id=str(alice.id), skip=True)],
            },
            content_type="application/json",
            **_auth(events_admin),
        )
        body = response.json()
        assert body["skipped_count"] == 1
        assert not EventRSVP.objects.filter(event=past_event, user=alice).exists()

    def test_unresolved_row_is_rejected(self, api_client, events_admin, past_event):
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {"event_id": str(past_event.id), "rows": [self._row(user_id=None, skip=False)]},
            content_type="application/json",
            **_auth(events_admin),
        )
        assert response.status_code == 400
        assert response.json()["detail"][0]["code"] == "attendance_import.ambiguous_user_pick"

    def test_existing_rsvp_is_updated_not_duplicated(
        self, api_client, events_admin, past_event, alice
    ):
        EventRSVP.objects.create(
            event=past_event,
            user=alice,
            status=RSVPStatus.MAYBE,
            attendance=AttendanceStatus.UNKNOWN,
        )
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {
                "event_id": str(past_event.id),
                "rows": [self._row(user_id=str(alice.id), checked_in=True)],
            },
            content_type="application/json",
            **_auth(events_admin),
        )
        body = response.json()
        assert body["updated_count"] == 1
        assert body["created_count"] == 0
        assert EventRSVP.objects.filter(event=past_event, user=alice).count() == 1

    def test_creates_event_when_no_event_id_given(self, api_client, events_admin, alice):
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {
                "event_title": "Legacy Mixer",
                "event_date": "2025-06-13",
                "rows": [self._row(user_id=str(alice.id), checked_in=True)],
            },
            content_type="application/json",
            **_auth(events_admin),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["event_title"] == "Legacy Mixer"
        event = Event.objects.get(id=body["event_id"])
        assert event.title == "Legacy Mixer"
        assert EventRSVP.objects.filter(event=event, user=alice).exists()

    def test_created_event_is_flagged_as_partiful_import(self, api_client, events_admin, alice):
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {
                "event_title": "Legacy Mixer",
                "event_date": "2025-06-13",
                "rows": [self._row(user_id=str(alice.id), checked_in=True)],
            },
            content_type="application/json",
            **_auth(events_admin),
        )
        assert response.status_code == 200
        event = Event.objects.get(id=response.json()["event_id"])
        assert event.is_partiful_import is True

    def test_existing_event_is_not_flagged_by_import(
        self, api_client, events_admin, past_event, alice
    ):
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {
                "event_id": str(past_event.id),
                "rows": [self._row(user_id=str(alice.id), checked_in=True)],
            },
            content_type="application/json",
            **_auth(events_admin),
        )
        assert response.status_code == 200
        past_event.refresh_from_db()
        assert past_event.is_partiful_import is False

    def test_defaults_to_community_event_type(self, api_client, events_admin, alice):
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {
                "event_title": "Legacy Mixer",
                "event_date": "2025-06-13",
                "rows": [self._row(user_id=str(alice.id), checked_in=True)],
            },
            content_type="application/json",
            **_auth(events_admin),
        )
        event = Event.objects.get(id=response.json()["event_id"])
        assert event.event_type == EventType.COMMUNITY

    @pytest.mark.parametrize("event_type", [EventType.OFFICIAL, EventType.CLUB])
    def test_creates_event_with_requested_qualifying_type(
        self, api_client, events_admin, alice, event_type
    ):
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {
                "event_title": "Club Mixer",
                "event_date": "2025-06-13",
                "event_type": event_type,
                "rows": [self._row(user_id=str(alice.id), checked_in=True)],
            },
            content_type="application/json",
            **_auth(events_admin),
        )
        assert response.status_code == 200
        event = Event.objects.get(id=response.json()["event_id"])
        assert event.event_type == event_type

    def test_invalid_event_type_rejected(self, api_client, events_admin, alice):
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {
                "event_title": "Legacy Mixer",
                "event_date": "2025-06-13",
                "event_type": "not_a_real_type",
                "rows": [self._row(user_id=str(alice.id), checked_in=True)],
            },
            content_type="application/json",
            **_auth(events_admin),
        )
        assert response.status_code == 400
        assert response.json()["detail"][0]["code"] == "attendance_import.invalid_event_type"

    def test_missing_event_and_title_rejected(self, api_client, events_admin, alice):
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {"rows": [self._row(user_id=str(alice.id))]},
            content_type="application/json",
            **_auth(events_admin),
        )
        assert response.status_code == 400

    def test_nonexistent_event_id_404s(self, api_client, events_admin, alice):
        response = api_client.post(
            "/api/community/events/attendance-import/commit/",
            {
                "event_id": "00000000-0000-0000-0000-000000000000",
                "rows": [self._row(user_id=str(alice.id))],
            },
            content_type="application/json",
            **_auth(events_admin),
        )
        assert response.status_code == 404

    def test_appears_in_attendance_report_after_commit(
        self, api_client, events_admin, past_event, alice, bob
    ):
        api_client.post(
            "/api/community/events/attendance-import/commit/",
            {
                "event_id": str(past_event.id),
                "rows": [
                    self._row(user_id=str(alice.id), checked_in=True),
                    self._row(user_id=str(bob.id), checked_in=False, partiful_status="Going"),
                ],
            },
            content_type="application/json",
            **_auth(events_admin),
        )
        response = api_client.get("/api/community/events/attendance-report/", **_auth(events_admin))
        row = next(r for r in response.json()["events"] if r["event_id"] == str(past_event.id))
        assert row["attended_count"] == 1
        assert row["no_show_count"] == 1


@pytest.mark.django_db
class TestEventOptionsEndpoint:
    def test_forbidden_without_permission(self, api_client, plain_member):
        response = api_client.get(
            "/api/community/events/attendance-import/events/", **_auth(plain_member)
        )
        assert response.status_code == 403

    def test_lists_events_matching_query(self, api_client, events_admin, past_event):
        response = api_client.get(
            "/api/community/events/attendance-import/events/",
            {"q": "potluck"},
            **_auth(events_admin),
        )
        assert response.status_code == 200
        titles = [e["title"] for e in response.json()]
        assert "Past Potluck" in titles
