import pytest
from community.management.commands._seed_staging_feedback import (
    FEEDBACK_EVENT_SPECS,
    FEEDBACK_SURVEY_SLUG,
    FEEDBACK_TITLE_PREFIX,
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
def test_seed_staging_creates_anonymous_responses_per_event():
    call_command("seed_staging")
    survey = Survey.objects.get(slug=FEEDBACK_SURVEY_SLUG)
    assert survey.feedback_event_type == EventType.OFFICIAL
    for spec in FEEDBACK_EVENT_SPECS:
        responses = SurveyResponse.objects.filter(survey=survey, event__title=spec.event.title)
        assert responses.count() == spec.responders
        assert not responses.filter(user__isnull=False).exists()
        assert all(r.answers for r in responses)
        assert (
            EventRSVP.objects.filter(
                event__title=spec.event.title, attendance=AttendanceStatus.ATTENDED
            ).count()
            == spec.attendees
        )
        requests = EventFeedbackRequest.objects.filter(event__title=spec.event.title)
        assert requests.filter(responded_on__isnull=False).count() == spec.responders
        assert not requests.filter(first_sent_at__isnull=True).exists()


@pytest.mark.django_db
def test_seed_staging_feedback_is_idempotent():
    call_command("seed_staging")
    count = SurveyResponse.objects.count()
    call_command("seed_staging")
    assert SurveyResponse.objects.count() == count


@pytest.mark.django_db
def test_seed_staging_reuses_existing_official_feedback_survey():
    survey = Survey.objects.create(
        title="real feedback", slug="real-feedback", feedback_event_type=EventType.OFFICIAL
    )
    SurveyQuestion.objects.create(
        survey=survey, label="rate it", field_type=SurveyQuestionType.RATING, display_order=0
    )
    call_command("seed_staging")
    assert not Survey.objects.filter(slug=FEEDBACK_SURVEY_SLUG).exists()
    assert survey.questions.count() == 1
    answers = [a["answer"] for r in survey.responses.all() for a in r.answers.values()]
    assert answers
    assert all(1 <= int(a) <= 5 for a in answers)


@pytest.mark.django_db
def test_seed_staging_reset_removes_seeded_feedback():
    call_command("seed_staging")
    call_command("seed_staging", "--reset")
    assert not SurveyResponse.objects.filter(event__isnull=True).exists()
    expected = sum(spec.responders for spec in FEEDBACK_EVENT_SPECS)
    assert (
        SurveyResponse.objects.filter(event__title__startswith=FEEDBACK_TITLE_PREFIX).count()
        == expected
    )
