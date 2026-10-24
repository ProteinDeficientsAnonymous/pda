import json
import logging
from datetime import timedelta

import pytest
from audit.models import AuditLogEntry
from community._validation import Code
from community.models import (
    Event,
    EventFeedbackRequest,
    EventType,
    Survey,
    SurveyQuestion,
    SurveyQuestionType,
    SurveyResponse,
)
from django.utils import timezone
from notifications._event_feedback_notifications import notify_event_feedback
from notifications.models import Notification, NotificationType
from users.models import User

from tests._asserts import assert_error_code


@pytest.fixture
def feedback_survey(db):
    survey = Survey.objects.create(
        title="official feedback",
        slug="official-feedback",
        anonymous=True,
        feedback_event_type=EventType.OFFICIAL,
    )
    SurveyQuestion.objects.create(
        survey=survey, label="how was it?", field_type=SurveyQuestionType.TEXT, required=True
    )
    return survey


@pytest.fixture
def event(db, test_user):
    start = timezone.now() - timedelta(days=1)
    return Event.objects.create(
        title="vegan potluck",
        event_type=EventType.OFFICIAL,
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        created_by=test_user,
    )


@pytest.fixture
def feedback_request(event, test_user):
    return EventFeedbackRequest.objects.create(
        event=event, user=test_user, token=EventFeedbackRequest.new_token()
    )


def _answers(survey: Survey, text: str = "loved it") -> str:
    question = survey.questions.first()
    assert question is not None
    return json.dumps({"answers": {str(question.id): text}})


@pytest.mark.django_db
class TestFeedbackSurveySlugHidden:
    def test_feedback_survey_hidden_from_slug_view_and_respond(self, api_client, feedback_survey):
        view = api_client.get(f"/api/community/surveys/view/{feedback_survey.slug}/")
        assert view.status_code == 404
        assert_error_code(view, Code.Survey.NOT_FOUND)

        respond = api_client.post(
            f"/api/community/surveys/view/{feedback_survey.slug}/respond/",
            data=_answers(feedback_survey),
            content_type="application/json",
        )
        assert respond.status_code == 404
        assert_error_code(respond, Code.Survey.NOT_FOUND)
        assert not SurveyResponse.objects.filter(survey=feedback_survey).exists()


FEEDBACK_URL = "/api/community/event-feedback/"
RESPOND_URL = "/api/community/event-feedback/respond/"


def _token_header(token: str) -> dict:
    return {"HTTP_X_FEEDBACK_TOKEN": token}


@pytest.mark.django_db
class TestGetFeedbackLink:
    def test_get_returns_survey_and_event_title(
        self, api_client, feedback_survey, feedback_request, event
    ):
        response = api_client.get(FEEDBACK_URL, **_token_header(feedback_request.token))
        assert response.status_code == 200
        body = response.json()
        assert body["event_id"] == str(event.id)
        assert body["event_title"] == "vegan potluck"
        assert body["event_start"] is not None
        assert body["already_responded"] is False
        assert body["is_open"] is True
        assert body["survey"]["id"] == str(feedback_survey.id)
        assert [q["label"] for q in body["survey"]["questions"]] == ["how was it?"]
        assert body["survey"]["my_response_id"] is None
        assert body["survey"]["my_answers"] is None

    def test_unknown_token_404(self, api_client, feedback_survey):
        response = api_client.get(FEEDBACK_URL, **_token_header("not-a-real-token"))
        assert response.status_code == 404
        assert_error_code(response, Code.Survey.FEEDBACK_LINK_INVALID)

    def test_missing_token_header_404(self, api_client, feedback_request):
        response = api_client.get(FEEDBACK_URL)
        assert response.status_code == 404
        assert_error_code(response, Code.Survey.FEEDBACK_LINK_INVALID)

    def test_get_without_feedback_survey_returns_no_survey(self, api_client, feedback_request):
        response = api_client.get(FEEDBACK_URL, **_token_header(feedback_request.token))
        assert response.status_code == 200
        assert response.json()["survey"] is None
        assert response.json()["is_open"] is False

    def test_get_after_survey_deactivated_reports_closed(
        self, api_client, feedback_survey, feedback_request
    ):
        feedback_survey.is_active = False
        feedback_survey.save(update_fields=["is_active"])
        response = api_client.get(FEEDBACK_URL, **_token_header(feedback_request.token))
        assert response.status_code == 200
        assert response.json()["is_open"] is False

    def test_get_after_responding_reports_already_responded(
        self, api_client, feedback_survey, feedback_request
    ):
        feedback_request.responded_on = timezone.localdate()
        feedback_request.save(update_fields=["responded_on"])
        response = api_client.get(FEEDBACK_URL, **_token_header(feedback_request.token))
        assert response.status_code == 200
        assert response.json()["already_responded"] is True


def _submit(api_client, feedback_request, survey, text="loved it"):
    return api_client.post(
        RESPOND_URL,
        data=_answers(survey, text),
        content_type="application/json",
        **_token_header(feedback_request.token),
    )


@pytest.mark.django_db
class TestSubmitFeedback:
    def test_submit_creates_response_without_user_and_with_event(
        self, api_client, feedback_survey, feedback_request, event
    ):
        response = _submit(api_client, feedback_request, feedback_survey)
        assert response.status_code == 201
        assert response.json() == {"confirmation_message": feedback_survey.confirmation_message}
        stored = SurveyResponse.objects.get(survey=feedback_survey)
        assert stored.user_id is None
        assert stored.event_id == event.id
        assert stored.anonymous_token is None

    def test_submit_marks_responded_on_date(self, api_client, feedback_survey, feedback_request):
        _submit(api_client, feedback_request, feedback_survey)
        feedback_request.refresh_from_db()
        assert feedback_request.responded_on == timezone.localdate()

    def test_submit_leaves_no_attributed_audit_row(
        self, api_client, feedback_survey, feedback_request, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            _submit(api_client, feedback_request, feedback_survey)
        entry = AuditLogEntry.objects.get(action="survey_response_submitted")
        assert entry.actor_id is None
        assert entry.ip_address is None
        assert feedback_request.token not in json.dumps(entry.details)

    def test_request_log_line_never_contains_token(
        self, api_client, feedback_survey, feedback_request, caplog, monkeypatch
    ):
        monkeypatch.setattr(logging.getLogger("pda"), "propagate", True)
        with caplog.at_level(logging.DEBUG):
            api_client.get(FEEDBACK_URL, **_token_header(feedback_request.token))
            assert _submit(api_client, feedback_request, feedback_survey).status_code == 201
            _submit(api_client, feedback_request, feedback_survey)
        middleware_lines = [r for r in caplog.records if r.name == "pda.middleware"]
        assert len(middleware_lines) == 3
        assert all(feedback_request.token not in r.getMessage() for r in caplog.records)
        assert all(feedback_request.token not in str(r.__dict__) for r in caplog.records)

    def test_second_submit_rejected(self, api_client, feedback_survey, feedback_request):
        assert _submit(api_client, feedback_request, feedback_survey).status_code == 201
        second = _submit(api_client, feedback_request, feedback_survey, "changed my mind")
        assert second.status_code == 400
        assert_error_code(second, Code.Survey.FEEDBACK_ALREADY_SUBMITTED)
        assert SurveyResponse.objects.filter(survey=feedback_survey).count() == 1

    def test_unknown_token_404(self, api_client, feedback_survey):
        response = api_client.post(
            RESPOND_URL,
            data=_answers(feedback_survey),
            content_type="application/json",
            **_token_header("nope"),
        )
        assert response.status_code == 404
        assert_error_code(response, Code.Survey.FEEDBACK_LINK_INVALID)

    def test_submit_after_survey_unmarked_404(self, api_client, feedback_survey, feedback_request):
        answers = _answers(feedback_survey)
        feedback_survey.feedback_event_type = ""
        feedback_survey.save(update_fields=["feedback_event_type"])
        response = api_client.post(
            RESPOND_URL,
            data=answers,
            content_type="application/json",
            **_token_header(feedback_request.token),
        )
        assert response.status_code == 404
        assert_error_code(response, Code.Survey.NOT_FOUND)
        assert not SurveyResponse.objects.exists()

    def test_submit_after_survey_deactivated_closed(
        self, api_client, feedback_survey, feedback_request
    ):
        feedback_survey.is_active = False
        feedback_survey.save(update_fields=["is_active"])
        response = _submit(api_client, feedback_request, feedback_survey)
        assert response.status_code == 400
        assert_error_code(response, Code.Survey.CLOSED)
        feedback_request.refresh_from_db()
        assert feedback_request.responded_on is None

    def test_required_question_missing_422(self, api_client, feedback_survey, feedback_request):
        response = api_client.post(
            RESPOND_URL,
            data=json.dumps({"answers": {}}),
            content_type="application/json",
            **_token_header(feedback_request.token),
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Survey.ANSWER_REQUIRED)
        feedback_request.refresh_from_db()
        assert feedback_request.responded_on is None

    def test_submit_rate_limited(self, api_client, feedback_survey, feedback_request):
        statuses = [
            _submit(api_client, feedback_request, feedback_survey).status_code for _ in range(21)
        ]
        assert statuses[-1] == 429


@pytest.mark.django_db
class TestFeedbackHostNotification:
    def test_submit_notifies_creator_and_cohosts(
        self, api_client, feedback_survey, event, test_user, django_capture_on_commit_callbacks
    ):
        cohost = User.objects.create_user(phone_number="+12025559301", first_name="Co")
        attendee = User.objects.create_user(phone_number="+12025559302", first_name="Zelda")
        event.co_hosts.add(cohost)
        feedback_request = EventFeedbackRequest.objects.create(
            event=event, user=attendee, token=EventFeedbackRequest.new_token()
        )
        with django_capture_on_commit_callbacks(execute=True):
            response = _submit(api_client, feedback_request, feedback_survey)
        assert response.status_code == 201
        notes = Notification.objects.filter(notification_type=NotificationType.EVENT_FEEDBACK)
        assert sorted(n.recipient_id for n in notes) == sorted([test_user.id, cohost.id])
        for note in notes:
            assert note.event_id == event.id
            assert note.message == "new feedback for vegan potluck"
            assert note.related_user_id is None
            assert "Zelda" not in note.message

    def test_long_event_title_truncated_to_fit(self, event):
        event.title = "x" * 300
        notify_event_feedback(event)
        note = Notification.objects.get(notification_type=NotificationType.EVENT_FEEDBACK)
        assert len(note.message) <= 255
        assert note.message.startswith("new feedback for xxx")
