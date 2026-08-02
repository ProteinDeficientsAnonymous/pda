from unittest.mock import patch

import pytest
from community._validation import Code
from community.models import Event, EventRsvpQuestion

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
        "field_type": "dropdown",
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
                        "field_type": "dropdown",
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
