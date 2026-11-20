import pytest
from community.models import Event, EventRSVP, EventRsvpQuestion, RsvpQuestionType, RSVPStatus
from users.models import User

from tests._auth import auth_headers_for
from tests._time import future_iso

ORDER = {
    "label": "what are you ordering?",
    "field_type": "select",
    "options": ["bowl", "plate"],
    "option_prices": [1200, 1850],
    "required": True,
}


@pytest.fixture
def rsvp_event(db, test_user):
    return Event.objects.create(
        title="Dinner",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        rsvp_enabled=True,
        created_by=test_user,
    )


@pytest.fixture
def other_headers(db):
    guest = User.objects.create_user(phone_number="+12025550998", password="guestpass")
    return auth_headers_for(guest)


def _sync(api_client, auth_headers, event, questions, expected=()):
    return api_client.put(
        f"/api/community/events/{event.id}/rsvp-questions/",
        {"expected": list(expected), "questions": questions},
        content_type="application/json",
        **auth_headers,
    )


@pytest.mark.django_db
class TestRsvpOptionPrices:
    def test_sync_saves_and_returns_prices(self, api_client, auth_headers, rsvp_event):
        response = _sync(api_client, auth_headers, rsvp_event, [ORDER])

        assert response.status_code == 200
        assert response.json()[0]["option_prices"] == [1200, 1850]
        assert EventRsvpQuestion.objects.get(event=rsvp_event).option_prices == [1200, 1850]

    def test_unpriced_question_returns_empty_prices(self, api_client, auth_headers, rsvp_event):
        unpriced = {k: v for k, v in ORDER.items() if k != "option_prices"}
        response = _sync(api_client, auth_headers, rsvp_event, [unpriced])

        assert response.json()[0]["option_prices"] == []

    @pytest.mark.parametrize(
        "overrides",
        [
            {"option_prices": [1200]},
            {"option_prices": [1200, -1]},
            {"option_prices": [1200, 1_000_001]},
            {"field_type": "textarea", "options": [], "option_prices": [1200]},
        ],
        ids=["count-mismatch", "negative", "too-large", "textarea"],
    )
    def test_invalid_prices_rejected(self, api_client, auth_headers, rsvp_event, overrides):
        response = _sync(api_client, auth_headers, rsvp_event, [{**ORDER, **overrides}])

        assert response.status_code == 422
        assert not EventRsvpQuestion.objects.filter(event=rsvp_event).exists()

    def test_price_change_by_someone_else_conflicts(self, api_client, auth_headers, rsvp_event):
        question = EventRsvpQuestion.objects.create(event=rsvp_event, **ORDER)
        stale = {**ORDER, "id": str(question.id), "option_prices": [1000, 1850]}

        response = _sync(api_client, auth_headers, rsvp_event, [stale], expected=[stale])

        assert response.status_code == 409

    def test_create_event_saves_prices(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/events/",
            {"title": "priced draft", "status": "draft", "rsvp_questions": [ORDER]},
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["rsvp_questions"][0]["option_prices"] == [1200, 1850]


def _rsvp(api_client, headers, event, answers):
    return api_client.post(
        f"/api/community/events/{event.id}/rsvp/",
        {"status": RSVPStatus.ATTENDING, "questionnaire_responses": answers},
        content_type="application/json",
        **headers,
    )


@pytest.mark.django_db
class TestRsvpAnswerPriceSnapshot:
    def test_select_answer_snapshots_option_price(self, api_client, other_headers, rsvp_event):
        q = EventRsvpQuestion.objects.create(event=rsvp_event, **ORDER)

        _rsvp(api_client, other_headers, rsvp_event, {str(q.id): "plate"})

        assert EventRSVP.objects.get(event=rsvp_event).questionnaire_responses[str(q.id)] == {
            "label": ORDER["label"],
            "answer": "plate",
            "price_cents": 1850,
        }

    def test_checkbox_answer_sums_ticked_prices(self, api_client, other_headers, rsvp_event):
        q = EventRsvpQuestion.objects.create(
            event=rsvp_event,
            **{
                **ORDER,
                "field_type": RsvpQuestionType.CHECKBOX,
                "options": ["a", "b", "c"],
                "option_prices": [100, 250, 400],
            },
        )

        _rsvp(api_client, other_headers, rsvp_event, {str(q.id): ["a", "c"]})

        snapshot = EventRSVP.objects.get(event=rsvp_event).questionnaire_responses[str(q.id)]
        assert snapshot["price_cents"] == 500

    def test_unpriced_answer_has_no_price(self, api_client, other_headers, rsvp_event):
        q = EventRsvpQuestion.objects.create(event=rsvp_event, **{**ORDER, "option_prices": []})

        _rsvp(api_client, other_headers, rsvp_event, {str(q.id): "bowl"})

        snapshot = EventRSVP.objects.get(event=rsvp_event).questionnaire_responses[str(q.id)]
        assert "price_cents" not in snapshot

    def test_unchanged_answer_keeps_price_after_host_edit(
        self, api_client, other_headers, rsvp_event
    ):
        q = EventRsvpQuestion.objects.create(event=rsvp_event, **ORDER)
        _rsvp(api_client, other_headers, rsvp_event, {str(q.id): "plate"})
        q.option_prices = [1200, 2500]
        q.save()

        _rsvp(api_client, other_headers, rsvp_event, {str(q.id): "plate"})
        kept = EventRSVP.objects.get(event=rsvp_event).questionnaire_responses[str(q.id)]
        _rsvp(api_client, other_headers, rsvp_event, {str(q.id): "bowl"})
        changed = EventRSVP.objects.get(event=rsvp_event).questionnaire_responses[str(q.id)]

        assert kept["price_cents"] == 1850
        assert changed["price_cents"] == 1200
