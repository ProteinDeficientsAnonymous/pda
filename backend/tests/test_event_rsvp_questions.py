"""Tests for per-event RSVP questions and answers on RSVP."""

import pytest
from community._validation import Code
from community.models import Event, EventRSVP, EventRsvpQuestion, RSVPStatus
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests._asserts import assert_error_code
from tests.conftest import future_iso


@pytest.fixture
def rsvp_event(db, test_user):
    return Event.objects.create(
        title="Questions Event",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        rsvp_enabled=True,
        created_by=test_user,
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        phone_number="+12025550999",
        password="otherpass",
        first_name="Other",
        last_name="Guest",
    )


@pytest.fixture
def other_headers(other_user):
    refresh = RefreshToken.for_user(other_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


def _create_question(api_client, auth_headers, event_id, **overrides):
    payload = {
        "label": "how are you getting there?",
        "field_type": "dropdown",
        "options": ["driving", "transit"],
        "required": True,
        **overrides,
    }
    return api_client.post(
        f"/api/community/events/{event_id}/rsvp-questions/",
        payload,
        content_type="application/json",
        **auth_headers,
    )


@pytest.mark.django_db
class TestEventRsvpQuestionCrud:
    def test_host_can_create_question(self, api_client, auth_headers, rsvp_event):
        response = _create_question(api_client, auth_headers, rsvp_event.id)
        assert response.status_code == 201
        data = response.json()
        assert data["label"] == "how are you getting there?"
        assert data["field_type"] == "dropdown"
        assert data["options"] == ["driving", "transit"]
        assert data["required"] is True
        assert data["display_order"] == 0
        assert EventRsvpQuestion.objects.filter(event=rsvp_event).count() == 1

    def test_non_host_cannot_create_question(self, api_client, other_headers, rsvp_event):
        response = _create_question(api_client, other_headers, rsvp_event.id)
        assert response.status_code == 403
        assert_error_code(response, Code.Event.PERM_DENIED)

    def test_create_choice_requires_options(self, api_client, auth_headers, rsvp_event):
        response = _create_question(api_client, auth_headers, rsvp_event.id, options=[])
        assert response.status_code == 400
        assert_error_code(response, Code.Event.RSVP_QUESTION_OPTIONS_REQUIRED)

    def test_event_out_includes_questions(self, api_client, auth_headers, rsvp_event):
        _create_question(api_client, auth_headers, rsvp_event.id)
        response = api_client.get(f"/api/community/events/{rsvp_event.id}/", **auth_headers)
        assert response.status_code == 200
        questions = response.json()["rsvp_questions"]
        assert len(questions) == 1
        assert questions[0]["label"] == "how are you getting there?"

    def test_host_can_update_and_delete(self, api_client, auth_headers, rsvp_event):
        created = _create_question(api_client, auth_headers, rsvp_event.id).json()
        qid = created["id"]
        patched = api_client.patch(
            f"/api/community/events/{rsvp_event.id}/rsvp-questions/{qid}/",
            {
                "label": "transport?",
                "field_type": "textarea",
                "options": [],
                "required": False,
            },
            content_type="application/json",
            **auth_headers,
        )
        assert patched.status_code == 200
        assert patched.json()["label"] == "transport?"
        assert patched.json()["field_type"] == "textarea"

        deleted = api_client.delete(
            f"/api/community/events/{rsvp_event.id}/rsvp-questions/{qid}/",
            **auth_headers,
        )
        assert deleted.status_code == 204
        assert EventRsvpQuestion.objects.filter(id=qid).count() == 0


@pytest.mark.django_db
class TestRsvpWithAnswers:
    def test_required_answer_blocks_attending(
        self, api_client, other_headers, auth_headers, rsvp_event
    ):
        q = _create_question(api_client, auth_headers, rsvp_event.id).json()
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.RSVP_ANSWER_REQUIRED)

        ok = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {
                "status": RSVPStatus.ATTENDING,
                "has_plus_one": False,
                "answers": {q["id"]: "driving"},
            },
            content_type="application/json",
            **other_headers,
        )
        assert ok.status_code == 200
        rsvp = EventRSVP.objects.get(event=rsvp_event)
        assert rsvp.answers[q["id"]]["answer"] == "driving"
        assert ok.json()["my_rsvp_answers"][q["id"]]["answer"] == "driving"

    def test_cant_go_skips_required_answers(
        self, api_client, other_headers, auth_headers, rsvp_event
    ):
        _create_question(api_client, auth_headers, rsvp_event.id)
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.CANT_GO, "has_plus_one": False},
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 200

    def test_invalid_option_rejected(self, api_client, other_headers, auth_headers, rsvp_event):
        q = _create_question(api_client, auth_headers, rsvp_event.id).json()
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {
                "status": RSVPStatus.MAYBE,
                "answers": {q["id"]: "helicopter"},
            },
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.RSVP_ANSWER_INVALID_OPTION)

    def test_host_sees_guest_answers_member_does_not(
        self, api_client, other_headers, auth_headers, rsvp_event, other_user
    ):
        q = _create_question(api_client, auth_headers, rsvp_event.id).json()
        assert (
            api_client.post(
                f"/api/community/events/{rsvp_event.id}/rsvp/",
                {
                    "status": RSVPStatus.ATTENDING,
                    "answers": {q["id"]: "transit"},
                },
                content_type="application/json",
                **other_headers,
            ).status_code
            == 200
        )

        host_view = api_client.get(f"/api/community/events/{rsvp_event.id}/", **auth_headers).json()
        host_guest = next(g for g in host_view["guests"] if g["user_id"] == str(other_user.pk))
        assert host_guest["answers"][q["id"]]["answer"] == "transit"

        member_view = api_client.get(
            f"/api/community/events/{rsvp_event.id}/", **other_headers
        ).json()
        member_guest = next(g for g in member_view["guests"] if g["user_id"] == str(other_user.pk))
        assert member_guest["answers"] == {}


@pytest.mark.django_db
class TestRsvpAnswerEdgeCases:
    def test_multiselect_comma_only_required_rejected(
        self, api_client, other_headers, auth_headers, rsvp_event
    ):
        q = _create_question(
            api_client,
            auth_headers,
            rsvp_event.id,
            field_type="multiselect",
            options=["a", "b"],
        ).json()
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "answers": {q["id"]: ",,,"}},
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.RSVP_ANSWER_REQUIRED)

    def test_option_with_comma_rejected(self, api_client, auth_headers, rsvp_event):
        response = _create_question(
            api_client,
            auth_headers,
            rsvp_event.id,
            options=["a, b", "c"],
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.RSVP_QUESTION_OPTION_NO_COMMA)

    def test_host_sees_guests_when_rsvp_disabled(
        self, api_client, other_headers, auth_headers, rsvp_event, other_user
    ):
        q = _create_question(api_client, auth_headers, rsvp_event.id).json()
        assert (
            api_client.post(
                f"/api/community/events/{rsvp_event.id}/rsvp/",
                {"status": RSVPStatus.ATTENDING, "answers": {q["id"]: "driving"}},
                content_type="application/json",
                **other_headers,
            ).status_code
            == 200
        )
        rsvp_event.rsvp_enabled = False
        rsvp_event.save(update_fields=["rsvp_enabled"])
        host_view = api_client.get(f"/api/community/events/{rsvp_event.id}/", **auth_headers).json()
        assert len(host_view["guests"]) == 1
        assert host_view["guests"][0]["answers"][q["id"]]["answer"] == "driving"


@pytest.mark.unit
def test_reverse_migrate_join_question_types_maps_wire_values():
    import importlib

    migration = importlib.import_module(
        "community.migrations.0086_rsvp_questions_and_join_form_types"
    )
    reverse_migrate_join_question_types = migration.reverse_migrate_join_question_types

    class FakeQS:
        def __init__(self, rows):
            self.rows = rows

        def filter(self, **kwargs):
            key, value = next(iter(kwargs.items()))
            self.rows = [r for r in self.rows if r[key] == value]
            return self

        def update(self, **kwargs):
            for row in self.rows:
                row.update(kwargs)
            return len(self.rows)

    class FakeManager:
        def __init__(self, rows):
            self.rows = rows

        def filter(self, **kwargs):
            return FakeQS(list(self.rows)).filter(**kwargs)

    rows = [
        {"field_type": "dropdown"},
        {"field_type": "textarea"},
        {"field_type": "text"},
    ]

    class FakeApps:
        def get_model(self, _app, _name):
            class M:
                objects = FakeManager(rows)

            return M

    reverse_migrate_join_question_types(FakeApps(), None)
    assert rows[0]["field_type"] == "select"
    assert rows[1]["field_type"] == "text"
    assert rows[2]["field_type"] == "text"
