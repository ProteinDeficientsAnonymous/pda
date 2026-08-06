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


def _question_data(**overrides):
    return {
        "label": "how are you getting there?",
        "field_type": "select",
        "options": ["driving", "transit"],
        "required": True,
        **overrides,
    }


def _create_question(event, **overrides):
    question = EventRsvpQuestion.objects.create(event=event, **_question_data(**overrides))
    return {"id": str(question.id)}


def _replace_question(api_client, auth_headers, event_id, **overrides):
    return api_client.put(
        f"/api/community/events/{event_id}/rsvp-questions/",
        {"expected": [], "questions": [{"id": None, **_question_data(**overrides)}]},
        content_type="application/json",
        **auth_headers,
    )


@pytest.mark.django_db
def test_event_out_includes_questions(api_client, auth_headers, rsvp_event):
    _create_question(rsvp_event)
    response = api_client.get(f"/api/community/events/{rsvp_event.id}/", **auth_headers)
    assert response.status_code == 200
    questions = response.json()["rsvp_questions"]
    assert len(questions) == 1
    assert questions[0]["label"] == "how are you getting there?"


@pytest.mark.django_db
class TestRsvpWithAnswers:
    def test_required_answer_blocks_attending(
        self, api_client, other_headers, auth_headers, rsvp_event
    ):
        q = _create_question(rsvp_event)
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
        assert rsvp.questionnaire_responses[q["id"]]["answer"] == "driving"
        assert ok.json()["my_rsvp_answers"][q["id"]]["answer"] == "driving"

    def test_cant_go_skips_required_answers(
        self, api_client, other_headers, auth_headers, rsvp_event
    ):
        _create_question(rsvp_event)
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.CANT_GO, "has_plus_one": False},
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 200

    def test_invalid_option_rejected(self, api_client, other_headers, auth_headers, rsvp_event):
        q = _create_question(rsvp_event)
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
        q = _create_question(rsvp_event)
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
    def test_checkbox_comma_only_required_rejected(
        self, api_client, other_headers, auth_headers, rsvp_event
    ):
        q = _create_question(
            rsvp_event,
            field_type="checkbox",
            options=["a", "b"],
        )
        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "answers": {q["id"]: ",,,"}},
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.RSVP_ANSWER_REQUIRED)

    def test_checkbox_option_with_comma_rejected(self, api_client, auth_headers, rsvp_event):
        response = _replace_question(
            api_client,
            auth_headers,
            rsvp_event.id,
            field_type="checkbox",
            options=["a, b", "c"],
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.RSVP_QUESTION_OPTION_NO_COMMA)

    def test_select_option_with_comma_allowed(self, api_client, auth_headers, rsvp_event):
        response = _replace_question(
            api_client,
            auth_headers,
            rsvp_event.id,
            options=["yes, with a guest", "no"],
        )

        assert response.status_code == 200

    def test_choice_option_over_max_length_rejected(self, api_client, auth_headers, rsvp_event):
        response = _replace_question(
            api_client,
            auth_headers,
            rsvp_event.id,
            options=["x" * 201],
        )

        assert response.status_code == 422

    def test_answer_too_long_uses_question_label(
        self, api_client, other_headers, auth_headers, rsvp_event
    ):
        q = _create_question(
            rsvp_event,
            field_type="textarea",
            options=[],
            label="travel details",
        )

        response = api_client.post(
            f"/api/community/events/{rsvp_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING, "answers": {q["id"]: "x" * 2001}},
            content_type="application/json",
            **other_headers,
        )

        assert response.status_code == 422
        error = response.json()["detail"][0]
        assert error["code"] == Code.Event.RSVP_ANSWER_TOO_LONG
        assert error["params"]["label"] == "travel details"

    def test_host_sees_guests_when_rsvp_disabled(
        self, api_client, other_headers, auth_headers, rsvp_event, other_user
    ):
        q = _create_question(rsvp_event)
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
