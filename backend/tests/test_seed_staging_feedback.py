import pytest
from community.management.commands._seed_staging_feedback import (
    FEEDBACK_EVENT_SPECS,
    FEEDBACK_SURVEY_SLUG,
)
from community.models import (
    AttendanceStatus,
    EventFeedbackRequest,
    EventRSVP,
    EventType,
    Survey,
    SurveyQuestion,
    SurveyQuestionType,
    SurveyResponse,
)
from django.core.management import call_command


@pytest.mark.django_db
def test_seed_staging_creates_anonymous_responses_per_event_idempotently():
    call_command("seed_staging")
    call_command("seed_staging")
    survey = Survey.objects.get(slug=FEEDBACK_SURVEY_SLUG)
    for spec in FEEDBACK_EVENT_SPECS:
        title = spec.event.title
        responses = SurveyResponse.objects.filter(survey=survey, event__title=title)
        assert responses.count() == spec.responders
        assert all(r.user_id is None and r.answers for r in responses)
        attended = EventRSVP.objects.filter(
            event__title=title, attendance=AttendanceStatus.ATTENDED
        )
        assert attended.count() == spec.attendees
        requests = EventFeedbackRequest.objects.filter(event__title=title)
        assert requests.filter(responded_on__isnull=False).count() == spec.responders
        assert not requests.filter(first_sent_at__isnull=True).exists()


@pytest.mark.django_db
def test_seed_staging_reuses_existing_official_feedback_survey():
    survey = Survey.objects.create(
        title="real feedback", slug="real-feedback", feedback_event_type=EventType.OFFICIAL
    )
    SurveyQuestion.objects.create(
        survey=survey, label="rate it", field_type=SurveyQuestionType.RATING
    )
    call_command("seed_staging")
    assert not Survey.objects.filter(slug=FEEDBACK_SURVEY_SLUG).exists()
    answers = [a["answer"] for r in survey.responses.all() for a in r.answers.values()]
    assert answers
    assert all(1 <= int(a) <= 5 for a in answers)


@pytest.mark.django_db
def test_seed_staging_reset_leaves_no_orphaned_feedback():
    call_command("seed_staging")
    call_command("seed_staging", "--reset")
    assert not SurveyResponse.objects.filter(event__isnull=True).exists()
    assert SurveyResponse.objects.count() == sum(s.responders for s in FEEDBACK_EVENT_SPECS)
