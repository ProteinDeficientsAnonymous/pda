from unittest.mock import patch

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


def _create_question(event, **overrides):
    data = {
        "label": "how are you getting there?",
        "field_type": "select",
        "options": ["driving", "transit"],
        "required": True,
        "display_order": event.rsvp_questions.count(),
        **overrides,
    }
    question = EventRsvpQuestion.objects.create(event=event, **data)
    return {
        "id": str(question.id),
        **data,
    }


def _sync_fields(question):
    return {
        "id": question["id"],
        "label": question["label"],
        "field_type": question["field_type"],
        "options": question["options"],
        "required": question["required"],
    }


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


@pytest.mark.django_db
class TestEventRsvpQuestionSync:
    def test_host_can_atomically_replace_questions(self, api_client, auth_headers, rsvp_event):
        existing = _create_question(rsvp_event)
        removed = _create_question(rsvp_event, label="remove me")

        response = api_client.put(
            f"/api/community/events/{rsvp_event.id}/rsvp-questions/",
            {
                "expected": [existing, removed],
                "questions": [
                    {
                        "id": existing["id"],
                        "label": "updated",
                        "field_type": "textarea",
                        "options": [],
                        "required": False,
                    },
                    {
                        "id": None,
                        "label": "new",
                        "field_type": "select",
                        "options": ["a", "b"],
                        "required": True,
                    },
                ],
            },
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 200
        assert [q["label"] for q in response.json()] == ["updated", "new"]
        assert [q["display_order"] for q in response.json()] == [0, 1]
        assert not EventRsvpQuestion.objects.filter(id=removed["id"]).exists()

    def test_replace_questions_rolls_back_when_id_is_unknown(
        self, api_client, auth_headers, rsvp_event
    ):
        existing = _create_question(rsvp_event)
        response = api_client.put(
            f"/api/community/events/{rsvp_event.id}/rsvp-questions/",
            {
                "expected": [existing],
                "questions": [
                    {**existing, "label": "changed"},
                    {
                        "id": "00000000-0000-0000-0000-000000000001",
                        "label": "missing",
                        "field_type": "textarea",
                        "options": [],
                        "required": False,
                    },
                ],
            },
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 404
        assert EventRsvpQuestion.objects.get(id=existing["id"]).label == existing["label"]

    def test_replace_questions_rejects_stale_baseline(self, api_client, auth_headers, rsvp_event):
        existing = _create_question(rsvp_event)
        _create_question(rsvp_event, label="concurrent")

        response = api_client.put(
            f"/api/community/events/{rsvp_event.id}/rsvp-questions/",
            {"expected": [existing], "questions": [existing]},
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 409
        assert EventRsvpQuestion.objects.filter(event=rsvp_event).count() == 2

    def test_replace_questions_rejects_duplicate_ids(self, api_client, auth_headers, rsvp_event):
        existing = _create_question(rsvp_event)
        response = api_client.put(
            f"/api/community/events/{rsvp_event.id}/rsvp-questions/",
            {"expected": [existing], "questions": [existing, existing]},
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 400
        assert_error_code(response, Code.Event.RSVP_QUESTION_DUPLICATE)

    def test_replace_questions_rolls_back_after_write_failure(
        self, api_client, auth_headers, rsvp_event
    ):
        existing = _create_question(rsvp_event)
        real_save = EventRsvpQuestion.save
        save_count = 0

        def fail_second_save(question, *args, **kwargs):
            nonlocal save_count
            save_count += 1
            if save_count == 2:
                raise RuntimeError("simulated write failure")
            return real_save(question, *args, **kwargs)

        with (
            patch.object(EventRsvpQuestion, "save", fail_second_save),
            pytest.raises(RuntimeError, match="simulated write failure"),
        ):
            api_client.put(
                f"/api/community/events/{rsvp_event.id}/rsvp-questions/",
                {
                    "expected": [existing],
                    "questions": [
                        {**existing, "label": "changed"},
                        {
                            "id": None,
                            "label": "new",
                            "field_type": "textarea",
                            "options": [],
                            "required": False,
                        },
                    ],
                },
                content_type="application/json",
                **auth_headers,
            )

        assert EventRsvpQuestion.objects.get(id=existing["id"]).label == existing["label"]
        assert EventRsvpQuestion.objects.filter(event=rsvp_event).count() == 1

    def test_create_event_saves_questions_atomically(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/events/",
            {
                "title": "draft with questions",
                "status": "draft",
                "rsvp_questions": [
                    {
                        "label": "dietary?",
                        "field_type": "textarea",
                        "options": [],
                        "required": True,
                    }
                ],
            },
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["rsvp_questions"][0]["label"] == "dietary?"

    def test_reorder_keeps_question_ids_and_existing_answers(
        self, api_client, auth_headers, other_headers, other_user, rsvp_event
    ):
        travel = _create_question(rsvp_event)
        notes = _create_question(
            rsvp_event,
            label="anything we should know?",
            field_type="textarea",
            options=[],
            required=False,
        )
        assert (
            api_client.post(
                f"/api/community/events/{rsvp_event.id}/rsvp/",
                {
                    "status": RSVPStatus.ATTENDING,
                    "has_plus_one": False,
                    "questionnaire_responses": {
                        travel["id"]: "transit",
                        notes["id"]: "nut allergy",
                    },
                },
                content_type="application/json",
                **other_headers,
            ).status_code
            == 200
        )

        response = api_client.put(
            f"/api/community/events/{rsvp_event.id}/rsvp-questions/",
            {
                "expected": [_sync_fields(travel), _sync_fields(notes)],
                "questions": [_sync_fields(notes), _sync_fields(travel)],
            },
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert [q["id"] for q in body] == [notes["id"], travel["id"]]
        assert [q["label"] for q in body] == ["anything we should know?", travel["label"]]
        assert [q["display_order"] for q in body] == [0, 1]
        assert EventRsvpQuestion.objects.get(id=notes["id"]).display_order == 0
        assert EventRsvpQuestion.objects.get(id=travel["id"]).display_order == 1

        saved = EventRSVP.objects.get(event=rsvp_event, user=other_user)
        assert saved.questionnaire_responses[travel["id"]]["answer"] == "transit"
        assert saved.questionnaire_responses[notes["id"]]["answer"] == "nut allergy"

        host_view = api_client.get(f"/api/community/events/{rsvp_event.id}/", **auth_headers).json()
        assert [q["id"] for q in host_view["rsvp_questions"]] == [notes["id"], travel["id"]]
        host_guest = next(g for g in host_view["guests"] if g["user_id"] == str(other_user.pk))
        assert host_guest["questionnaire_responses"][travel["id"]]["answer"] == "transit"
        assert host_guest["questionnaire_responses"][notes["id"]]["answer"] == "nut allergy"

        guest_view = api_client.get(
            f"/api/community/events/{rsvp_event.id}/", **other_headers
        ).json()
        assert [q["id"] for q in guest_view["rsvp_questions"]] == [notes["id"], travel["id"]]
        assert guest_view["my_questionnaire_responses"][travel["id"]]["answer"] == "transit"
        assert guest_view["my_questionnaire_responses"][notes["id"]]["answer"] == "nut allergy"

        new_guest = User.objects.create_user(
            phone_number="+12025550888",
            password="newpass",
            first_name="New",
            last_name="Guest",
        )
        new_headers = {
            "HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(new_guest).access_token}"  # type: ignore
        }
        assert (
            api_client.post(
                f"/api/community/events/{rsvp_event.id}/rsvp/",
                {
                    "status": RSVPStatus.ATTENDING,
                    "has_plus_one": False,
                    "questionnaire_responses": {
                        notes["id"]: "gluten free",
                        travel["id"]: "driving",
                    },
                },
                content_type="application/json",
                **new_headers,
            ).status_code
            == 200
        )

        after = api_client.get(f"/api/community/events/{rsvp_event.id}/", **auth_headers).json()
        assert [q["label"] for q in after["rsvp_questions"]] == [
            "anything we should know?",
            travel["label"],
        ]
        old_guest = next(g for g in after["guests"] if g["user_id"] == str(other_user.pk))
        fresh_guest = next(g for g in after["guests"] if g["user_id"] == str(new_guest.pk))
        assert old_guest["questionnaire_responses"][travel["id"]]["answer"] == "transit"
        assert old_guest["questionnaire_responses"][notes["id"]]["answer"] == "nut allergy"
        assert fresh_guest["questionnaire_responses"][travel["id"]]["answer"] == "driving"
        assert fresh_guest["questionnaire_responses"][notes["id"]]["answer"] == "gluten free"
