import pytest
from community._validation import Code
from community.models import Event, EventRSVP, EventRsvpQuestion, RsvpQuestionType, RSVPStatus

from tests._asserts import assert_error_code
from tests.conftest import future_iso


@pytest.fixture
def rsvp_event(db, test_user):
    return Event.objects.create(
        title="Potluck",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        rsvp_enabled=True,
        created_by=test_user,
    )


def _question(event, field_type=RsvpQuestionType.CHECKBOX, **fields):
    return EventRsvpQuestion.objects.create(
        event=event,
        label="bringing",
        field_type=field_type,
        options=["mains", "desserts"],
        required=True,
        **fields,
    )


def _rsvp(api_client, auth_headers, event, answers):
    return api_client.post(
        f"/api/community/events/{event.id}/rsvp/",
        {"status": RSVPStatus.ATTENDING, "questionnaire_responses": answers},
        content_type="application/json",
        **auth_headers,
    )


@pytest.mark.django_db
class TestRsvpCheckboxListAnswers:
    def test_list_answer_is_stored_as_deduped_list(
        self, api_client, auth_headers, rsvp_event, test_user
    ):
        q = _question(rsvp_event)
        answer = ["desserts", " desserts ", "mains"]
        response = _rsvp(api_client, auth_headers, rsvp_event, {str(q.id): answer})
        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=rsvp_event, user=test_user)
        assert rsvp.questionnaire_responses[str(q.id)]["answer"] == ["desserts", "mains"]

    def test_unknown_option_in_list_is_rejected(self, api_client, auth_headers, rsvp_event):
        q = _question(rsvp_event)
        response = _rsvp(api_client, auth_headers, rsvp_event, {str(q.id): ["mains", "nope"]})
        assert response.status_code == 422
        assert_error_code(response, Code.Event.RSVP_ANSWER_INVALID_OPTION)

    def test_list_answer_to_select_question_is_rejected(self, api_client, auth_headers, rsvp_event):
        q = _question(rsvp_event, field_type=RsvpQuestionType.SELECT)
        response = _rsvp(api_client, auth_headers, rsvp_event, {str(q.id): ["mains"]})
        assert response.status_code == 422
        assert_error_code(response, Code.Event.RSVP_ANSWER_INVALID_FORMAT)

    def test_blank_list_counts_as_unanswered(self, api_client, auth_headers, rsvp_event):
        q = _question(rsvp_event)
        response = _rsvp(api_client, auth_headers, rsvp_event, {str(q.id): [" "]})
        assert response.status_code == 422
        assert_error_code(response, Code.Event.RSVP_ANSWER_REQUIRED)
