import pytest
from community._validation import Code
from community.models import EventRSVP, EventRsvpQuestion, RsvpQuestionType, RSVPStatus
from users.models import NonMemberRsvpToken

from tests._public_rsvp_helpers import first_code, make_non_member, make_official_event


@pytest.fixture
def nonmember(db):
    return make_non_member("+14155550001", "nm@example.com", name="non member")


@pytest.fixture
def official_event(db):
    return make_official_event(title="Official A")


def _post(api_client, event, token, body):
    return api_client.post(
        f"/api/community/public/my-rsvps/{event.id}/?token={token.token}",
        body,
        content_type="application/json",
    )


@pytest.mark.django_db
class TestPublicRsvpAnswerUpdates:
    def test_update_without_answers_preserves_existing_answers(
        self, api_client, nonmember, official_event
    ):
        question = EventRsvpQuestion.objects.create(
            event=official_event,
            label="travel details",
            field_type=RsvpQuestionType.TEXTAREA,
            required=False,
        )
        EventRSVP.objects.create(
            event=official_event,
            user=nonmember,
            status=RSVPStatus.ATTENDING,
            questionnaire_responses={
                str(question.id): {"label": question.label, "answer": "taking transit"}
            },
        )
        token = NonMemberRsvpToken.issue_or_extend(nonmember)

        response = _post(api_client, official_event, token, {"status": RSVPStatus.MAYBE})

        assert response.status_code == 200
        rsvp = EventRSVP.objects.get(event=official_event, user=nonmember)
        assert rsvp.questionnaire_responses[str(question.id)]["answer"] == "taking transit"

    def test_update_without_answers_validates_new_required_questions(
        self, api_client, nonmember, official_event
    ):
        EventRSVP.objects.create(
            event=official_event,
            user=nonmember,
            status=RSVPStatus.CANT_GO,
        )
        EventRsvpQuestion.objects.create(
            event=official_event,
            label="travel details",
            field_type=RsvpQuestionType.TEXTAREA,
            required=True,
        )
        token = NonMemberRsvpToken.issue_or_extend(nonmember)

        response = _post(api_client, official_event, token, {"status": RSVPStatus.ATTENDING})

        assert response.status_code == 422
        assert first_code(response) == Code.Event.RSVP_ANSWER_REQUIRED

    def test_explicit_answers_preserve_deleted_question_snapshots(
        self, api_client, nonmember, official_event
    ):
        current = EventRsvpQuestion.objects.create(
            event=official_event,
            label="current",
            field_type=RsvpQuestionType.TEXTAREA,
            required=False,
        )
        deleted_id = "00000000-0000-0000-0000-000000000001"
        EventRSVP.objects.create(
            event=official_event,
            user=nonmember,
            status=RSVPStatus.ATTENDING,
            questionnaire_responses={
                deleted_id: {"label": "deleted", "answer": "historical"},
                str(current.id): {"label": "old current label", "answer": "unchanged"},
            },
        )
        token = NonMemberRsvpToken.issue_or_extend(nonmember)

        response = _post(
            api_client,
            official_event,
            token,
            {
                "status": RSVPStatus.MAYBE,
                "questionnaire_responses": {str(current.id): "unchanged"},
            },
        )

        assert response.status_code == 200
        answers = EventRSVP.objects.get(
            event=official_event, user=nonmember
        ).questionnaire_responses
        assert answers[deleted_id]["answer"] == "historical"
        assert answers[str(current.id)]["label"] == "old current label"
